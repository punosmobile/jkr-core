from datetime import datetime, timedelta
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import csv

from sqlalchemy import text
from sqlalchemy.orm import Session

from jkrimporter.model import Asiakas, JkrData
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.intervals import IntervalCounter
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import init_code_objects
from .database import engine
from .models import Kohde, Kuljetus, Tiedontuottaja
from .services.buildings import counts as building_counts
from .services.buildings import (
    find_building_candidates_for_kohde,
    find_buildings_for_kohde,
)
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_new_kohde,
    create_perusmaksurekisteri_kohteet,
    find_kohde_by_address,
    find_kohde_by_kiinteisto,
    find_kohde_by_prt,
    get_or_create_multiple_and_uninhabited_kohteet,
    get_or_create_paritalo_kohteet,
    get_or_create_single_asunto_kohteet,
    get_ulkoinen_asiakastieto,
    update_kohde,
    update_ulkoinen_asiakastieto,
)
from .services.osapuoli import create_or_update_haltija_osapuoli
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
                massa=tyhjennys.massa,
                tilavuus=tyhjennys.tilavuus,
                tiedontuottaja=urakoitsija,
            )
            session.add(db_kuljetus)


def find_and_update_kohde(
    session: "Session",
    asiakas: "Asiakas",
    do_create: bool,
    do_update: bool,
    prt_counts: Dict[str, int],
    kitu_counts: Dict[str, int],
    address_counts: Dict[str, int],
) -> Union[Kohde, None]:

    kohde = None
    ulkoinen_asiakastieto = get_ulkoinen_asiakastieto(session, asiakas.asiakasnumero)
    if ulkoinen_asiakastieto:
        print("Kohde found by customer id.")
        update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas)

        kohde = ulkoinen_asiakastieto.kohde
        if do_update:
            update_kohde(kohde, asiakas)
    else:
        print("Customer id not found. Searching for kohde by customer data...")
        if asiakas.rakennukset:
            kohde = find_kohde_by_prt(session, asiakas)
        if not kohde and asiakas.kiinteistot:
            kohde = find_kohde_by_kiinteisto(session, asiakas)
        if (
            not kohde
            and asiakas.haltija.osoite.postinumero
            and asiakas.haltija.osoite.katunimi
        ):
            kohde = find_kohde_by_address(session, asiakas)
        if kohde and do_update:
            update_kohde(kohde, asiakas)
        elif do_create:
            # this creates kohde without buildings
            print("Kohde not found, creating new one...")
            kohde = create_new_kohde(session, asiakas)
        if kohde:
            add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)
        else:
            print("Could not find kohde.")

    if do_create and not kohde.rakennus_collection:
        print("New kohde created. Looking for buildings...")
        buildings = find_buildings_for_kohde(
            session, asiakas, prt_counts, kitu_counts, address_counts
        )
        if buildings:
            kohde.rakennus_collection = buildings

        elif not kohde.ehdokasrakennus_collection:
            building_candidates = find_building_candidates_for_kohde(session, asiakas)
            if building_candidates:
                kohde.ehdokasrakennus_collection = building_candidates

    return kohde


def set_end_dates_to_kohteet(
    session: Session,
    poimintapvm: datetime.date,
):
    previous_pvm = poimintapvm - timedelta(days=1)
    add_date_query = \
        text("UPDATE jkr.kohde SET loppupvm = :loppu_pvm WHERE loppupvm IS NULL")
    session.execute(add_date_query, {"loppu_pvm": previous_pvm.strftime("%Y-%m-%d")})
    session.commit()


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
        session, asiakas, do_create, do_update_kohde, prt_counts, kitu_counts, address_counts
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
):
    # Set end date for each kohde without end date. This will remain as an end
    # date for non-active kohteet. The active kohteet will be updated below and
    # the end date is cleared.
    if poimintapvm is not None:
        set_end_dates_to_kohteet(session, poimintapvm)

    # 1) Yhden asunnon kohteet
    single_asunto_kohteet = get_or_create_single_asunto_kohteet(
        session, poimintapvm, loppupvm
    )
    session.commit()
    print(f"Imported {len(single_asunto_kohteet)} single kohteet")

    # 2) Perusmaksurekisterin kohteet
    if perusmaksutiedosto:
        perusmaksukohteet = create_perusmaksurekisteri_kohteet(
            session, perusmaksutiedosto, poimintapvm, loppupvm
        )
        session.commit()
        print(f"Imported {len(perusmaksukohteet)} kohteet with perusmaksu data")
    else:
        print("No perusmaksu data")

    # 3) Paritalokohteet
    paritalo_kohteet = get_or_create_paritalo_kohteet(session, poimintapvm, loppupvm)
    session.commit()
    print(f"Imported {len(paritalo_kohteet)} paritalokohteet")

    # 4) Muut kohteet
    multiple_and_uninhabited_kohteet = get_or_create_multiple_and_uninhabited_kohteet(
        session, poimintapvm, loppupvm
    )
    session.commit()
    print(f"Imported {len(multiple_and_uninhabited_kohteet)} remaining kohteet")


