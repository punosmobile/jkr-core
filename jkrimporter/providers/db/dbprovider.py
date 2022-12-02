import datetime
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, FrozenSet, List, NamedTuple, Optional, Set, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from jkrimporter.model import Asiakas, JkrData, Tunnus
from jkrimporter.model import Tyhjennystapahtuma as JkrTyhjennystapahtuma
from jkrimporter.utils.intervals import IntervalCounter
from jkrimporter.utils.progress import Progress

from . import codes
from .codes import init_code_objects
from .database import engine
from .models import (
    Katu,
    Kohde,
    KohteenOsapuolet,
    KohteenRakennukset,
    Kuljetus,
    Osapuoli,
    Osoite,
    RakennuksenVanhimmat,
    Rakennus,
    Tiedontuottaja,
    UlkoinenAsiakastieto,
)
from .services.buildings import Kohdetiedot, Rakennustiedot
from .services.buildings import counts as building_counts
from .services.buildings import (
    find_building_candidates_for_kohde,
    find_buildings_for_kohde,
    freeze,
)
from .services.kohde import (
    add_ulkoinen_asiakastieto_for_kohde,
    create_multiple_and_uninhabited_kohteet,
    create_new_kohde,
    create_paritalo_kohteet,
    create_perusmaksurekisteri_kohteet,
    create_single_asunto_kohteet,
    find_kohde_by_asiakastiedot,
    match_asiakastieto,
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

        # TODO: here we have the assumption that there is only one kuljetus
        # for a given period and jatetyyppi. It may be false, there may even
        # be more than one kuljetus for a period and jatetyyppi with the *same*
        # urakoitsija, with the same *or* different customer ids.
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


def import_dvv_kohteet(
    session: Session, alkupvm: str, loppupvm: str, perusmaksutiedosto: Optional[Path]
):
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
    single_asunto_kohteet = create_single_asunto_kohteet(session, alkupvm, loppupvm)
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
            session, alkupvm, loppupvm, perusmaksutiedosto
        )
    session.commit()
    print(f"Imported {len(perusmaksukohteet)} kohteet with perusmaksu data")

    # 4) Paritalot: molemmille huoneistoille omat kohteet
    # Does it matter this is imported after 7? -No, because paritalot will not
    # interact with 7.
    # - Asiakas on kumpikin vanhin asukas erikseen.
    # - Kiinteistöllä kaksi kohdetta joilla sama rakennus, muita rakennuksia ei liitetä.
    # TODO: add all buildings on kiinteistö?
    paritalo_kohteet = create_paritalo_kohteet(session, alkupvm, loppupvm)
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
    multiple_and_uninhabited_kohteet = create_multiple_and_uninhabited_kohteet(
        session, alkupvm, loppupvm
    )
    session.commit()
    print(f"Imported {len(multiple_and_uninhabited_kohteet)} remaining kohteet")


