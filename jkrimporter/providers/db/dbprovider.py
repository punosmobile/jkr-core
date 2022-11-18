import datetime
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from jkrimporter.model import Asiakas, JkrData
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import init_code_objects
from .database import engine
from .models import Kohde, Kuljetus, Tiedontuottaja
from .services.buildings import counts as building_counts
from .services.buildings import find_buildings_for_kohde
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_multiple_and_uninhabited_kohteet,
    create_new_kohde,
    create_paritalo_kohteet,
    create_perusmaksurekisteri_kohteet,
    create_single_asunto_kohteet,
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
    urakoitsija: Tiedontuottaja,
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
                tiedontuottaja=urakoitsija,
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
    urakoitsija: Tiedontuottaja,
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


def import_dvv_kohteet(session: Session, perusmaksutiedosto: Optional[Path]):
    # 1) Yhden asunnon talot (asutut): DVV:n tiedoissa kiinteistöllä yksi rakennus ja
    # asukas.
    # 2) Yhden asunnon talot (tyhjillään tai asuttu): DVV:n tiedoissa kiinteistön
    # rakennuksilla sama omistaja. Voi olla yksi tai monta rakennusta.Yhdessä
    # rakennuksessa voi olla asukkaita.
    # - Asiakas on vanhin asukas.
    # - Kiinteistön muut rakennukset asumattomia (esim. lomarakennukset, saunat),
    #  joten ne liitetään, jos sama omistaja ja osoite.
    # - Kiinteistön asumattomista muun omistajan tai osoitteen rakennuksista
    # tehdään erilliset kohteet omistajan ja osoitteen mukaan.
    # - Kohdetta ei tuoda, jos samalla kiinteistöllä muita asuttuja rakennuksia.
    single_asunto_kohteet = create_single_asunto_kohteet(session)
    session.commit()
    print(f"Imported {len(single_asunto_kohteet)} single kohteet")

    # Perusmaksurekisteri may combine buildings and kiinteistöt to a single kohde.
    # 3) Kerros ja rivitalot: Perusmaksurekisterin aineistosta asiakasnumero. Voi olla
    # yksi tai monta rakennusta.
    # 7) Vapaa-ajanasunnot: kaikki samat omistajat. Perusmaksurekisterin aineistosta
    # asiakasnumero. Voi olla yksi tai monta rakennusta.
    # - Kohteeseen yhdistetään rakennukset kiinteistöistä riippumatta.
    # - Asiakkaiksi tallennetaan kaikki kohteen rakennusten omistajat.
    # - Saunat ja talousrakennukset liitetään, jos sama kiinteistö, omistaja ja osoite
    # kuin jollakin rakennuksista.
    # - Kiinteistö(je)n muita rakennuksia ei liitetä, sillä niissä voi olla asukkaita,
    # joilla erilliset sopimukset.
    if perusmaksutiedosto:
        perusmaksukohteet = create_perusmaksurekisteri_kohteet(
            session, perusmaksutiedosto
        )
    session.commit()
    print(f"Imported {len(perusmaksukohteet)} kohteet with perusmaksu data")

    # 4) Paritalot: molemmille huoneistoille omat kohteet
    # Does it matter this is imported after 7? -No, because paritalot will not
    # interact with 7.
    # - Asiakas on kumpikin vanhin asukas erikseen.
    # - Kiinteistöllä kaksi kohdetta joilla sama rakennus, muita rakennuksia ei liitetä.
    # TODO: add all buildings on kiinteistö?
    paritalo_kohteet = create_paritalo_kohteet(session)
    session.commit()
    print(f"Imported {len(paritalo_kohteet)} paritalokohteet")

    # Remaining buildings will be combined by owner and kiinteistö.
    # TODO: limit imported types

    # 5) Muut rakennukset, joissa huoneistotieto eli asukas: DVV:n tiedoissa
    # kiinteistöllä yksi rakennus ja asukas. Voi olla 1 rakennus.
    # TODO: näihin vielä asukas omistajan sijaan asiakkaaksi. TODO: makes no sense.
    # Siinä tapauksessa vahtimestari saa koko koulun jätehuollon laskut, ja koulua
    # ei tuodakaan omistajan nimellä.

    # Does it matter this is imported after 7? - Ei. Näitä on *yksi* vapaa-ajanasuntojen
    # kanssa samalla kiinteistöllä *koko alueella*, siinäkin useampi asukas.
    # Tällä kiinteistöllä on yhden asunnon talo,
    # muu pientalo, vapaa-ajanasunto ja autotalli. Autotalli eri osoitteessa, joten siitä
    # joka tapauksessa oma kohde. Kaikilla samat omistajat. Vapaa-ajanasunto tuotu ensin.
    # Yhden asunnon talo ja muu pientalo tuodaan lopuksi, koska kummassakin asukkaita.

    # 6) Muut asumisen rakennukset (asuntola, palvelutalo): käyttötarkoitus + omistaja
    # + kiinteistö
    # Does it matter this is imported after 7? - Ei, koska käyttötarkoituksen mukaan
    # rajataan kuitenkin erilliset kohteet.

    # 8) Koulut: käyttötarkoitus + omistaja + sijaintikiinteistö
    # 9) Muut rakennukset, joissa huoneisto: sama kiinteistö, sama omistaja.
    # TODO: näihin omistaja asiakkaaksi. Voiko tehdä yhdessä 5:n kanssa?
    # Does it matter if this is imported at the same time as 6 & 8? Voi tehdä, jos
    # halutaan alkuperäinen järjestys, eli kouluille asiakkaaksi ainoa asukas eikä omistaja.
    # Useamman asukkaan kohteille asiakkaaksi omistaja.

    # - Asiakas on suurin omistaja.
    # - Kiinteistön rakennukset yhdistetään omistajan ja osoitteen mukaan.
    # TODO: limit added buildings on kiinteistö?
    # - Kiinteistön asumattomista muun omistajan tai osoitteen rakennuksista
    # tehdään erilliset kohteet omistajan ja osoitteen mukaan.
    multiple_and_uninhabited_kohteet = create_multiple_and_uninhabited_kohteet(session)
    session.commit()
    print(f"Imported {len(multiple_and_uninhabited_kohteet)} remaining kohteet")


class DbProvider:
    def write(self, jkr_data: JkrData, tiedontuottaja_lyhenne: str):
        try:
            progress = Progress(len(jkr_data.asiakkaat))

            prt_counts, kitu_counts, address_counts = count(jkr_data)
            with Session(engine) as session:
                init_code_objects(session)

                urakoitsija = session.get(
                    Tiedontuottaja, tiedontuottaja_lyhenne
                )

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

    def write_dvv_kohteet(self, perusmaksutiedosto: Optional[Path]):
        """
        This method creates kohteet from dvv data existing in the database.

        Optionally, a perusmaksurekisteri xlsx file may be provided to
        combine dvv buildings with the same customer id.
        """
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Luodaan kohteet")
                import_dvv_kohteet(session, perusmaksutiedosto)

        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(building_counts)