class DbProvider:
    def write(
        self,
        jkr_data: JkrData,
        tiedontuottaja_lyhenne: str,
        ala_luo: bool,
        ala_paivita_yhteystietoja: bool,
        ala_paivita_kohdetta: bool,
        siirtotiedosto: Path
    ):
        try:
            expected_headers = [
                            'UrakoitsijaId', 'UrakoitsijankohdeId', 'Kiinteistotunnus',
                            'Kiinteistonkatuosoite', 'Kiinteistonposti', 'Haltijannimi',
                            'Haltijanyhteyshlo', 'Haltijankatuosoite', 'Haltijanposti',
                            'Haltijanmaakoodi', 'Haltijanulkomaanpaikkakunta', 'Pvmalk',
                            'Pvmasti', 'tyyppiIdEWC', 'COUNT(kaynnit)',
                            'SUM(astiamaara)', 'koko', 'SUM(paino)', 'tyhjennysvali',
                            'tyhjennysvali2', 'kertaaviikossa', 'kertaaviikossa2',
                            'Voimassaoloviikotalkaen', 'Voimassaoloviikotasti',
                            'palveluKimppakohdeId', 'Kimpanyhteyshlo', 'KimpanNimi',
                            'Kimpankatuosoite', 'Kimpanposti', 'Kuntatun',
                            'Keskeytysalkaen', 'Keskeytysasti'
                        ]
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
                        # Rebuild row to insert into the error .csv
                        row_data = {
                            'UrakoitsijaId': kohdentumaton['ulkoinen_asiakastieto'].UrakoitsijaId,
                            'UrakoitsijankohdeId': kohdentumaton['ulkoinen_asiakastieto'].UrakoitsijankohdeId,
                            'Kiinteistotunnus': kohdentumaton['ulkoinen_asiakastieto'].Kiinteistotunnus,
                            'Kiinteistonkatuosoite': kohdentumaton['ulkoinen_asiakastieto'].Kiinteistonkatuosoite,
                            'Kiinteistonposti': kohdentumaton['ulkoinen_asiakastieto'].Kiinteistonposti,
                            'Haltijannimi': kohdentumaton['ulkoinen_asiakastieto'].Haltijannimi,
                            'Haltijanyhteyshlo': kohdentumaton['ulkoinen_asiakastieto'].Haltijanyhteyshlo,
                            'Haltijankatuosoite': kohdentumaton['ulkoinen_asiakastieto'].Haltijankatuosoite,
                            'Haltijanposti': kohdentumaton['ulkoinen_asiakastieto'].Haltijanposti,
                            'Haltijanmaakoodi': kohdentumaton['ulkoinen_asiakastieto'].Haltijanmaakoodi,
                            'Pvmalk': kohdentumaton['ulkoinen_asiakastieto'].Pvmalk,
                            'Pvmasti': kohdentumaton['ulkoinen_asiakastieto'].Pvmasti,
                            'tyyppiIdEWC': kohdentumaton['ulkoinen_asiakastieto'].tyyppiIdEWC,
                            'COUNT(kaynnit)': kohdentumaton['ulkoinen_asiakastieto'].kaynnit,
                            'SUM(astiamaara)': kohdentumaton['ulkoinen_asiakastieto'].astiamaara,
                            'koko': kohdentumaton['ulkoinen_asiakastieto'].koko,
                            'SUM(paino)': kohdentumaton['ulkoinen_asiakastieto'].paino,
                            'tyhjennysvali': kohdentumaton['ulkoinen_asiakastieto'].tyhjennysvali,
                            'tyhjennysvali2': kohdentumaton['ulkoinen_asiakastieto'].tyhjennysvali2,
                            'kertaaviikossa': kohdentumaton['ulkoinen_asiakastieto'].kertaaviikossa,
                            'kertaaviikossa2': kohdentumaton['ulkoinen_asiakastieto'].kertaaviikossa2,
                            'Voimassaoloviikotalkaen': kohdentumaton['voimassa'].Voimassaoloviikotalkaen,
                            'Voimassaoloviikotasti': kohdentumaton['voimassa'].Voimassaoloviikotasti,
                            'palveluKimppakohdeId': kohdentumaton['ulkoinen_asiakastieto'].palveluKimppakohdeId,
                            'Kimpanyhteyshlo': kohdentumaton['ulkoinen_asiakastieto'].Kimpanyhteyshlo,
                            'KimpanNimi': kohdentumaton['ulkoinen_asiakastieto'].kimpanNimi,
                            'Kimpankatuosoite': kohdentumaton['ulkoinen_asiakastieto'].Kimpankatuosoite,
                            'Kimpanposti': kohdentumaton['ulkoinen_asiakastieto'].Kimpanposti,
                            'Kuntatun': kohdentumaton['ulkoinen_asiakastieto'].Kuntatun,
                            'Keskeytysalkaen': kohdentumaton['ulkoinen_asiakastieto'].Keskeytysalkaen,
                            'Keskeytysasti': kohdentumaton['ulkoinen_asiakastieto'].Keskeytysasti,
                                                    }

                        csv_path = siirtotiedosto / "kohdentumattomat.csv"
                        with open(csv_path, mode="a", encoding="cp1252", newline="") as csv_file:
                            fieldnames = expected_headers
                            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=";", quotechar='"')
                            csv_writer.writerow(row_data)

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
