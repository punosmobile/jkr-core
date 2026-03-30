"""
LIETE-aineiston kääntäjä JKR-muotoon.

Muuntaa LIETE-kuljetustiedot JKR-järjestelmän ymmärtämään muotoon.
"""

import logging
from datetime import date
from typing import List, Optional

from jkrimporter.model import (
    Asiakas as JkrAsiakas,
    Jatelaji as JkrJatelaji,
    JkrData,
    SopimusTyyppi,
    TyhjennysSopimus,
    Tunnus,
    Tyhjennystapahtuma,
    Yhteystieto,
    Osoite,
)
from jkrimporter.providers.lahti.liete_kuljetustiedosto import LieteKuljetustiedosto
from jkrimporter.providers.lahti.liete_models import LieteKuljetusRow
from jkrimporter.utils.intervals import Interval

logger = logging.getLogger(__name__)


# Kartoitus LIETE-jätetyypeistä JKR-jätelajeihin
# Määrittely 17.11.2025
# Huom: "Jätteen kuvaus" (Umpisäiliö, Saostussäiliö, Pienpuhdistamo) on keräysvälinetyyppi, ei jätelaji
LIETE_JATELAJI_MAP = {
    # Lietteen tyyppi (jätetyyppi) -> Jätelaji:
    "Musta": JkrJatelaji.mustaliete,
    "Harmaa": JkrJatelaji.harmaaliete,
    "Ei tietoa": JkrJatelaji.liete,  # Fallback yleiseen lietteeseen
    
    # Vanhat nimitykset (yhteensopivuus):
    "Liete": JkrJatelaji.liete,
    "Musta liete": JkrJatelaji.mustaliete,
    "Harmaa liete": JkrJatelaji.harmaaliete,
}


