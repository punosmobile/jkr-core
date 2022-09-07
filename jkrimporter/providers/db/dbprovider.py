import datetime
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from jkrimporter.model import Asiakas, JkrData
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import OsapuolenlajiTyyppi, init_code_objects
from .database import engine
from .models import Kohde, Kuljetus, Osapuoli
from .services.buildings import counts as building_counts
from .services.buildings import find_buildings_for_kohde
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_new_kohde,
    find_kohde_by_asiakastiedot,
    get_kohde_by_asiakasnumero,
    get_ulkoinen_asiakastieto,
    update_kohde,
    update_ulkoinen_asiakastieto,
)
from .services.osapuoli import (
    create_or_update_haltija_osapuoli,
    create_or_update_yhteystieto_osapuoli,
)
from .services.sopimus import update_sopimukset_for_kohde

logger = logging.getLogger(__name__)


def get_or_create_urakoitsija(session: "Session"):
    statement = select(Osapuoli).where(Osapuoli.nimi == "Pirkanmaan Jätehuolto Oy")
    osapuoli = session.execute(statement).scalar_one()

    if not osapuoli:
        osapuolilaji = codes.osapuolenlajit[OsapuolenlajiTyyppi.JULKINEN]

        osapuoli = Osapuoli(
            ytunnus="0968008-1", nimi="Pirkanmaan Jätehuolto Oy", rooli=osapuolilaji
        )

    return osapuoli


def count(jkr_data: JkrData) -> Tuple[Dict[str, int], Dict[str, int]]:
    prt_counts: Dict[str, int] = defaultdict(int)
    kitu_counts: Dict[str, int] = defaultdict(int)
    address_counts: Dict[str, int] = defaultdict(int)

    for asiakas in jkr_data.asiakkaat.values():
        for prt in asiakas.rakennukset:
            prt_counts[prt] += 1
        for kitu in asiakas.kiinteistot:
            kitu_counts[kitu] += 1
        addr = asiakas.haltija.osoite.osoite_rakennus()
        if addr:
            address_counts[addr] += 1

    return prt_counts, kitu_counts, address_counts


def insert_kuljetukset(
    session,
    kohde,
    tyhjennystapahtumat: List[JkrTyhjennystapahtuma],
    raportointi_alkupvm,
    raportointi_loppupvm,
    urakoitsija,
):
    for tyhjennys in tyhjennystapahtumat:
        alkupvm = tyhjennys.pvm or raportointi_alkupvm
        loppupvm = tyhjennys.pvm or raportointi_loppupvm

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
                osapuoli=urakoitsija,
            )
            session.add(db_kuljetus)


def find_and_update_kohde(session: "Session", asiakas: "Asiakas") -> Kohde:
    ulkoinen_asiakastieto = get_ulkoinen_asiakastieto(session, asiakas.asiakasnumero)
    if ulkoinen_asiakastieto:
        update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas)

        kohde = ulkoinen_asiakastieto.kohde
        update_kohde(kohde, asiakas)
    else:
        kohde = find_kohde_by_asiakastiedot(session, asiakas)
        if kohde:
            update_kohde(kohde, asiakas)
        else:
            kohde = create_new_kohde(session, asiakas)

        add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)

    return kohde


def import_asiakastiedot(
    session: Session,
    asiakas: Asiakas,
    alkupvm: datetime.date,
    loppupvm: datetime.date,
    urakoitsija: Osapuoli,
    prt_counts: Dict[str, int],
    kitu_counts: Dict[str, int],
    address_counts: Dict[str, int],
):

    kohde = find_and_update_kohde(session, asiakas)

    create_or_update_haltija_osapuoli(session, kohde, asiakas)
    create_or_update_yhteystieto_osapuoli(session, kohde, asiakas)
    insert_kuljetukset(
        session,
        kohde,
        asiakas.tyhjennystapahtumat,
        alkupvm,
        loppupvm,
        urakoitsija,
    )

    if not kohde.rakennus_collection:
        buildings = find_buildings_for_kohde(
            session, asiakas, prt_counts, kitu_counts, address_counts
        )
        if buildings:
            kohde.rakennus_collection = buildings

    session.commit()


class DbProvider:
    def write(self, jkr_data: JkrData, tiedontuottaja_lyhenne: str):
        try:
            progress = Progress(len(jkr_data.asiakkaat))

            prt_counts, kitu_counts, address_counts = count(jkr_data)
            with Session(engine) as session:
                init_code_objects(session)

                urakoitsija = get_or_create_urakoitsija(session)

                print("Importoidaan asiakastiedot")
                for asiakas in jkr_data.asiakkaat.values():
                    progress.tick()

                    import_asiakastiedot(
                        session,
                        asiakas,
                        jkr_data.alkupvm,
                        jkr_data.loppupvm,
                        urakoitsija,
                        prt_counts,
                        kitu_counts,
                        address_counts,
                    )

                progress.complete()

                print("Importoidaan sopimukset")
                progress.reset()
                for asiakas in jkr_data.asiakkaat.values():
                    progress.tick()

                    kohde = get_kohde_by_asiakasnumero(session, asiakas.asiakasnumero)
                    update_sopimukset_for_kohde(
                        session,
                        asiakas,
                        kohde,
                        asiakas.sopimukset,
                        urakoitsija,
                        jkr_data.loppupvm,
                    )
                    session.commit()

                progress.complete()

        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(building_counts)
