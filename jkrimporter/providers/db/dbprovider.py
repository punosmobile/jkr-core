import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from sqlalchemy import text, or_
from sqlalchemy.orm import Session

from jkrimporter.conf import get_kohdentumattomat_siirtotiedosto_filename
from jkrimporter.datasheets import get_siirtotiedosto_headers
from jkrimporter.model import (
    Asiakas,
    JkrData,
    JkrIlmoitukset,
    Paatos,
    LopetusIlmoitus,
    KeraysvalineTyyppi,
)
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.ilmoitus import (
    export_kohdentumattomat_ilmoitukset,
    export_kohdentumattomat_lieteIlmoitukset,
    export_kohdentumattomat_lopetusilmoitukset
)
from jkrimporter.utils.intervals import IntervalCounter
from jkrimporter.utils.liete import export_kohdentumattomat_liete_kuljetukset
from jkrimporter.utils.paatos import export_kohdentumattomat_paatokset
from jkrimporter.utils.kaivotieto import (
    export_kohdentumattomat_kaivotiedot,
    export_kohdentumattomat_kaivotiedon_lopetukset,
)
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import get_code_id, init_code_objects, keraysvalinetyypit
from .database import engine
from .models import (
    AKPPoistoSyy,
    Jatetyyppi,
    Kompostori,
    KompostorinKohteet,
    Kuljetus,
    Paatostulos,
    Tapahtumalaji,
    Tiedontuottaja,
    Viranomaispaatokset,
    DVVPoimintaPvm,
    Keraysvaline,
    KohteenRakennukset
)
from .services.buildings import counts as building_counts
from .services.buildings import (
    find_buildings_for_kohde,
    find_osoite_by_prt,
    find_single_building_id_by_prt,
    find_active_buildings_with_moved_residents_or_owners,
    find_inactive_buildings,
    RakennusData
)
from .services.dvv_poimintapvm import (
    find_last_dvv_poiminta
)
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_perusmaksurekisteri_kohteet,
    find_kohde_by_prt,
    find_kohteet_by_prt,
    get_or_create_multiple_and_uninhabited_kohteet,
    check_and_update_old_other_building_kohde_kohdetyyppi,
    get_or_create_single_asunto_kohteet,
    get_ulkoinen_asiakastieto,
    remove_buildings_from_kohde,
    update_kohde,
    update_ulkoinen_asiakastieto,
)
from .services.kaivotieto import (
    find_kohde_by_single_prt,
    find_existing_kaivotieto_by_type,
    get_kaivotietotyyppi_id,
    insert_kaivotieto,
    update_kaivotieto_loppupvm,
)
from ..lahti.viemaritiedosto import (
    export_kohdentumattomat_viemariilmoitukset,
    export_kohdentumattomat_viemarilopetusilmoitukset
)

from .services.viemariliitos import (
    insert_viemariliitos,
    update_viemariliitos_loppupvm,
    find_existing_viemariliitos
)
from .services.osapuoli import (
    create_or_update_haltija_osapuoli,
    create_or_update_komposti_yhteyshenkilo,
    should_remove_from_kohde_via_asukas,
    should_remove_from_kohde_via_omistaja,
)
from .services.sopimus import update_sopimukset_for_kohde

logger = logging.getLogger(__name__)


def count(jkr_data: JkrData):
    prt_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)
    kitu_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)
    address_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)

    for asiakas in jkr_data.asiakkaat.values():
        for prt in asiakas.rakennukset:
            prt_counts[prt].append(asiakas.voimassa)
        for kitu in asiakas.kiinteistot:
            kitu_counts[kitu].append(asiakas.voimassa)
        # this just saves all the buildings with the same address string together
        addr = asiakas.haltija.osoite.osoite_rakennus()
        if addr:
            address_counts[addr].append(asiakas.voimassa)

    return prt_counts, kitu_counts, address_counts


def insert_kuljetukset(
    session,
    kohde,
    tyhjennystapahtumat: List[JkrTyhjennystapahtuma],
    raportointi_alkupvm: Optional[date],
    raportointi_loppupvm: Optional[date],
    urakoitsija: Tiedontuottaja,
):
    for tyhjennys in tyhjennystapahtumat:
        print("importing tyhjennys")
        print(tyhjennys)
        if not tyhjennys.alkupvm:
            # In many cases, only one date is known for tyhjennys. Looks like
            # in those cases the date is marked as the end date.
            alkupvm = tyhjennys.loppupvm or raportointi_alkupvm
        else:
            alkupvm = tyhjennys.alkupvm
        loppupvm = tyhjennys.loppupvm or raportointi_loppupvm

        jatetyyppi = codes.jatetyypit[tyhjennys.jatelaji]
        if not jatetyyppi:
            logger.warning(
                f"Ohitetaan tyhjennystapahtuma. Jätetyyppi "
                f"'{tyhjennys.jatelaji}' unknown"
            )
            continue
        if tyhjennys.jatelaji not in codes.KiinteatJatelajit:
            massa = None
        else:
            massa = tyhjennys.massa

        exists = any(
            k.jatetyyppi == jatetyyppi
            and k.alkupvm == alkupvm
            and k.loppupvm == loppupvm
            for k in kohde.kuljetus_collection
        )

        if not exists:
            db_kuljetus = Kuljetus(
                kohde=kohde,
                jatetyyppi=jatetyyppi,
                alkupvm=alkupvm,
                loppupvm=loppupvm,
                tyhjennyskerrat=tyhjennys.tyhjennyskerrat,
                massa=massa,
                tilavuus=tyhjennys.tilavuus,
                tiedontuottaja=urakoitsija,
                lietteentyhjennyspaiva=tyhjennys.lietteentyhjennyspaiva,
                jatteen_kuvaus=tyhjennys.jatteen_kuvaus,  # LAH-449: Jätteen kuvaus
            )
            session.add(db_kuljetus)


def find_and_update_kohde(session, asiakas, do_update_kohde, prt_counts, kitu_counts, address_counts):
    """
    Etsii olemassa olevan kohteen asiakkaalle tai luo uuden.
    """
    kohde = None

    # 1. Etsi kohde rakennustietojen perusteella
    print("Searching for kohde by customer data...")
    if asiakas.rakennukset:
        kohde = find_kohde_by_prt(session, asiakas)

    if kohde and do_update_kohde:
        print("Kohde found, updating dates...")
        update_kohde(kohde, asiakas)

    if kohde:
        add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)
    else:
        print("Could not find kohde.")

    if not kohde:
        print("trying to find via customer id.")
        ulkoinen_asiakastieto = get_ulkoinen_asiakastieto(session, asiakas.asiakasnumero)

        # 2. Etsi kohde asiakasnumeron perusteella
        if ulkoinen_asiakastieto:
            print("Kohde found by customer id.")

            kohde = ulkoinen_asiakastieto.kohde
            if do_update_kohde:
                update_kohde(kohde, asiakas)

    return kohde


