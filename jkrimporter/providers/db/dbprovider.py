import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from sqlalchemy import text
from sqlalchemy.orm import Session

from jkrimporter.conf import get_kohdentumattomat_siirtotiedosto_filename
from jkrimporter.datasheets import get_siirtotiedosto_headers
from jkrimporter.model import (
    Asiakas,
    JkrData,
    JkrIlmoitukset,
    Paatos,
    LopetusIlmoitus
)
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.ilmoitus import (
    export_kohdentumattomat_ilmoitukset,
    export_kohdentumattomat_lopetusilmoitukset
)
from jkrimporter.utils.intervals import IntervalCounter
from jkrimporter.utils.paatos import export_kohdentumattomat_paatokset
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import get_code_id, init_code_objects
from .database import engine
from .models import (
    AKPPoistoSyy,
    Jatetyyppi,
    Kohde,
    Kompostori,
    KompostorinKohteet,
    Kuljetus,
    Paatostulos,
    Tapahtumalaji,
    Tiedontuottaja,
    Viranomaispaatokset,
)
from .services.buildings import counts as building_counts
from .services.buildings import (
    find_building_candidates_for_kohde,
    find_buildings_for_kohde,
    find_osoite_by_prt,
    find_single_building_id_by_prt,
)
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_new_kohde,
    create_perusmaksurekisteri_kohteet,
    find_kohde_by_address,
    find_kohde_by_prt,
    find_kohteet_by_prt,
    get_or_create_multiple_and_uninhabited_kohteet,
    check_and_update_old_other_building_kohde_kohdetyyppi,
    get_or_create_single_asunto_kohteet,
    get_ulkoinen_asiakastieto,
    update_kohde,
    update_ulkoinen_asiakastieto,
)
from .services.osapuoli import (
    create_or_update_haltija_osapuoli,
    create_or_update_komposti_yhteyshenkilo,
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
    raportointi_alkupvm: Optional[datetime.date],
    raportointi_loppupvm: Optional[datetime.date],
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
            )
            session.add(db_kuljetus)


def find_and_update_kohde(session, asiakas, do_create, do_update_kohde, prt_counts, kitu_counts, address_counts):
    """
    Etsii olemassa olevan kohteen asiakkaalle tai luo uuden.
    """
    kohde = None
    ulkoinen_asiakastieto = get_ulkoinen_asiakastieto(session, asiakas.asiakasnumero)
    
    # 1. Etsi kohde asiakasnumeron perusteella
    if ulkoinen_asiakastieto:
        print("Kohde found by customer id.")
        update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas)

        kohde = ulkoinen_asiakastieto.kohde
        if do_update_kohde:
            update_kohde(kohde, asiakas)
    else:
        # 2. Etsi kohde rakennustietojen perusteella
        print("Customer id not found. Searching for kohde by customer data...")
        if asiakas.rakennukset:
            kohde = find_kohde_by_prt(session, asiakas)
            
        # 3. Etsi kohde osoitteen perusteella
        if (
            not kohde
            and asiakas.haltija.osoite.postinumero
            and asiakas.haltija.osoite.katunimi
        ):
            kohde = find_kohde_by_address(session, asiakas)
            
        if kohde and do_update_kohde:
            update_kohde(kohde, asiakas)
        elif do_create:
            print("Kohde not found, creating new one...")
            kohde = create_new_kohde(session, asiakas)
            
        if kohde:
            add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)
        else:
            print("Could not find kohde.")

    # 4. Jos kohde luotu ilman rakennuksia, etsi sopivat rakennukset
    if do_create and kohde and not kohde.rakennus_collection:
        print("New kohde created. Looking for buildings...")
        buildings = find_buildings_for_kohde(
            session, asiakas, prt_counts, kitu_counts, address_counts
        )
        if buildings:
            kohde.rakennus_collection = buildings

    return kohde


