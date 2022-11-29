import datetime
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from jkrimporter.model import Asiakas, JkrData
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.intervals import IntervalCounter
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import init_code_objects
from .database import engine
from .models import Kohde, KohteenRakennukset, Kuljetus, Tiedontuottaja
from .services.buildings import counts as building_counts
from .services.buildings import (
    find_building_candidates_for_kohde,
    find_buildings_for_kohde,
)
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
    match_asukas,
    update_kohde,
    update_ulkoinen_asiakastieto,
)
from .services.osapuoli import (
    create_or_update_haltija_osapuoli,
    create_or_update_yhteystieto_osapuoli,
)
from .services.sopimus import update_sopimukset_for_kohde

logger = logging.getLogger(__name__)


def count(jkr_data: JkrData):
    prt_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)
    kitu_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)
    address_counts: Dict[str, IntervalCounter] = defaultdict(IntervalCounter)

    # TODO: So we have duplicate asiakkaat in the same address for the same interval.
    # So what? Jukka will have biojäte, sekajäte, energia. So will Aija.
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
) -> Kohde:
    ulkoinen_asiakastieto = get_ulkoinen_asiakastieto(session, asiakas.asiakasnumero)
    if ulkoinen_asiakastieto:
        update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas)

        kohde = ulkoinen_asiakastieto.kohde
        if do_update:
            update_kohde(kohde, asiakas)
    else:
        kohde = find_kohde_by_asiakastiedot(session, asiakas)
        if kohde:
            if do_update:
                update_kohde(kohde, asiakas)
        elif do_create:
            kohde = create_new_kohde(session, asiakas)

    if not kohde or not kohde.rakennus_collection:
        print("No kohde found. Looking for buildings...")
        buildings = find_buildings_for_kohde(
            session, asiakas, prt_counts, kitu_counts, address_counts
        )
        if kohde:
            if buildings:
                kohde.rakennus_collection = buildings

            elif not kohde.ehdokasrakennus_collection:
                building_candidates = find_building_candidates_for_kohde(
                    session, asiakas
                )
                if building_candidates:
                    kohde.ehdokasrakennus_collection = building_candidates
        else:
            print("got buildings")
            print(buildings)
            kohde_ids = session.execute(
                select(KohteenRakennukset.kohde_id).where(
                    KohteenRakennukset.rakennus_id.in_(
                        [building.id for building in buildings]
                    )
                )
            ).all()
            print("got kohde ids")
            print(kohde_ids)
            # There may be several. Paritalot must be selected by customer
            # name, we might not know if they inhabit A or B. Pick the last
            # one if no name matches.
            for kohde_id in kohde_ids:
                kohde = session.get(Kohde, kohde_id)
                print("we have kohde")
                print(kohde)
                # if match_asukas(kohde, asiakas.haltija):
                #     break

        if kohde:
            add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)

    return kohde


def import_asiakastiedot(
    session: Session,
    asiakas: Asiakas,
    alkupvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date],
    urakoitsija: Tiedontuottaja,
    do_create: bool,
    do_update: bool,
    prt_counts: Dict[str, IntervalCounter],
    kitu_counts: Dict[str, IntervalCounter],
    address_counts: Dict[str, IntervalCounter],
):

    kohde = find_and_update_kohde(
        session, asiakas, do_create, do_update, prt_counts, kitu_counts, address_counts
    )
    if not kohde:
        print(f"Could not find kohde for asiakas {asiakas}, skipping...")
        return

    # Update osapuolet from the same tiedontuottaja. These functions will not
    # touch data from other tiedontuottajat.
    create_or_update_haltija_osapuoli(session, kohde, asiakas, do_update)
    create_or_update_yhteystieto_osapuoli(session, kohde, asiakas, do_update)

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
    def write(
        self,
        jkr_data: JkrData,
        tiedontuottaja_lyhenne: str,
        ala_luo: bool,
        ala_paivita: bool,
    ):
        try:
            print(len(jkr_data.asiakkaat))
            progress = Progress(len(jkr_data.asiakkaat))

            prt_counts, kitu_counts, address_counts = count(jkr_data)
            # print(prt_counts)
            # print(kitu_counts)
            # print(address_counts)
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

                    import_asiakastiedot(
                        session,
                        asiakas,
                        jkr_data.alkupvm,
                        jkr_data.loppupvm,
                        tiedontuottajat[urakoitsija_tunnus],
                        not ala_luo,
                        not ala_paivita,
                        prt_counts,
                        kitu_counts,
                        address_counts,
                    )
                session.commit()
                progress.complete()

                # print("Importoidaan sopimukset")
                # progress.reset()
                # for asiakas in jkr_data.asiakkaat.values():
                #     progress.tick()

                #     # Asiakastieto may come from different urakoitsija than the
                #     # immediate tiedontuottaja. In such a case, the asiakas
                #     # information takes precedence.
                #     urakoitsija_tunnus = asiakas.asiakasnumero.jarjestelma

                #     kohde = get_kohde_by_asiakasnumero(session, asiakas.asiakasnumero)
                #     update_sopimukset_for_kohde(
                #         session,
                #         asiakas,
                #         kohde,
                #         asiakas.sopimukset,
                #         urakoitsija,
                #         jkr_data.loppupvm,
                #     )
                #     session.commit()
                #     break
                # progress.complete()

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
