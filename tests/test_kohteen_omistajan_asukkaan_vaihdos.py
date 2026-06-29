"""
Testit kohteen säilymiselle ja päivittymiselle omistajan/asukkaan vaihtuessa
(LAH-230).

DVV-päivityksessä kohteen kohtalo riippuu siitä, ovatko rakennuksen omistajat
tai asukkaat vaihtuneet edellisen poiminnan jälkeen. Tämä päätös tehdään
funktioissa:
    - osapuoli.should_remove_from_kohde_via_omistaja
    - osapuoli.should_remove_from_kohde_via_asukas
joissa True tarkoittaa "rakennus irrotetaan vanhasta kohteesta" (kohde
päivittyy / uusi kohde luodaan) ja False tarkoittaa "kohde säilyy ennallaan".

Keskeinen sääntö (ml. leski-tilanne): jos rakennuksella on nykyinen omistaja
tai asukas, jonka omistus/asuminen on alkanut jo *ennen edellistä poimintaa*,
kohde säilyy ennallaan. Näin esim. leski, jonka omistus alkaa ennen edellistä
poimintaa, ei aiheuta kohteen uudelleenluontia.

Testit rakentavat hallitut omistaja-/asukasrivit synteettiselle rakennukselle
ja kutsuvat päätösfunktioita suoraan, jotta kaikki kolme skenaariota
(omistaja vaihtuu, asukas vaihtuu, leski säilyttää kohteen) tulevat katetuiksi.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.services.osapuoli import (
    should_remove_from_kohde_via_asukas,
    should_remove_from_kohde_via_omistaja,
)

# Poimintapäivämäärät: edellinen ja nykyinen
EDELLINEN_POIMINTA = date(2022, 1, 28)
NYKYINEN_POIMINTA = date(2023, 1, 31)

# Omistuksen/asumisen alkupäivät suhteessa edelliseen poimintaan
ENNEN_EDELLISTA = date(2020, 1, 1)   # < EDELLINEN_POIMINTA
EDELLISEN_JALKEEN = date(2022, 6, 17)  # > EDELLINEN_POIMINTA


@pytest.fixture
def db():
    """Tarjoaa istunnon ja apufunktiot synteettisen testidatan luontiin.

    Luodut rakennukset ja osapuolet siivotaan testin jälkeen (rakennuksen
    poisto poistaa cascade-säännöllä myös omistaja- ja asukasrivit).
    """
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    session = Session(engine)
    luodut = {"rakennus": [], "osapuoli": []}

    def new_rakennus():
        rid = session.execute(
            text("INSERT INTO jkr.rakennus DEFAULT VALUES RETURNING id")
        ).scalar()
        luodut["rakennus"].append(rid)
        return rid

    def new_osapuoli(nimi, henkilotunnus):
        oid = session.execute(
            text(
                "INSERT INTO jkr.osapuoli (nimi, henkilotunnus) "
                "VALUES (:nimi, :hetu) RETURNING id"
            ),
            {"nimi": nimi, "hetu": henkilotunnus},
        ).scalar()
        luodut["osapuoli"].append(oid)
        return oid

    def add_omistaja(rakennus_id, osapuoli_id, alkupvm, loppupvm=None):
        session.execute(
            text(
                "INSERT INTO jkr.rakennuksen_omistajat "
                "(rakennus_id, osapuoli_id, omistuksen_alkupvm, omistuksen_loppupvm) "
                "VALUES (:r, :o, :a, :l)"
            ),
            {"r": rakennus_id, "o": osapuoli_id, "a": alkupvm, "l": loppupvm},
        )

    def add_asukas(rakennus_id, osapuoli_id, alkupvm, loppupvm=None):
        session.execute(
            text(
                "INSERT INTO jkr.rakennuksen_vanhimmat "
                "(rakennus_id, osapuoli_id, alkupvm, loppupvm) "
                "VALUES (:r, :o, :a, :l)"
            ),
            {"r": rakennus_id, "o": osapuoli_id, "a": alkupvm, "l": loppupvm},
        )

    helpers = SimpleNamespace(
        session=session,
        new_rakennus=new_rakennus,
        new_osapuoli=new_osapuoli,
        add_omistaja=add_omistaja,
        add_asukas=add_asukas,
        commit=session.commit,
    )

    try:
        yield helpers
    finally:
        session.rollback()
        for rid in luodut["rakennus"]:
            session.execute(text("DELETE FROM jkr.rakennus WHERE id = :i"), {"i": rid})
        for oid in luodut["osapuoli"]:
            session.execute(text("DELETE FROM jkr.osapuoli WHERE id = :i"), {"i": oid})
        session.commit()
        session.close()


class TestKohteenSailyminenOmistajanVaihtuessa:
    """LAH-230: omistajan vaihtuminen ja leski-tilanne (should_remove_..._omistaja)."""

    def test_leski_omistus_alkanut_ennen_edellista_poimintaa_kohde_sailyy(self, db):
        # Leski: edellinen omistaja kuollut (poistunut), uusi omistaja jonka
        # omistus alkaa ENNEN edellistä poimintaa -> kohteen tulee säilyä.
        rakennus_id = db.new_rakennus()
        vainaja = db.new_osapuoli("Vainaja Vilho", "010130-001A")
        leski = db.new_osapuoli("Leski Liisa", "020235-002B")
        db.add_omistaja(rakennus_id, vainaja, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_omistaja(rakennus_id, leski, ENNEN_EDELLISTA, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_omistaja(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is False, \
            "Leski (omistus alkanut ennen edellistä poimintaa) -> kohteen tulee säilyä"

    def test_omistaja_vaihtunut_kokonaan_kohde_paivittyy(self, db):
        # Vanha omistaja poistunut, uusi omistaja eri henkilö jonka omistus
        # alkaa vasta edellisen poiminnan JÄLKEEN -> rakennus irrotetaan kohteelta.
        rakennus_id = db.new_rakennus()
        vanha = db.new_osapuoli("Vanha Omistaja", "030340-003C")
        uusi = db.new_osapuoli("Uusi Omistaja", "040445-004D")
        db.add_omistaja(rakennus_id, vanha, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_omistaja(rakennus_id, uusi, EDELLISEN_JALKEEN, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_omistaja(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is True, \
            "Omistaja vaihtunut kokonaan edellisen poiminnan jälkeen -> kohde päivittyy"

    def test_sama_omistaja_jatkaa_kohde_sailyy(self, db):
        # Sama omistaja (sama henkilötunnus) jatkaa, vaikka omistusrivi olisi
        # uusittu edellisen poiminnan jälkeen -> kohteen tulee säilyä (yhtäläisyys).
        # Sama osapuoli kahdella omistusrivillä: vanha päättynyt, uusi voimassa.
        rakennus_id = db.new_rakennus()
        sama = db.new_osapuoli("Pysyvä Omistaja", "050550-005E")
        db.add_omistaja(rakennus_id, sama, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_omistaja(rakennus_id, sama, EDELLISEN_JALKEEN, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_omistaja(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is False, \
            "Sama omistaja jatkaa -> kohteen tulee säilyä"


class TestKohteenSailyminenAsukkaanVaihtuessa:
    """LAH-230: asukkaan vaihtuminen (should_remove_..._asukas)."""

    def test_asukas_vaihtunut_kohde_paivittyy(self, db):
        # Vanha asukas poistunut, uusi asukas eri henkilö joka on muuttanut
        # vasta edellisen poiminnan JÄLKEEN -> rakennus irrotetaan kohteelta.
        rakennus_id = db.new_rakennus()
        vanha = db.new_osapuoli("Vanha Asukas", "060660-006F")
        uusi = db.new_osapuoli("Uusi Asukas", "070770-007G")
        db.add_asukas(rakennus_id, vanha, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_asukas(rakennus_id, uusi, EDELLISEN_JALKEEN, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_asukas(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is True, \
            "Asukas vaihtunut kokonaan edellisen poiminnan jälkeen -> kohde päivittyy"

    def test_asukas_muuttanut_ennen_edellista_poimintaa_kohde_sailyy(self, db):
        # Uusi asukas on muuttanut taloon ENNEN edellistä poimintaa
        # (esim. samassa taloudessa asunut) -> kohteen tulee säilyä.
        rakennus_id = db.new_rakennus()
        poistunut = db.new_osapuoli("Poistunut Asukas", "080880-008H")
        jaava = db.new_osapuoli("Jäävä Asukas", "090990-009I")
        db.add_asukas(rakennus_id, poistunut, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_asukas(rakennus_id, jaava, ENNEN_EDELLISTA, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_asukas(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is False, \
            "Asukas muuttanut ennen edellistä poimintaa -> kohteen tulee säilyä"

    def test_sama_asukas_jatkaa_kohde_sailyy(self, db):
        # Sama asukas (sama henkilötunnus) on sekä poistuneissa että nykyisissä
        # -> yhtäläisyys -> kohteen tulee säilyä.
        # Sama osapuoli kahdella asukasrivillä: vanha päättynyt, uusi voimassa.
        rakennus_id = db.new_rakennus()
        sama = db.new_osapuoli("Pysyvä Asukas", "101000-010J")
        db.add_asukas(rakennus_id, sama, ENNEN_EDELLISTA, loppupvm=EDELLISEN_JALKEEN)
        db.add_asukas(rakennus_id, sama, EDELLISEN_JALKEEN, loppupvm=None)
        db.commit()

        poistetaan = should_remove_from_kohde_via_asukas(
            db.session, rakennus_id, NYKYINEN_POIMINTA, EDELLINEN_POIMINTA
        )
        assert poistetaan is False, \
            "Sama asukas jatkaa -> kohteen tulee säilyä"