class LieteTranslator:
    """
    Kääntää LIETE-kuljetustiedot JKR-muotoon.
    
    LIETE-data on kuljetustapahtumia, ei sopimuksia, joten:
    - Luodaan asiakkaat kuljetustietojen perusteella
    - Kuljetukset tallennetaan tyhjennystapahtuminakohdentaminen tehdään PRT:n tai osoitteen perusteella
    """
    
    def __init__(self, liete_tiedosto: LieteKuljetustiedosto, tiedontuottajatunnus: str):
        """
        Alustaa kääntäjän.
        
        Args:
            liete_tiedosto: LIETE-kuljetustiedosto
            tiedontuottajatunnus: Tiedontuottajan tunnus (esim. 'LSJ')
        """
        self._source = liete_tiedosto
        self._tiedontuottaja_tunnus = tiedontuottajatunnus
        self._asiakas_cache = {}  # Cache asiakkaille
    
    def as_jkr_data(self, alkupvm: Optional[date], loppupvm: Optional[date]) -> JkrData:
        """
        Muuntaa LIETE-datan JKR-dataksi.
        
        Args:
            alkupvm: Raportointikauden alkupäivämäärä
            loppupvm: Raportointikauden loppupäivämäärä
            
        Returns:
            JkrData-objekti
        """
        data = JkrData()
        data.alkupvm = alkupvm
        data.loppupvm = loppupvm
        
        logger.info(f"Aloitetaan LIETE-datan muunnos, kausi: {alkupvm} - {loppupvm}")
        
        kuljetus_count = 0
        asiakas_count = 0
        skipped_count = 0
        
        for kuljetus_row in self._source.kuljetustiedot:
            kuljetus_count += 1
            
            # Luo tai hae asiakas
            asiakas = self._get_or_create_asiakas(data, kuljetus_row)
            
            if not asiakas:
                logger.warning(
                    f"Ohitetaan kuljetus {kuljetus_row.id_tunnus}: "
                    f"Ei voitu luoda asiakasta"
                )
                skipped_count += 1
                continue
            
            # Luo tyhjennystapahtuma
            tapahtuma = self._create_tyhjennystapahtuma(kuljetus_row)
            
            if tapahtuma:
                asiakas.tyhjennystapahtumat.append(tapahtuma)
            else:
                logger.warning(
                    f"Ohitetaan kuljetus {kuljetus_row.id_tunnus}: "
                    f"Ei voitu luoda tyhjennystapahtumaata"
                )
                skipped_count += 1
        
        asiakas_count = len(data.asiakkaat)
        
        logger.info(
            f"LIETE-datan muunnos valmis: "
            f"{kuljetus_count} kuljetusta, "
            f"{asiakas_count} asiakasta, "
            f"{skipped_count} ohitettu"
        )
        
        return data
    
    def _get_or_create_asiakas(
        self, 
        data: JkrData, 
        kuljetus_row: LieteKuljetusRow
    ) -> Optional[JkrAsiakas]:
        """
        Hakee tai luo asiakkaan kuljetustiedon perusteella.
        
        LIETE-datassa asiakas tunnistetaan (määrittely 17.11.2025):
        1. PRT (pysyvä rakennustunnus) - ensisijainen
        2. Osoite (siirron alkamispaikan katuosoite + postinumero) - toissijainen
        
        Tiedontuottajana käytetään kuljettaja-kenttää (Y-tunnus).
        
        Args:
            data: JKR-data johon asiakas lisätään
            kuljetus_row: LIETE-kuljetusrivi
            
        Returns:
            JkrAsiakas tai None jos ei voitu luoda
        """
        # Luo asiakastunnus
        # Määrittelyn mukaan kohdentaminen:
        # 1. Ensisijainen: PRT (pysyvä rakennustunnus)
        # 2. Toissijainen: Siirron alkamispaikan katuosoite + postinumero
        if kuljetus_row.pysyva_rakennustunnus:
            asiakas_id = f"PRT_{kuljetus_row.pysyva_rakennustunnus}"
        # Toissijainen: osoite (EI kiinteistötunnusta!)
        elif kuljetus_row.alkamispaikan_katuosoite and kuljetus_row.alkamispaikan_postinumero:
            asiakas_id = (
                f"ADDR_{kuljetus_row.alkamispaikan_katuosoite}_"
                f"{kuljetus_row.alkamispaikan_postinumero}"
            ).replace(" ", "_").replace("/", "_")
        else:
            # Viimeisenä vaihtoehtona ID-tunnus (ei hyvä, koska eri joka kuljetukselle)
            logger.warning(
                f"Ei löytynyt PRT tai osoitetta kuljetukselle {kuljetus_row.id_tunnus}, "
                f"käytetään ID-tunnusta (asiakas luodaan joka kuljetukselle erikseen)"
            )
            if kuljetus_row.id_tunnus:
                asiakas_id = f"LIETE_{kuljetus_row.id_tunnus}"
            else:
                logger.warning("Ei tunnistetta asiakkaalle, ohitetaan")
                return None
        
        # Tarkista cache
        if asiakas_id in self._asiakas_cache:
            return self._asiakas_cache[asiakas_id]
        
        # Luo tunnus
        # Käytetään kuljettaja-kenttää (Y-tunnus) tiedontuottajana määrittelyn mukaan
        tiedontuottaja = kuljetus_row.kuljettaja if kuljetus_row.kuljettaja else self._tiedontuottaja_tunnus
        tunnus = Tunnus(tiedontuottaja, asiakas_id)
        
        # Tarkista onko jo datassa
        if tunnus in data.asiakkaat:
            asiakas = data.asiakkaat[tunnus]
            self._asiakas_cache[asiakas_id] = asiakas
            return asiakas
        
        # Luo uusi asiakas
        asiakas = self._create_asiakas(kuljetus_row, tunnus)
        
        if asiakas:
            data.asiakkaat[tunnus] = asiakas
            self._asiakas_cache[asiakas_id] = asiakas
        
        return asiakas
    
    def _create_asiakas(
        self, 
        kuljetus_row: LieteKuljetusRow, 
        tunnus: Tunnus
    ) -> Optional[JkrAsiakas]:
        """
        Luo uuden asiakkaan kuljetustiedon perusteella.
        
        Args:
            kuljetus_row: LIETE-kuljetusrivi
            tunnus: Asiakkaan tunnus
            
        Returns:
            JkrAsiakas tai None
        """
        # Luo osoite
        osoite = Osoite(
            katunimi=kuljetus_row.alkamispaikan_katuosoite or kuljetus_row.tuottajan_katuosoite,
            postinumero=kuljetus_row.alkamispaikan_postinumero or kuljetus_row.tuottajan_postinumero,
        )
        
        # Luo haltija
        haltija = Yhteystieto(
            nimi=kuljetus_row.jatteen_tuottaja or "Tuntematon",
            osoite=osoite,
        )
        
        # Luo kiinteistötunnukset
        kiinteistot = []
        if kuljetus_row.kiinteistotunnus:
            kiinteistot.append(kuljetus_row.kiinteistotunnus)
        
        # Luo rakennustunnukset
        rakennukset = []
        if kuljetus_row.pysyva_rakennustunnus:
            rakennukset.append(kuljetus_row.pysyva_rakennustunnus)
        
        # Luodaan sopimus liete-jätelajilla, jotta osapuoli luodaan
        # LIETE_TILAAJA-roolilla (create_or_update_haltija_osapuoli vaatii sopimuksen)
        liete_sopimus = TyhjennysSopimus(
            sopimustyyppi=SopimusTyyppi.tyhjennyssopimus,
            jatelaji=JkrJatelaji.liete,
            alkupvm=kuljetus_row.siirron_alkamisaika,
            loppupvm=kuljetus_row.siirron_paattymisaika or kuljetus_row.siirron_alkamisaika,
        )

        asiakas = JkrAsiakas(
            asiakasnumero=tunnus,
            voimassa=Interval(None, None),  # LIETE-datassa ei ole voimassaolotietoja
            ulkoinen_asiakastieto=kuljetus_row,  # Käytetään objektia, ei dict()
            kiinteistot=kiinteistot,
            rakennukset=rakennukset,
            haltija=haltija,
            yhteyshenkilo=None,  # LIETE-datassa ei ole yhteyshenkilöä
            sopimukset=[liete_sopimus],
            tyhjennystapahtumat=[],
        )
        
        return asiakas
    
    def _create_tyhjennystapahtuma(
        self, 
        kuljetus_row: LieteKuljetusRow
    ) -> Optional[Tyhjennystapahtuma]:
        """
        Luo tyhjennystapahtu man kuljetustiedon perusteella.
        
        Args:
            kuljetus_row: LIETE-kuljetusrivi
            
        Returns:
            Tyhjennystapahtuma tai None
        """
        # Määritä jätelaji
        jatelaji = self._map_jatelaji(kuljetus_row)
        
        if not jatelaji:
            logger.warning(
                f"Tuntematon jätelaji: {kuljetus_row.jatteen_kuvaus} / "
                f"{kuljetus_row.lietteen_tyyppi}"
            )
            return None
        
        # Muunna tilavuus m³ -> litroiksi
        tilavuus_litraa = None
        if kuljetus_row.jatteen_tilavuus_m3:
            tilavuus_litraa = int(kuljetus_row.jatteen_tilavuus_m3 * 1000)
        
        # Muunna paino tonneista kilogrammoiksi
        massa_kg = None
        if kuljetus_row.jatteen_paino_t:
            massa_kg = int(kuljetus_row.jatteen_paino_t * 1000)
        
        tapahtuma = Tyhjennystapahtuma(
            alkupvm=kuljetus_row.siirron_alkamisaika,
            loppupvm=kuljetus_row.siirron_paattymisaika or kuljetus_row.siirron_alkamisaika,
            jatelaji=jatelaji,
            tyhjennyskerrat=1,  # LIETE-datassa yksi rivi = yksi kuljetus
            tilavuus=tilavuus_litraa,
            massa=massa_kg,
            lietteentyhjennyspaiva=kuljetus_row.siirron_alkamisaika,  # LIETE: tyhjennyspäivä = siirron alkamisaika
            jatteen_kuvaus=kuljetus_row.jatteen_kuvaus,  # LAH-449: Jätteen kuvaus (keräysvälinetyyppi)
        )
        
        return tapahtuma
    
    def _map_jatelaji(self, kuljetus_row: LieteKuljetusRow) -> Optional[JkrJatelaji]:
        """
        Kartoittaa LIETE-jätetyypin JKR-jätelajiksi.
        
        Määrittelyn mukaan (17.11.2025):
        - Jätelaji määräytyy "Lietteen tyyppi" -kentästä (Musta, Harmaa, Ei tietoa)
        - "Jätteen kuvaus" (Umpisäiliö, Saostussäiliö, Pienpuhdistamo) on keräysvälinetyyppi
        
        Args:
            kuljetus_row: LIETE-kuljetusrivi
            
        Returns:
            JkrJatelaji
        """
        # Käytä lietteen tyyppiä jätelajin määrittämiseen
        if kuljetus_row.lietteen_tyyppi:
            jatelaji = LIETE_JATELAJI_MAP.get(kuljetus_row.lietteen_tyyppi)
            if jatelaji:
                return jatelaji
        
        # Oletus: yleinen liete
        return JkrJatelaji.liete