def set_end_dates_to_kohteet(
    session: Session,
    poimintapvm: date,
):
    previous_pvm = poimintapvm - timedelta(days=1)
    add_date_query = text(
        "UPDATE jkr.kohde SET loppupvm = :loppu_pvm WHERE loppupvm IS NULL"
    )
    session.execute(add_date_query, {"loppu_pvm": previous_pvm.strftime("%Y-%m-%d")})
    session.commit()


def import_asiakastiedot(
    session: Session,
    asiakas: Asiakas,
    alkupvm: Optional[date],
    loppupvm: Optional[date],
    urakoitsija: Tiedontuottaja,
    do_update_contact: bool,
    do_update_kohde: bool,
    prt_counts: Dict[str, IntervalCounter],
    kitu_counts: Dict[str, IntervalCounter],
    address_counts: Dict[str, IntervalCounter],
):

    kohde = find_and_update_kohde(
        session,
        asiakas,
        do_update_kohde,
        prt_counts,
        kitu_counts,
        address_counts,
    )
    if not kohde:
        print(f"Could not find kohde for asiakas {asiakas}, skipping...")
        return asiakas

    # Update osapuolet from the same tiedontuottaja. This function will not
    # touch data from other tiedontuottajat.
    create_or_update_haltija_osapuoli(session, kohde, asiakas, do_update_contact)

    update_sopimukset_for_kohde(session, kohde, asiakas, loppupvm, urakoitsija)
    insert_kuljetukset(
        session,
        kohde,
        asiakas.tyhjennystapahtumat,
        alkupvm,
        loppupvm,
        urakoitsija,
    )

    session.commit()


def import_dvv_kohteet(
    session: Session,
    poimintapvm: Optional[date],
    loppupvm: Optional[date] = None,
    perusmaksutiedosto: Optional[Path] = None,
) -> None:
    """
    Luo kohteet DVV rakennustiedoista määritysten mukaisessa järjestyksessä.
    
    Kohteiden luontijärjestys:
    1. Perusmaksurekisterin kohteet (rivitalot, kerrostalot jne.)
    2. Yhden asunnon kohteet (omakotitalot, paritalot)
    3. Kaikki jäljellä olevat kohteet
    
    Args:
        session: Tietokantaistunto
        poimintapvm: Uusien kohteiden alkupäivämäärä ja vanhojen loppupäivämäärä-1
        loppupvm: Uusien kohteiden loppupäivämäärä (None = ei loppupäivää)
        perusmaksutiedosto: Polku perusmaksurekisterin Excel-tiedostoon
    """
    logger = logging.getLogger(__name__)
    print("Aloitetaan DVV-kohteiden luonti...")
    logger.info("\nAloitetaan DVV-kohteiden luonti...")

    # # Aseta loppupäivämäärä olemassa oleville kohteille ilman loppupäivää
    # if poimintapvm is not None:
    #     previous_pvm = poimintapvm - timedelta(days=1)
    #     print(f"Asetetaan loppupäivämäärä {previous_pvm} vanhoille kohteille...")
    #     logger.info(f"Asetetaan loppupäivämäärä {previous_pvm} vanhoille kohteille...")

    #     add_date_query = text(
    #         """
    #         UPDATE jkr.kohde
    #         SET loppupvm = :loppu_pvm
    #         WHERE (loppupvm IS NULL OR loppupvm > :loppu_pvm)
    #         AND alkupvm < :loppu_pvm
    #         """
    #     )
    #     session.execute(add_date_query, {"loppu_pvm": previous_pvm.strftime("%Y-%m-%d")})
    #     session.commit()
    #     print("Loppupäivämäärät asetettu")
    #     logger.info("Loppupäivämäärät asetettu")

    # 1. Perusmaksurekisterin kohteet (jos tiedosto annettu)
    if perusmaksutiedosto:
        print(f"\nLuodaan perusmaksurekisterin kohteet...")
        logger.info("\nLuodaan perusmaksurekisterin kohteet...")
        try:
            perusmaksukohteet = create_perusmaksurekisteri_kohteet(
                session, perusmaksutiedosto, poimintapvm, loppupvm
            )
            session.commit()
            print(
                f"Luotu {len(perusmaksukohteet)} kohdetta perusmaksurekisterin perusteella"
            )
            logger.info(
                f"Luotu {len(perusmaksukohteet)} kohdetta perusmaksurekisterin perusteella"
            )
        except Exception as e:
            print(f"Virhe perusmaksurekisterin käsittelyssä: {str(e)}")
            logger.error(f"Virhe perusmaksurekisterin käsittelyssä: {str(e)}")
            raise
    else:
        print(f"Ei perusmaksurekisteritiedostoa, ohitetaan vaihe 1")
        logger.info("Ei perusmaksurekisteritiedostoa, ohitetaan vaihe 1")

    print("Päätetään vanhat kohteet ennen uusien luomista")
    # Haetaan rakennukset, joita ei enää löydy aineistoista
    poistettavat_paattyneet_rakennukset = find_inactive_buildings(session)
    print(f"Löydettiin {len(poistettavat_paattyneet_rakennukset)} päättynyttä rakennusta")

    poistettavat_rakennukset: list[RakennusData] = poistettavat_paattyneet_rakennukset

    # Haetaan rakennukset, joiden omistajat tai asukkaat ovat vaihtuneet kohteilta
    tarkistettava_rakennus_id_lists = find_active_buildings_with_moved_residents_or_owners(session)
    print(f"Tarkistetaan {len(tarkistettava_rakennus_id_lists['asukasRakennukset'])} asukasta vaihtanutta rakennusta")

    # Asukaspohjaiset päätökset
    pysyvat_rakennukset_asukastiedolla: list[RakennusData] = []
    dvv_poimintapvm: date | None = None
    if len(tarkistettava_rakennus_id_lists['asukasRakennukset'] + tarkistettava_rakennus_id_lists['omistajaRakennukset']) > 0:
        dvv_poimintapvm = find_last_dvv_poiminta(session)


    for rakennus in tarkistettava_rakennus_id_lists['asukasRakennukset']:
        # Tarkastetaan kunkin rakennuksen asukastietojen muutokset
        if should_remove_from_kohde_via_asukas(session, rakennus["id"], poimintapvm, dvv_poimintapvm):
            poistettavat_rakennukset.append(rakennus)
        else:
            pysyvat_rakennukset_asukastiedolla.append(rakennus)

    print(f"Tarkistetaan {len(tarkistettava_rakennus_id_lists['omistajaRakennukset'])} omistajaa vaihtanutta rakennusta")

    # Omistajapohjaiset päätökset
    pysyvat_rakennukset_omistajatiedolla = []
    poistettavat_rakennukset_omistaja: list[RakennusData] = []
    for rakennus in tarkistettava_rakennus_id_lists['omistajaRakennukset']:
        # Tarkastetaan kunkin rakennuksen omistajatietojen muutokset
        if should_remove_from_kohde_via_omistaja(session, rakennus["id"], poimintapvm, dvv_poimintapvm):
            poistettavat_rakennukset_omistaja.append(rakennus)
        else:
            pysyvat_rakennukset_omistajatiedolla.append(rakennus)

    print(f"{len(poistettavat_rakennukset)} asukas ja  {len(poistettavat_rakennukset_omistaja)} omistaja rakennusta on poistumassa kohteiltaan")
    print(f"{len(pysyvat_rakennukset_asukastiedolla) + len(pysyvat_rakennukset_omistajatiedolla)} tarkastelluista rakennuksista pysyy kohteillaan")

    # Poistetaan rakennukset kohteilta asukas tai omistajapohjaisesti
    asukas_kohde_list: List[KohteenRakennukset] = []
    omistaja_kohde_list: List[KohteenRakennukset] = []
    if len(poistettavat_rakennukset) > 0:
        asukas_kohde_list = remove_buildings_from_kohde(session, poistettavat_rakennukset, 'asukas', poimintapvm)
    if len(poistettavat_rakennukset_omistaja) > 0:
        omistaja_kohde_list = remove_buildings_from_kohde(session, poistettavat_rakennukset_omistaja, 'omistaja', poimintapvm)

    # Otetaan yhteinen lista poistetuista rakennuksista kohteineen
    poistettujen_rakennusten_kohteet = asukas_kohde_list + omistaja_kohde_list

    session.commit()

    # 2. Yhden asunnon kohteet (omakotitalot ja paritalot)
    logger.info("\nLuodaan yhden asunnon kohteet...")
    print("\nLuodaan yhden asunnon kohteet...")

    single_asunto_kohteet = get_or_create_single_asunto_kohteet(
        session, poimintapvm, loppupvm, poistettujen_rakennusten_kohteet
    )
    session.commit()
    logger.info(f"Luotu {len(single_asunto_kohteet)} yhden asunnon kohdetta")
    print(f"Luotu {len(single_asunto_kohteet)} yhden asunnon kohdetta")

    # 3. Muut kohteet (kaikki loput rakennukset)
    logger.info("\nLuodaan loput kohteet...")
    print("\nLuodaan loput kohteet...")
    multiple_and_uninhabited_kohteet = get_or_create_multiple_and_uninhabited_kohteet(
        session, poimintapvm, loppupvm, poistettujen_rakennusten_kohteet
    )
    session.commit()
    logger.info(f"Luotu {len(multiple_and_uninhabited_kohteet)} muuta kohdetta")
    print(f"Luotu {len(multiple_and_uninhabited_kohteet)} muuta kohdetta")

    # 4. Vanhat yhden rakennuksen kohteet
    paivitetut_rakennus_kohteet = check_and_update_old_other_building_kohde_kohdetyyppi(session, poimintapvm)
    session.commit()

    # Yhteenveto
    total_kohteet = (
        (len(perusmaksukohteet) if 'perusmaksukohteet' in locals() else 0) +
        len(single_asunto_kohteet) + 
        len(multiple_and_uninhabited_kohteet)
    )

    # Tallennetaan uusin DVV-poimintaPVM tietokantaan seuraavalle käsittelylle
    db_dvv_pomintapvvm = DVVPoimintaPvm(
        poimintapvm=poimintapvm
    )
    print(f"\nSaving poimintapvm: {db_dvv_pomintapvvm.poimintapvm}")
    session.add(db_dvv_pomintapvvm)
    session.commit()

    print(f"\nDVV-kohteiden luonti valmis. Luotu yhteensä {total_kohteet} kohdetta ja päivitetty {len(paivitetut_rakennus_kohteet)} vanhaa kohdetta")
    logger.info(f"\nDVV-kohteiden luonti valmis. Luotu yhteensä {total_kohteet} kohdetta.")