def import_asiakastiedot(
    session: Session,
    asiakas: Asiakas,
    alkupvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date],
    urakoitsija: Tiedontuottaja,
    do_create: bool,
    do_update_contact: bool,
    do_update_kohde: bool,
    prt_counts: Dict[str, IntervalCounter],
    kitu_counts: Dict[str, IntervalCounter],
    address_counts: Dict[str, IntervalCounter],
):

    kohde = find_and_update_kohde(
        session,
        asiakas,
        do_create,
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
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date] = None,
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

    # 2. Yhden asunnon kohteet (omakotitalot ja paritalot)
    logger.info("\nLuodaan yhden asunnon kohteet...")
    print("\nLuodaan yhden asunnon kohteet...")

    single_asunto_kohteet = get_or_create_single_asunto_kohteet(
        session, poimintapvm, loppupvm
    )
    session.commit()
    logger.info(f"Luotu {len(single_asunto_kohteet)} yhden asunnon kohdetta")
    print(f"Luotu {len(single_asunto_kohteet)} yhden asunnon kohdetta")

    # 3. Muut kohteet (kaikki loput rakennukset)
    logger.info("\nLuodaan loput kohteet...")
    print("\nLuodaan loput kohteet...")
    multiple_and_uninhabited_kohteet = get_or_create_multiple_and_uninhabited_kohteet(
        session, poimintapvm, loppupvm
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
    print(f"\nDVV-kohteiden luonti valmis. Luotu yhteensä {total_kohteet} kohdetta ja päivitetty {len(paivitetut_rakennus_kohteet)} vanhaa kohdetta")
    logger.info(f"\nDVV-kohteiden luonti valmis. Luotu yhteensä {total_kohteet} kohdetta.")


class DbProvider:
    def write(
        self,
        jkr_data: JkrData,
        tiedontuottaja_lyhenne: str,
        ala_luo: bool,
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
                        not ala_luo,
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
                    for kohdentumaton in kohdentumattomat:

                        # Rebuild rows to insert into the error .csv
                        rows = []
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
                                csv_writer.writerow(rd)

                    print(f"Kohdentumattomat tiedot lisätty CSV-tiedostoon: {csv_path}")
                else:
                    print("Ei kohdentumattomia tietoja.")

        except Exception as e:
            logger.exception(e)
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
                    kompostorin_kohde = find_kohde_by_prt(session, ilmoitus)
                    if kompostorin_kohde:
                        print(f"Kompostorin kohde: {kompostorin_kohde.id} prt: {ilmoitus.sijainti_prt}")
                        osapuoli = create_or_update_komposti_yhteyshenkilo(
                            session, kompostorin_kohde, ilmoitus
                        )
                        osoite_id = find_osoite_by_prt(session, ilmoitus)
                        if not osoite_id:
                            print(
                                "Ei löytynyt osoite_id:tä rakennus: "
                                + f"{ilmoitus.sijainti_prt}"
                            )
                            kohdentumattomat.append(ilmoitus.rawdata)
                            continue
                        # There should never be identical Kompostori
                        existing_kompostori = session.query(Kompostori).filter(
                            Kompostori.alkupvm == ilmoitus.alkupvm,
                            Kompostori.loppupvm == ilmoitus.loppupvm,
                            Kompostori.osoite_id == osoite_id,
                            Kompostori.onko_kimppa == ilmoitus.onko_kimppa,
                            Kompostori.osapuoli_id == osapuoli.id
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
                        if kohteet:
                            for kohde in kohteet:
                                existing_kohde = session.query(
                                    KompostorinKohteet).filter(
                                        KompostorinKohteet.kompostori_id == komposti.id,
                                        KompostorinKohteet.kohde_id == kohde.id
                                ).first()
                                if existing_kohde:
                                    print("Kohde on jo kompostorin kohteissa...")
                                else:
                                    print("Lisätään kohde kompostorin kohteisiin...")
                                    session.add(
                                        KompostorinKohteet(
                                            kompostori=komposti,
                                            kohde=kohde
                                        ),
                                    )
                        if kohdentumattomat_prt:
                            # Append rawdata dicts for each kohdentumaton kompostoija.
                            for prt in kohdentumattomat_prt:
                                for rawdata in ilmoitus.rawdata:
                                    if rawdata.get(
                                        "Rakennuksen tiedot, jossa kompostori sijaitsee:Käsittelijän lisäämä tunniste"
                                    ) == prt:
                                        kohdentumattomat.append(rawdata)
                    else:
                        # Append each rawdata dict.
                        for rawdata in ilmoitus.rawdata:
                            kohdentumattomat.append(rawdata)
                session.commit()
        except Exception as e:
            logger.exception(e)

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat ilmoitukset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_ilmoitukset(
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

        if kohdentumattomat:
            print(
                f"Tallennetaan kohdentumattomat päätökset ({len(kohdentumattomat)}) tiedostoon"
            )
            export_kohdentumattomat_paatokset(
                os.path.dirname(paatostiedosto), kohdentumattomat
            )