class DbProvider:
    # preload all the important data indexed in memory so we don't have to do expensive
    # db queries at every point
    rakennustiedot_by_prt: dict[str, Rakennustiedot] = {}
    rakennustiedot_by_kiinteistotunnus: dict[str, Set[Rakennustiedot]] = defaultdict(
        set
    )
    rakennustiedot_by_ytunnus: dict[str, Set[Rakennustiedot]] = defaultdict(set)
    rakennustiedot_by_address: dict[tuple, Set[Rakennustiedot]] = defaultdict(set)
    rakennustiedot_by_asiakastunnus: dict[Tunnus, Set[Rakennustiedot]] = defaultdict(
        set
    )
    osapuolet_by_id: dict[str, Osapuoli] = {}
    # This extra step is because mutable sets are not hashable.
    kohdetiedot_by_prt_and_kohde_id: dict[str, dict[str, Kohdetiedot]] = defaultdict(
        defaultdict
    )

    def init_provider(self, session):
        print("Caching osapuolet to memory...")
        osapuolet = session.execute(select(Osapuoli)).all()
        self.osapuolet_by_id = {row[0].id: row[0] for row in osapuolet}

        print("Caching building information to memory...")
        # This is the huge query, will take some seconds and then some.
        db_rakennustiedot: List[
            (
                Rakennus,
                RakennuksenVanhimmat,
                Osapuoli,
                Osoite,
                Katu,
                Kohde,
                UlkoinenAsiakastieto,
                KohteenOsapuolet,
            )
        ] = session.execute(
            select(
                Rakennus,
                RakennuksenVanhimmat,
                Osapuoli,
                Osoite,
                Katu,
                Kohde,
                UlkoinenAsiakastieto,
                KohteenOsapuolet,
            )
            # include buildings without inhabitants, e.g. vapaa-ajanasunnot
            .join(Rakennus.rakennuksen_vanhimmat_collection, isouter=True)
            .join(Rakennus.osapuoli_collection)
            .join(Rakennus.osoite_collection)
            .join(Osoite.katu)
            .join(Rakennus.kohde_collection)
            # include kohteet that don't yet have asiakas
            .join(Kohde.ulkoinen_asiakastieto_collection, isouter=True)
            .join(Kohde.kohteen_osapuolet_collection)
        ).all()
        # construct rakennustiedot and kohdetiedot tuples, indexing with prt
        for (
            rakennus,
            vanhin,
            osapuoli,
            osoite,
            katu,
            kohde,
            asiakastieto,
            kohteen_osapuoli,
        ) in db_rakennustiedot:
            # Rakennustiedot must contain sets, no frozen sets, at this point.
            # Will typecast to frozen sets *after* constructing.
            if rakennus.prt not in self.rakennustiedot_by_prt:
                self.rakennustiedot_by_prt[rakennus.prt] = Rakennustiedot(
                    rakennus,
                    set(),
                    set(),
                    set(),
                    set(),
                )
            self.rakennustiedot_by_prt[rakennus.prt].osapuolet.add(osapuoli)
            osoitetiedot = (osoite, katu)
            self.rakennustiedot_by_prt[rakennus.prt].osoitteet.add(osoitetiedot)
            if vanhin:
                self.rakennustiedot_by_prt[rakennus.prt].vanhimmat.add(vanhin)
            # Kohdetiedot must contain sets, no frozen sets, at this point.
            # Will typecast to frozen sets *after* constructing.
            if kohde:
                if kohde.id not in self.kohdetiedot_by_prt_and_kohde_id[rakennus.prt]:
                    self.kohdetiedot_by_prt_and_kohde_id[rakennus.prt][
                        kohde.id
                    ] = Kohdetiedot(
                        kohde,
                        set(),
                        set(),
                    )
                self.kohdetiedot_by_prt_and_kohde_id[rakennus.prt][
                    kohde.id
                ].kohteen_osapuolet.add(kohteen_osapuoli)
                if asiakastieto:
                    self.kohdetiedot_by_prt_and_kohde_id[rakennus.prt][
                        kohde.id
                    ].ulkoiset_asiakastiedot.add(asiakastieto)
        # Combine kohdetiedot and rakennustiedot.
        for prt, kohdetiedot_dict in self.kohdetiedot_by_prt_and_kohde_id.items():
            # print('combining rakennustiedot')
            *rakennustiedot, empty_kohteet = self.rakennustiedot_by_prt[prt]
            kohteet = frozenset(
                Kohdetiedot(*freeze(kohdetiedot))
                for kohdetiedot in kohdetiedot_dict.values()
            )
            # print('got kohteet')
            # print(kohteet)
            self.rakennustiedot_by_prt[prt] = Rakennustiedot(
                *freeze(rakennustiedot), kohteet
            )
            # print('got rakennustiedot')
            # print(self.rakennustiedot_by_prt[prt])

        # create all other indexes
        for rakennustiedot in self.rakennustiedot_by_prt.values():
            # print('creating indexes')
            self.rakennustiedot_by_kiinteistotunnus[
                rakennustiedot.rakennus.kiinteistotunnus
            ].add(rakennustiedot)
            # print('got rakennustiedot')
            # print(rakennustiedot)
            for osapuoli in rakennustiedot.osapuolet:
                if osapuoli.ytunnus:
                    self.rakennustiedot_by_ytunnus[osapuoli.ytunnus].add(rakennustiedot)
            for osoite, katu in rakennustiedot.osoitteet:
                if katu.katunimi_fi:
                    # here again, osoite identity must be its salient strings combined,
                    # not the duplicated object. Don't use the whole Osoite model, we
                    # don't want to match osoitekirjain and asuntonumero here.
                    postinumero = osoite.posti_numero
                    katu = katu.katunimi_fi.lower()
                    osoitenumero = osoite.osoitenumero
                    self.rakennustiedot_by_address[
                        ((postinumero, katu, osoitenumero))
                    ].add(rakennustiedot)
            for kohdetiedot in rakennustiedot.kohteet:
                asiakastiedot = kohdetiedot.ulkoiset_asiakastiedot
                for asiakas in asiakastiedot:
                    tunnus = asiakas.tiedontuottaja_tunnus
                    ulkoinen_id = asiakas.ulkoinen_id
                    self.rakennustiedot_by_asiakastunnus[(tunnus, ulkoinen_id)].add(
                        rakennustiedot
                    )

    def find_and_update_kohde(
        self,
        session: "Session",
        asiakas: "Asiakas",
        do_create: bool,
        do_update: bool,
        prt_counts: Dict[str, int],
        kitu_counts: Dict[str, int],
        address_counts: Dict[str, int],
    ) -> "Union[Kohde, None]":
        kohde = None
        print("trying to find rakennustiedot with asiakasnumero")
        print(asiakas.asiakasnumero)
        rakennustiedot = self.rakennustiedot_by_asiakastunnus[asiakas.asiakasnumero]
        if rakennustiedot:
            print("Tunnus found")
            # Same asiakastunnus may have multiple rakennus and each rakennus
            # may have multiple kohde.
            # Just check the kohteet for first rakennus.
            kohdetiedot = next(iter(rakennustiedot)).kohteet
            for tiedot in kohdetiedot:
                kohde = tiedot.kohde
                ulkoinen_asiakastieto = match_asiakastieto(
                    tiedot.ulkoiset_asiakastiedot, asiakas.asiakasnumero
                )
                # For paritalot, we must to pick the kohde that had matching
                # asiakastieto.
                if ulkoinen_asiakastieto:
                    break

            update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas)
            if do_update:
                update_kohde(kohde, asiakas)
        else:
            print("Tunnus not found, looking by prt, address and other data")
            kohde = find_kohde_by_asiakastiedot(
                self.rakennustiedot_by_prt,
                self.rakennustiedot_by_kiinteistotunnus,
                self.rakennustiedot_by_ytunnus,
                self.rakennustiedot_by_address,
                self.osapuolet_by_id,
                asiakas,
            )

            if kohde:
                print("Kohde found")
                add_ulkoinen_asiakastieto_for_kohde(session, kohde, asiakas)
                if do_update:
                    update_kohde(kohde, asiakas)
            elif do_create:
                print("Kohde not found, creating new kohde")
                kohde = create_new_kohde(session, asiakas)
            if kohde and not kohde.rakennus_collection:
                print("Adding new buildings for kohde...")
                rakennustiedot = find_buildings_for_kohde(
                    self.rakennustiedot_by_prt,
                    self.rakennustiedot_by_kiinteistotunnus,
                    self.rakennustiedot_by_ytunnus,
                    self.rakennustiedot_by_address,
                    self.osapuolet_by_id,
                    asiakas,
                    prt_counts,
                    kitu_counts,
                    address_counts,
                )
                if rakennustiedot:
                    kohde.rakennus_collection = [
                        tiedot.rakennus for tiedot in rakennustiedot
                    ]
                elif not kohde.ehdokasrakennus_collection:
                    # TODO: refactor to need no queries if this happens often
                    building_candidates = find_building_candidates_for_kohde(
                        session, asiakas
                    )
                    if building_candidates:
                        kohde.ehdokasrakennus_collection = building_candidates

        return kohde

    def import_asiakastiedot(
        self,
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

        kohde = self.find_and_update_kohde(
            session,
            asiakas,
            do_create,
            do_update,
            prt_counts,
            kitu_counts,
            address_counts,
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
                self.init_provider(session)

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

                    self.import_asiakastiedot(
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

        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(building_counts)

    def write_dvv_kohteet(
        self, alkupvm: str, loppupvm: str, perusmaksutiedosto: Optional[Path]
    ):
        """
        This method creates kohteet from dvv data existing in the database.
        Alkupvm and loppupvm may be used to define the period the kohteet
        should be considered to be valid.

        Optionally, a perusmaksurekisteri xlsx file may be provided to
        combine dvv buildings with the same customer id.
        """
        try:
            with Session(engine) as session:
                init_code_objects(session)
                print("Luodaan kohteet")
                import_dvv_kohteet(session, alkupvm, loppupvm, perusmaksutiedosto)

        except Exception as e:
            logger.exception(e)
        finally:
            logger.debug(building_counts)