class DbProvider:
    def write(
        self,
        jkr_data: JkrData,
        tiedontuottaja_lyhenne: str,
        ala_paivita_yhteystietoja: bool,
        ala_paivita_kohdetta: bool,
        siirtotiedosto: Path,
    ):
        try:
            kohdentumattomat = []
            print(len(jkr_data.asiakkaat))
            progress = Progress(len(jkr_data.asiakkaat))

            prt_counts, kitu_counts, address_counts = count(jkr_data)
            with Session(engine) as session:
                init_code_objects(session)

                tiedoston_tuottaja = session.get(Tiedontuottaja, tiedontuottaja_lyhenne)

                # The same tiedontuottaja may contain data from multiple
                # urakoitsijat. Create all urakoitsijat in the db first.
                print("Importoidaan urakoitsijat")
                urakoitsijat: Set[str] = set()
                for asiakas in jkr_data.asiakkaat.values():
                    if asiakas.asiakasnumero.jarjestelma not in urakoitsijat:
                        print(f"found urakoitsija {asiakas.asiakasnumero.jarjestelma}")
                        urakoitsijat.add(asiakas.asiakasnumero.jarjestelma)
                tiedontuottajat: Dict[str, Tiedontuottaja] = {}
                for urakoitsija_tunnus in urakoitsijat:
                    print("checking or adding urakoitsija")
                    tiedontuottaja = session.get(Tiedontuottaja, urakoitsija_tunnus)
                    print(tiedontuottaja)
                    if not tiedontuottaja:
                        print("not found, adding")
                        tiedontuottaja = Tiedontuottaja(
                            # let's create the urakoitsijat using only y-tunnus for now.
                            # We can create tiedontuottaja-nimi maps later.
                            tunnus=urakoitsija_tunnus,
                            nimi=urakoitsija_tunnus,
                        )
                        session.add(tiedontuottaja)
                    tiedontuottajat[urakoitsija_tunnus] = tiedontuottaja
                session.commit()

                print("Importoidaan asiakastiedot")
                for asiakas in jkr_data.asiakkaat.values():
                    print("---------")
                    print("importing")
                    print(asiakas)
                    progress.tick()

                    # Asiakastieto may come from different urakoitsija than the
                    # immediate tiedontuottaja. In such a case, the asiakas
                    # information takes precedence.
                    urakoitsija_tunnus = asiakas.asiakasnumero.jarjestelma

                    kohdentumaton = import_asiakastiedot(
                        session,
                        asiakas,
                        jkr_data.alkupvm,
                        jkr_data.loppupvm,
                        tiedontuottajat[urakoitsija_tunnus],
                        not ala_paivita_yhteystietoja,
                        not ala_paivita_kohdetta,
                        prt_counts,
                        kitu_counts,
                        address_counts,
                    )
                    if kohdentumaton:
                        asiakas_dict = kohdentumaton.__dict__
                        kohdentumattomat.append(asiakas_dict)
                session.commit()
                progress.complete()

                if kohdentumattomat:
                    kohdentumattomatRivit = 0
                    csv_path = None
                    
                    for kohdentumaton in kohdentumattomat:

                        # Rebuild rows to insert into the error .csv
                        rows = []
                        
                        # Tarkista onko ulkoinen_asiakastieto dict vai LIETE-data
                        ulkoinen = kohdentumaton["ulkoinen_asiakastieto"]
                        if isinstance(ulkoinen, dict):
                            # Dict-muotoinen data
                            # Ohitetaan kohdentumattomien tallennus, koska rakenne on erilainen
                            logger.warning(
                                f"Ohitetaan kohdentumattoman tiedon tallennus: "
                                f"ulkoinen_asiakastieto on dict-muodossa"
                            )
                            continue
                        
                        # Tarkista onko Lahden siirtotiedoston rivi (jolla on kaynnit-attribuutti)
                        if not hasattr(ulkoinen, 'kaynnit'):
                            # LIETE-data tai muu data jolla ei ole kaynnit-attribuuttia
                            logger.warning(
                                f"Ohitetaan kohdentumattoman tiedon tallennus: "
                                f"ulkoinen_asiakastieto ei ole Lahden siirtotiedoston rivi "
                                f"(tyyppi: {type(ulkoinen).__name__})"
                            )
                            continue
                        
                        for ii, _ in enumerate(
                            kohdentumaton["ulkoinen_asiakastieto"].kaynnit
                        ):
                            row_data = {
                                "UrakoitsijaId": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].UrakoitsijaId,
                                "UrakoitsijankohdeId": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].UrakoitsijankohdeId,
                                "Kiinteistotunnus": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kiinteistotunnus,
                                "Kiinteistonkatuosoite": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kiinteistonkatuosoite,
                                "Kiinteistonposti": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kiinteistonposti,
                                "Haltijannimi": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Haltijannimi,
                                "Haltijanyhteyshlo": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Haltijanyhteyshlo,
                                "Haltijankatuosoite": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Haltijankatuosoite,
                                "Haltijanposti": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Haltijanposti,
                                "Haltijanmaakoodi": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Haltijanmaakoodi,
                                "Pvmalk": kohdentumaton["voimassa"].lower.strftime(
                                    "%d.%m.%Y"
                                ),
                                "Pvmasti": kohdentumaton["voimassa"].upper.strftime(
                                    "%d.%m.%Y"
                                ),
                                "tyyppiIdEWC": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].tyyppiIdEWC,
                                "COUNT(kaynnit)": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].kaynnit[ii],
                                "SUM(astiamaara)": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].astiamaara,
                                "koko": kohdentumaton["ulkoinen_asiakastieto"].koko,
                                "SUM(paino)": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].paino[ii],
                                "tyhjennysvali": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].tyhjennysvali[
                                    ii * 2
                                ],  # two tyhjennysvalis per row
                                "kertaaviikossa": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].kertaaviikossa[ii * 2],
                                "Voimassaoloviikotalkaen": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotalkaen[ii * 2],
                                "Voimassaoloviikotasti": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotasti[ii * 2],
                                "palveluKimppakohdeId": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].palveluKimppakohdeId,
                                "KimpanNimi": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].kimpanNimi,
                                "Kimpanyhteyshlo": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kimpanyhteyshlo,
                                "Kimpankatuosoite": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kimpankatuosoite,
                                "Kimpanposti": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kimpanposti,
                                "Kuntatun": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Kuntatun,
                                "Keskeytysalkaen": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Keskeytysalkaen,
                                "Keskeytysasti": kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Keskeytysasti,
                            }
                            if (
                                kohdentumaton["ulkoinen_asiakastieto"].tyhjennysvali[
                                    ii * 2 + 1
                                ]
                                is not None
                            ):
                                row_data["tyhjennysvali2"] = kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].tyhjennysvali[ii * 2 + 1]
                            if (
                                kohdentumaton["ulkoinen_asiakastieto"].kertaaviikossa[
                                    ii * 2 + 1
                                ]
                                is not None
                            ):
                                row_data["kertaaviikossa2"] = kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].kertaaviikossa[ii * 2 + 1]
                            if (
                                kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotalkaen[ii * 2 + 1]
                                is not None
                            ):
                                row_data["Voimassaoloviikotalkaen2"] = kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotalkaen[ii * 2 + 1]
                            if (
                                kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotasti[ii * 2 + 1]
                                is not None
                            ):
                                row_data["Voimassaoloviikotasti2"] = kohdentumaton[
                                    "ulkoinen_asiakastieto"
                                ].Voimassaoloviikotasti[ii * 2 + 1]
                            rows.append(row_data)
                            

                        csv_path = (
                            siirtotiedosto
                            / get_kohdentumattomat_siirtotiedosto_filename()
                        )
                        with open(
                            csv_path, mode="a", encoding="cp1252", newline=""
                        ) as csv_file:
                            csv_writer = csv.DictWriter(
                                csv_file,
                                fieldnames=get_siirtotiedosto_headers(),
                                delimiter=";",
                                quotechar='"',
                            )
                            for rd in rows:
                                kohdentumattomatRivit = kohdentumattomatRivit + 1
                                csv_writer.writerow(rd)

                    if csv_path and kohdentumattomatRivit > 0:
                        print(f"Kohdentumattomat tiedot ({len(kohdentumattomat)}) kpl eli käynteineen {kohdentumattomatRivit} riviä lisätty CSV-tiedostoon: {csv_path}")
                    elif kohdentumattomatRivit == 0 and kohdentumattomat:
                        # LIETE-data tai muu data jota ei voitu tallentaa Lahden muodossa
                        print(f"Kohdentumattomia tietoja ({len(kohdentumattomat)}) kpl, tallennetaan erilliseen tiedostoon")
                        try:
                            # Käytä siirtotiedoston hakemistoa, ei tiedostoa itseään
                            output_dir = os.path.dirname(str(siirtotiedosto)) if siirtotiedosto else "."
                            export_kohdentumattomat_liete_kuljetukset(
                                output_dir, kohdentumattomat
                            )
                        except Exception as export_error:
                            logger.exception(f"LIETE-kohdentumattomien tallennus epäonnistui: {export_error}")
                else:
                    print("Ei kohdentumattomia tietoja.")

        except Exception as e:
            logger.exception(e)
            raise
        finally:
            logger.debug(building_counts)

    def write_dvv_kohteet(
        self,
        poimintapvm: Optional[datetime.date],
        loppupvm: Optional[datetime.date],
        perusmaksutiedosto: Optional[Path],
    ):
        """
        This method creates kohteet from dvv data existing in the database.

        Optionally, a perusmaksurekisteri xlsx file may be provided to
        combine dvv buildings with the same customer id.
        """
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Luodaan kohteet")
                import_dvv_kohteet(session, poimintapvm, loppupvm, perusmaksutiedosto)

        except Exception as e:
            logger.exception(e)
            raise
        finally:
            logger.debug(building_counts)

    def write_ilmoitukset(
            self,
            ilmoitus_list: List[JkrIlmoitukset],
            ilmoitustiedosto: Path,
    ):  
        """
        This method creates Kompostori and KompostorinKohteet from ilmoitus data.
        The method also stores kohdentumattomat rows.
        """
        kohdentumattomat = []
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Importoidaan ilmoitukset")
                kohteet = []
                for ilmoitus in ilmoitus_list:
                    print("\n ---------- \n")
                    kompostorin_kohde = find_kohde_by_prt(session, ilmoitus)
                    if kompostorin_kohde:
                        print(f"Kompostorin kohde: {kompostorin_kohde.id} prt: {ilmoitus.prt}")
                        osapuoli = create_or_update_komposti_yhteyshenkilo(
                            session, kompostorin_kohde, ilmoitus
                        )
                        osoite_id = find_osoite_by_prt(session, ilmoitus)
                        if not osoite_id:
                            print(
                                "Ei löytynyt osoite_id:tä rakennus: "
                                + f"{ilmoitus.prt}"
                            )
                            kohdentumattomat.append(ilmoitus.rawdata)
                            continue
                        # There should never be identical Kompostori
                        existing_kompostori = session.query(Kompostori).filter(
                            Kompostori.alkupvm == ilmoitus.alkupvm,
                            Kompostori.loppupvm == ilmoitus.loppupvm,
                            Kompostori.osoite_id == osoite_id,
                            Kompostori.onko_kimppa == ilmoitus.onko_kimppa,
                            Kompostori.osapuoli_id == osapuoli.id,
                            or_(
                                Kompostori.onko_liete.is_(False),
                                Kompostori.onko_liete.is_(None),
                            ),
                        ).first()
                        if existing_kompostori:
                            print("Vastaava kompostori löydetty, ohitetaan luonti...")
                            komposti = existing_kompostori
                        # Based on the comments on 23.2.2024, do not set ending dates
                        # for Kompostori if new ilmoitus with the same vastuuhenkilo and
                        # sijainti is added, even if the dates are different. Only set
                        # end dates when lopetus ilmoitus is added.
                        else:
                            print("Lisätään uusi kompostori...")
                            komposti = Kompostori(
                                alkupvm=ilmoitus.alkupvm,
                                loppupvm=ilmoitus.loppupvm,
                                osoite_id=osoite_id,
                                onko_kimppa=ilmoitus.onko_kimppa,
                                osapuoli=osapuoli,
                            )
                            session.add(komposti)
                        # Look for kohde for each kompostoija.
                        kohteet, kohdentumattomat_prt = find_kohteet_by_prt(
                            session,
                            ilmoitus
                        )

                        print(f"Käsiteltävän kompostorin id: {komposti.id}")
                        if kohteet:
                            for kohde in kohteet:
                                existing_kohde = session.query(
                                    KompostorinKohteet).filter(
                                        KompostorinKohteet.kompostori_id == komposti.id,
                                        KompostorinKohteet.kohde_id == kohde.id
                                ).first()
                                if existing_kohde:
                                    print(f"Kohde {kohde.id} on jo kompostorin {komposti.id} kohteissa...")
                                else:
                                    print(f"Lisätään kohde {kohde.id} kompostorin {komposti.id} kohteisiin...")
                                    session.add(
                                        KompostorinKohteet(
                                            kompostori=komposti,
                                            kohde=kohde
                                        ),
                                    )
                        if kohdentumattomat_prt:
                            # Append rawdata dicts for each kohdentumaton kompostoija.
                            print(f"Kohdentumatta jäi {len(kohdentumattomat_prt)} kompostoria")
                            for prt in kohdentumattomat_prt:
                                print(prt)
                                for rawdata in ilmoitus.rawdata:
                                    if rawdata.get(
                                        "1. Kompostoria käyttävän rakennuksen tiedot:Käsittelijän lisäämä tunniste"
                                    ) == prt:
                                        kohdentumattomat.append(rawdata)
                    else:
                        # Append each rawdata dict.
                        for rawdata in ilmoitus.rawdata:
                            kohdentumattomat.append(rawdata)
                session.commit()
        except Exception as e:
            logger.exception(e)
            raise

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat ilmoitukset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_ilmoitukset(
                os.path.dirname(ilmoitustiedosto), kohdentumattomat
            )


    def write_lieteIlmoitukset(
            self,
            lieteIlmoitus_list: List[JkrIlmoitukset],
            ilmoitustiedosto: Path
    ):
        """
        This method creates new liete kompostori entries based on data.
        The method also stores kohdentumattomat rows.
        """
        kohdentumattomat = []
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Importoidaan lieteilmoitukset")
                for ilmoitus in lieteIlmoitus_list:
                    kompostorin_kohde = find_kohde_by_prt(session, ilmoitus)

                    if kompostorin_kohde:
                        print(f"Liete kompostorin kohde: {kompostorin_kohde.id} prt: {ilmoitus.prt}")
                        osapuoli = create_or_update_komposti_yhteyshenkilo(
                            session, kompostorin_kohde, ilmoitus
                        )
                        osoite_id = find_osoite_by_prt(session, ilmoitus)
                        if not osoite_id:
                            print(
                                "Ei löytynyt osoite_id:tä rakennus: "
                                + f"{ilmoitus.prt}"
                            )

                        # There should never be identical Kompostori
                        existing_kompostori = session.query(Kompostori).filter(
                            Kompostori.alkupvm == ilmoitus.alkupvm,
                            Kompostori.loppupvm == ilmoitus.loppupvm,
                            Kompostori.osoite_id == osoite_id,
                            Kompostori.osapuoli_id == osapuoli.id,
                            Kompostori.onko_liete is True,
                        ).first()
                        if existing_kompostori:
                            print("Vastaava liete kompostori löydetty, ohitetaan luonti...")
                            komposti = existing_kompostori
                        # Based on the comments on 23.2.2024, do not set ending dates
                        # for Kompostori if new ilmoitus with the same vastuuhenkilo and
                        # sijainti is added, even if the dates are different. Only set
                        # end dates when lopetus ilmoitus is added.
                        else:
                            print("Lisätään uusi liete kompostori...")
                            komposti = Kompostori(
                                alkupvm=ilmoitus.alkupvm,
                                loppupvm=ilmoitus.loppupvm,
                                osoite_id=osoite_id,
                                onko_liete=True,
                                osapuoli=osapuoli,
                            )
                            session.add(komposti)
                        # Look for kohde for each kompostoija.
                        kohteet, kohdentumattomat_prt = find_kohteet_by_prt(
                            session,
                            ilmoitus
                        )

                        print(f"Käsiteltävän kompostorin id: {komposti.id}")
                        if kohteet:
                            for kohde in kohteet:
                                existing_kohde = session.query(
                                    KompostorinKohteet).filter(
                                        KompostorinKohteet.kompostori_id == komposti.id,
                                        KompostorinKohteet.kohde_id == kohde.id
                                ).first()
                                if existing_kohde:
                                    print(f"Kohde {kohde.id} on jo kompostorin {komposti.id} kohteissa...")
                                else:
                                    print(f"Lisätään kohde {kohde.id} kompostorin {komposti.id} kohteisiin...")
                                    session.add(
                                        KompostorinKohteet(
                                            kompostori=komposti,
                                            kohde=kohde
                                        ),
                                    )
                                
                                print("creating new väline")
                                keraysvaline_id = codes.keraysvalinetyypit.get(KeraysvalineTyyppi.PIENPUHDISTAMO)

                                existing_keraysvaline = session.query(
                                    Keraysvaline).filter(
                                        Keraysvaline.kohde_id == kohde.id,
                                        Keraysvaline.keraysvalinetyyppi_id == keraysvaline_id.id
                                ).first()

                                if existing_keraysvaline:
                                    print(f"Kohteella {kohde.id} on jo PIENPUHDISTAMO, ohitetaan luonti...")
                                    continue

                                db_keraysvaline = Keraysvaline(
                                    pvm=ilmoitus.pienpuhdistamo_alkupwm,
                                    keraysvalinetyyppi=keraysvaline_id,
                                    tilavuus=0,
                                    maara=0,
                                    kohde_id=kohde.id,
                                )
                                print(f"Kohteelle {kohde.id} lisätty PIENPUHDISTAMO")

                                session.add(db_keraysvaline)

                        if kohdentumattomat_prt:
                            # Append rawdata dicts for each kohdentumaton kompostoija.
                            print(f"Kohdentumatta jäi {len(kohdentumattomat_prt)} liete kompostoria")
                            for prt in kohdentumattomat_prt:
                                print(prt)
                                for rawdata in ilmoitus.rawdata:
                                    if rawdata.get(
                                        "Tiedot kiinteistöstä, jonka liete kompostoidaan:Käsittelijän lisäämä tunniste"
                                    ) == prt:
                                        kohdentumattomat.append(rawdata)

                session.commit()
        except Exception as e:
            logger.exception(e)
            raise

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat lieteilmoitukset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_lieteIlmoitukset(
                os.path.dirname(ilmoitustiedosto), kohdentumattomat
            )

    def write_lopetusilmoitukset(
            self,
            lopetusilmoitus_list: List[LopetusIlmoitus],
            ilmoitustiedosto: Path,
    ):
        """
        This method sets end dates for Kompostori based on lopetusilmoitus data.
        The method also stores kohdentumattomat rows.
        """
        kohdentumattomat = []
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Importoidaan lopetusilmoitukset")
                for ilmoitus in lopetusilmoitus_list:
                    kompostorin_kohde = find_kohde_by_prt(session, ilmoitus)
                    if kompostorin_kohde:
                        osoite_id = find_osoite_by_prt(session, ilmoitus)
                        if not osoite_id:
                            print(
                                "Ei löytynyt osoite_id:tä rakennukselle: "
                                + f"{ilmoitus.prt}"
                            )
                            kohdentumattomat.append(ilmoitus.rawdata)
                            continue
                        ending_kompostorit = session.query(Kompostori).filter(
                            # Get all Kompostori, with the osoite_id, and starting date
                            # earlier and ending date greater than lopetusilmoitus date.
                            Kompostori.osoite_id == osoite_id,
                            Kompostori.alkupvm < ilmoitus.Vastausaika,
                            Kompostori.loppupvm > ilmoitus.Vastausaika
                        ).all()
                        if ending_kompostorit:
                            print(
                                f"Lopetettavia kompostoreita löytynyt {len(ending_kompostorit)} kpl."
                            )
                            for kompostori in ending_kompostorit:
                                kompostori.loppupvm = ilmoitus.Vastausaika
                            session.commit()
                        else:
                            print("Lopetettavia voimassaolevia kompostoreita ei löytynyt...")
                    else:
                        print(f"Kohdetta ei löytynyt rakennuksella: {ilmoitus.prt}")
                        kohdentumattomat.append(ilmoitus.rawdata)
                session.commit()
        except Exception as e:
            logger.exception(e)
            raise

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat lopetusilmoitukset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_lopetusilmoitukset(
                os.path.dirname(ilmoitustiedosto), kohdentumattomat
            )

    def write_paatokset(
        self,
        paatos_list: List[Paatos],
        paatostiedosto: Path,
    ):
        kohdentumattomat = []
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Importoidaan päätökset")
                for paatos in paatos_list:
                    rakennus_id = find_single_building_id_by_prt(session, paatos.prt)
                    if rakennus_id:
                        akppoistosyy_id = (
                            get_code_id(
                                session, AKPPoistoSyy, paatos.akppoistosyy.value
                            ).id
                            if paatos.akppoistosyy is not None
                            else None
                        )
                        jatetyyppi_id = (
                            get_code_id(session, Jatetyyppi, paatos.jatetyyppi.value).id
                            if paatos.jatetyyppi is not None
                            else None
                        )
                        session.add(
                            Viranomaispaatokset(
                                paatosnumero=paatos.paatosnumero,
                                alkupvm=paatos.alkupvm,
                                loppupvm=paatos.loppupvm,
                                vastaanottaja=paatos.vastaanottaja,
                                tyhjennysvali=paatos.tyhjennysvali,
                                paatostulos_koodi=get_code_id(
                                    session, Paatostulos, paatos.paatostulos.value
                                ).koodi,
                                tapahtumalaji_koodi=get_code_id(
                                    session, Tapahtumalaji, paatos.tapahtumalaji.value
                                ).koodi,
                                akppoistosyy_id=akppoistosyy_id,
                                jatetyyppi_id=jatetyyppi_id,
                                rakennus_id=rakennus_id,
                            )
                        )
                    else:
                        kohdentumattomat.append(paatos.rawdata)
                session.commit()
        except Exception as e:
            logger.exception(e)
            raise

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat päätökset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_paatokset(
                os.path.dirname(paatostiedosto), kohdentumattomat
            )

    def write_kaivotiedot(
        self,
        kaivotiedot_list,
        tiedontuottaja_tunnus: str,
        kaivotiedosto_path: Path,
    ):
        """
        Tuo kaivotiedot (aloitus) JKR-järjestelmään.
        
        LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.
        
        Määrittelyn mukaan:
        - Kohdentaminen PRT:llä kohteelle
        - Jos kohteella on jo sama tieto, sitä ei viedä päälle ja se jää kohdentumatta
        - Vastausaika -> alkupvm
        - Yksi rivi voi sisältää useita kaivotietotyyppejä
        
        Args:
            kaivotiedot_list: Lista KaivotiedotRow-objekteista
            tiedontuottaja_tunnus: Tiedontuottajan tunnus
            kaivotiedosto_path: Polku alkuperäiseen tiedostoon (virheraporttia varten)
        """
        kohdentumattomat = []
        inserted_count = 0
        skipped_existing_count = 0
        skipped_no_kohde_count = 0
        
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print(f"Importoidaan kaivotiedot ({len(kaivotiedot_list)} riviä)")
                
                for row in kaivotiedot_list:
                    # Etsi kohde PRT:n perusteella
                    kohde = find_kohde_by_single_prt(session, row.prt)
                    
                    if not kohde:
                        logger.warning(f"Kohdetta ei löytynyt PRT:llä {row.prt}")
                        skipped_no_kohde_count += 1
                        if row.rawdata:
                            kohdentumattomat.append(row.rawdata)
                        continue
                    
                    # Käsittele jokainen kaivotietotyyppi erikseen
                    kaivotietotyypit = row.get_kaivotietotyypit()
                    
                    if not kaivotietotyypit:
                        logger.warning(f"Rivillä PRT {row.prt} ei ole yhtään kaivotietotyyppiä valittuna")
                        continue
                    
                    row_has_uninserted = False
                    
                    for tyyppi in kaivotietotyypit:
                        # Tarkista onko jo olemassa (millään alkupvm:llä)
                        tyyppi_id = get_kaivotietotyyppi_id(tyyppi)
                        if find_existing_kaivotieto_by_type(session, kohde.id, tyyppi_id):
                            logger.info(
                                f"Kaivotieto {tyyppi.value} on jo olemassa kohteella {kohde.id}, "
                                f"ohitetaan (ei viedä päälle)"
                            )
                            skipped_existing_count += 1
                            row_has_uninserted = True
                            continue
                        
                        # Lisää kaivotieto
                        success, msg = insert_kaivotieto(
                            session,
                            kohde.id,
                            tyyppi,
                            row.vastausaika,
                            row.tietolahde,
                            tiedontuottaja_tunnus
                        )
                        
                        if success:
                            inserted_count += 1
                            logger.info(msg)
                        else:
                            logger.warning(msg)
                            row_has_uninserted = True
                    
                    # Jos rivillä oli kaivotietoja joita ei voitu lisätä, 
                    # EI lisätä virheraporttiin (määrittelyn mukaan)
                    # Virheraporttiin vain ne joita ei voitu kohdentaa
                
                session.commit()
                
        except Exception as e:
            logger.exception(e)
            raise

        # Yhteenveto
        print("\nKaivotietojen tuonti valmis:")
        print(f"  - Lisätty: {inserted_count}")
        print(f"  - Ohitettu (jo olemassa): {skipped_existing_count}")
        print(f"  - Kohdentumatta (ei kohdetta): {skipped_no_kohde_count}")
        
        if kohdentumattomat:
            print(f"\nTallennetaan kohdentumattomat kaivotiedot ({len(kohdentumattomat)}) tiedostoon")
            export_kohdentumattomat_kaivotiedot(
                os.path.dirname(kaivotiedosto_path), kohdentumattomat
            )

    def write_kaivotiedon_lopetukset(
        self,
        lopetukset_list,
        tiedontuottaja_tunnus: str,
        lopetustiedosto_path: Path,
    ):
        """
        Tuo kaivotiedon lopetukset JKR-järjestelmään.
        
        LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.
        
        Määrittelyn mukaan:
        - Lopetus edellyttää että samalla kohteella on vastaava tieto alkanut
        - Tieto kohdennetaan PRT:llä kohteelle
        - Mikäli kohteella on useita samoja alkaneita kaivotietoja, 
          lopetuspäivämäärä lopettaa kaikki vastaavat samannimiset kaivotiedot
        
        Args:
            lopetukset_list: Lista KaivotiedonLopetusRow-objekteista
            tiedontuottaja_tunnus: Tiedontuottajan tunnus
            lopetustiedosto_path: Polku alkuperäiseen tiedostoon (virheraporttia varten)
        """
        kohdentumattomat = []
        updated_count = 0
        skipped_no_kohde_count = 0
        skipped_no_kaivotieto_count = 0
        
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print(f"Importoidaan kaivotiedon lopetukset ({len(lopetukset_list)} riviä)")
                
                for row in lopetukset_list:
                    # Etsi kohde PRT:n perusteella
                    kohde = find_kohde_by_single_prt(session, row.prt)
                    
                    if not kohde:
                        logger.warning(f"Kohdetta ei löytynyt PRT:llä {row.prt}")
                        skipped_no_kohde_count += 1
                        if row.rawdata:
                            kohdentumattomat.append(row.rawdata)
                        continue
                    
                    # Käsittele jokainen kaivotietotyyppi erikseen
                    kaivotietotyypit = row.get_kaivotietotyypit()
                    
                    if not kaivotietotyypit:
                        logger.warning(f"Rivillä PRT {row.prt} ei ole yhtään kaivotietotyyppiä valittuna")
                        continue
                    
                    for tyyppi in kaivotietotyypit:
                        # Päivitä loppupvm
                        kaivocount, msg = update_kaivotieto_loppupvm(
                            session,
                            kohde.id,
                            tyyppi,
                            row.vastausaika  # Vastausaika on loppupvm
                        )
                        
                        if kaivocount > 0:
                            updated_count += kaivocount
                            logger.info(msg)
                        else:
                            logger.warning(msg)
                            skipped_no_kaivotieto_count += 1
                            # Ei lisätä virheraporttiin - määrittelyn mukaan
                            # virheraportti vain kohdentumattomista
                
                session.commit()
                
        except Exception as e:
            logger.exception(e)
            raise

        # Yhteenveto
        print("\nKaivotiedon lopetusten tuonti valmis:")
        print(f"  - Päivitetty: {updated_count}")
        print(f"  - Kohdentumatta (ei kohdetta): {skipped_no_kohde_count}")
        print(f"  - Ohitettu (ei aktiivista kaivotietoa): {skipped_no_kaivotieto_count}")
        
        if kohdentumattomat:
            print(f"\nTallennetaan kohdentumattomat lopetukset ({len(kohdentumattomat)}) tiedostoon")
            export_kohdentumattomat_kaivotiedon_lopetukset(
                os.path.dirname(lopetustiedosto_path), kohdentumattomat
            )

    def write_viemariliitos(
        self,
        viemariliitos_list,
        viemaritiedosto_path: Path,
    ):
        """
        Tuo viemäritiedot JKR-järjestelmään.
        
        LAH-433: Viemäritiedot ja viemäriliitostiedon vienti kantaan.
        
        Määrittelyn mukaan:
        - Kohdentaminen PRT:llä kohteelle
        - Jos kohteella on jo sama tieto, sitä ei viedä päälle ja se jää kohdentumatta
        
        Args:
            viemäritiedot_list: Lista ViemäritiedotRow-objekteista
            viemäritiedosto_path: Polku alkuperäiseen tiedostoon (virheraporttia varten)
        """
        kohdentumattomat = []
        inserted_count = 0
        error_count = 0
        skipped_no_kohde_count = 0
        
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print(f"Importoidaan viemäriliitokset ({len(viemariliitos_list)} riviä)")
                
                for row in viemariliitos_list:
                    # Etsi kohde PRT:n perusteella
                    kohde = find_kohde_by_single_prt(session, row.prt)
                    
                    if not kohde:
                        logger.warning(f"Kohdetta ei löytynyt PRT:llä {row.prt}")
                        skipped_no_kohde_count += 1
                        if row.rawdata:
                            kohdentumattomat.append(row.rawdata)
                        continue
                

                    # Lisää viemäriliitos
                    success, msg = insert_viemariliitos(
                        session,
                        kohde.id,
                        row.viemariverkosto_alkupvm,
                        row.prt,
                    )
                    
                    if success:
                        inserted_count += 1
                        logger.info(msg)
                    else:
                        logger.warning(msg)
                        error_count += 1
                        kohdentumattomat.append(row.rawdata)
                
                
                session.commit()
                
        except Exception as e:
            logger.exception(e)
            raise

        # Yhteenveto
        print("\nViemäriliitosten tuonti valmis:")
        print(f"  - Lisätty: {inserted_count}")
        print(f"  - Kohdentumatta (muu virhe): {error_count}")
        print(f"  - Kohdentumatta (ei kohdetta): {skipped_no_kohde_count}")
        
        if kohdentumattomat:
            print(f"\nTallennetaan kohdentumattomat viemäriliitokset ({len(kohdentumattomat)}) tiedostoon")
            export_kohdentumattomat_viemariilmoitukset(
                os.path.dirname(viemaritiedosto_path), kohdentumattomat, viemaritiedosto_path
            )


    def write_viermariliitosten_lopetukset(
        self,
        lopetukset_list,
        lopetustiedosto_path: Path,
    ):
        """
        Tuo viemäritiedon lopetukset JKR-järjestelmään.
        
        LAH-433: Viemäriliitosten lopetus tietojen vienti kantaan.
        
        Määrittelyn mukaan:
        - Lopetus edellyttää että samalla kohteella on vastaava tieto alkanut
        - Tieto kohdennetaan PRT:llä kohteelle
        - Lopetuspäivämäärä lopettaa kaikki samalle kohteelle kuuluvat viemäriliitokset
        
        Args:
            lopetukset_list: Lista ViemäriLopetusRow-objekteista
            lopetustiedosto_path: Polku alkuperäiseen tiedostoon (virheraporttia varten)
        """
        kohdentumattomat = []
        updated_count = 0
        skipped_no_kohde_count = 0
        skipped_no_viemari_count = 0
        
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print(f"Importoidaan viemariliitosten lopetukset ({len(lopetukset_list)} riviä)")
                
                for row in lopetukset_list:
                    # Etsi kohde PRT:n perusteella
                    kohde = find_kohde_by_single_prt(session, row.prt)
                    
                    if not kohde:
                        logger.warning(f"Kohdetta ei löytynyt PRT:llä {row.prt}")
                        skipped_no_kohde_count += 1
                        if row.rawdata:
                            kohdentumattomat.append(row.rawdata)
                        continue
                    
                    # Päivitä loppupvm
                    viemaricount, msg = update_viemariliitos_loppupvm(
                        session,
                        kohde.id,
                        row.viemariverkosto_loppupvm,
                    )
                    
                    if viemaricount > 0:
                        updated_count += viemaricount
                        logger.info(msg)
                    else:
                        logger.warning(msg)
                        skipped_no_viemari_count += 1
                        kohdentumattomat.append(row.rawdata)
                
                session.commit()
                
        except Exception as e:
            logger.exception(e)
            raise

        # Yhteenveto
        print("\nViemäriliitoksen lopetusten tuonti valmis:")
        print(f"  - Päivitetty: {updated_count}")
        print(f"  - Kohdentumatta (ei kohdetta): {skipped_no_kohde_count}")
        print(f"  - Ohitettu (ei aktiivista viemäritietoa): {skipped_no_viemari_count}")
        
        if kohdentumattomat:
            print(f"\nTallennetaan kohdentumattomat lopetukset ({len(kohdentumattomat)}) tiedostoon")
            export_kohdentumattomat_viemarilopetusilmoitukset(
                os.path.dirname(lopetustiedosto_path), kohdentumattomat
            )