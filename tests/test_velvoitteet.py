"""
Testit velvoitteiden ja velvoiteyhteenvetojen muodostumiselle (LAH-228, LAH-229).

DVV-tuonti luo kohteet, minkä jälkeen kannan funktio jkr.update_velvoitteet()
muodostaa kohteille velvoitteet (jkr.velvoite) ja velvoiteyhteenvedot
(jkr.velvoiteyhteenveto) velvoite- ja velvoiteyhteenvetomallien sääntöjen
(saanto) perusteella.

Säännöt (ks. R__Add_velvoite_management_functions.sql):
- Velvoite muodostuu kohteelle, joka kuuluu velvoitemallin saanto-näkymään,
  kunhan kohdetyyppi ei ole 8/9 (MUU) ja jätetyyppi sopii kohdetyypille.
- Velvoiteyhteenveto muodostuu vain kohteille, joiden kohdetyyppi on 5, 6 tai 7
  (hapa/biohapa/asuinkiinteistö).
- update_velvoitteet on idempotentti: uudelleenajo ei luo duplikaatteja eikä
  muuta avoimien velvoitteiden määrää.

Testit tarkistavat rakenteelliset invariantit (ei kovakoodattuja lukumääriä),
jotta ne kestävät testiaineiston muutokset mutta havaitsevat todelliset
regressiot velvoitelogiikassa.
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet


def _cleanup(engine):
    """Poistaa kohteet, velvoitteet ja velvoiteyhteenvedot puhtaaseen tilaan."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM jkr.velvoiteyhteenveto_status"))
        conn.execute(text("DELETE FROM jkr.velvoiteyhteenveto"))
        conn.execute(text("DELETE FROM jkr.velvoite_status"))
        conn.execute(text("DELETE FROM jkr.velvoite"))
        conn.execute(text("DELETE FROM jkr.kompostorin_kohteet"))
        conn.execute(text("DELETE FROM jkr.kompostori"))
        conn.execute(text("DELETE FROM jkr.keskeytys"))
        conn.execute(text("DELETE FROM jkr.kuljetus"))
        conn.execute(text("DELETE FROM jkr.tyhjennysvali"))
        conn.execute(text("DELETE FROM jkr.sopimus"))
        conn.execute(text("DELETE FROM jkr.viranomaispaatokset"))
        conn.execute(text("DELETE FROM jkr.kohteen_osapuolet"))
        conn.execute(text("DELETE FROM jkr.kohteen_rakennukset"))
        conn.execute(text("DELETE FROM jkr.kohde"))
        conn.execute(text("DELETE FROM jkr.dvv_poimintapvm"))
        conn.execute(text("DELETE FROM jkr.hapa_aineisto"))
        conn.execute(text(
            "DELETE FROM jkr.osapuoli "
            "WHERE tiedontuottaja_tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.commit()


@pytest.fixture(scope="module")
def velvoite_setup():
    """Tuo DVV-kohteet, ottaa talteen 'ennen'-tilan ja ajaa update_velvoitteet.

    Palauttaa (engine, ennen), jossa ennen-sanakirja sisältää avoimien
    velvoitteiden ja velvoiteyhteenvetojen määrät ennen update_velvoitteet-ajoa.
    """
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    _cleanup(engine)
    source = Path(__file__).parent / "data" / "test_data_import"
    with Session(engine) as session:
        init_code_objects(session)
        import_dvv_kohteet(
            session,
            poimintapvm=datetime.strptime("28.1.2022", "%d.%m.%Y").date(),
            perusmaksutiedosto=source / "perusmaksurekisteri.xlsx",
        )

    with engine.connect() as conn:
        ennen = {
            "velvoite": conn.execute(
                text("SELECT count(*) FROM jkr.velvoite WHERE loppupvm IS NULL")
            ).scalar(),
            "yhteenveto": conn.execute(
                text("SELECT count(*) FROM jkr.velvoiteyhteenveto WHERE loppupvm IS NULL")
            ).scalar(),
        }
        conn.execute(text("SELECT jkr.update_velvoitteet()"))
        conn.commit()

    try:
        yield engine, ennen
    finally:
        _cleanup(engine)


class TestVelvoitteidenMuodostuminen:
    """LAH-229: velvoitteiden muodostuminen DVV-tuonnin kohteille."""

    def test_ennen_paivitysta_ei_velvoitteita(self, velvoite_setup):
        _, ennen = velvoite_setup
        assert ennen["velvoite"] == 0, \
            "Ennen update_velvoitteet-ajoa ei pitäisi olla avoimia velvoitteita"

    def test_velvoitteita_muodostuu(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            avoimet = conn.execute(
                text("SELECT count(*) FROM jkr.velvoite WHERE loppupvm IS NULL")
            ).scalar()
        assert avoimet > 0, "update_velvoitteet ei muodostanut yhtään velvoitetta"

    def test_jokaisella_kohteella_on_velvoite(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            # Kohteet (tyyppi 5/6/7) ilman yhtään avointa velvoitetta
            ilman = conn.execute(text(
                "SELECT count(*) FROM jkr.kohde k "
                "WHERE k.kohdetyyppi_id IN (5, 6, 7) "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM jkr.velvoite v "
                "  WHERE v.kohde_id = k.id AND v.loppupvm IS NULL)"
            )).scalar()
        assert ilman == 0, \
            f"{ilman} kohteella (tyyppi 5/6/7) ei ole yhtään velvoitetta"

    def test_muu_kohteilla_ei_velvoitetta(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            # Velvoitteita ei saa muodostua MUU/EI-kohteille (kohdetyyppi 8/9)
            virheelliset = conn.execute(text(
                "SELECT count(*) FROM jkr.velvoite v "
                "JOIN jkr.kohde k ON k.id = v.kohde_id "
                "WHERE v.loppupvm IS NULL AND k.kohdetyyppi_id IN (8, 9)"
            )).scalar()
        assert virheelliset == 0, \
            "MUU-tyyppisille kohteille (8/9) ei saa muodostua velvoitteita"

    def test_paivitys_on_idempotentti(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            ennen = conn.execute(
                text("SELECT count(*) FROM jkr.velvoite WHERE loppupvm IS NULL")
            ).scalar()
            conn.execute(text("SELECT jkr.update_velvoitteet()"))
            conn.commit()
            jalkeen = conn.execute(
                text("SELECT count(*) FROM jkr.velvoite WHERE loppupvm IS NULL")
            ).scalar()
        assert ennen == jalkeen, (
            "update_velvoitteet ei ole idempotentti: avoimien velvoitteiden määrä "
            f"muuttui {ennen} -> {jalkeen}"
        )


class TestVelvoiteyhteenveto:
    """LAH-228: velvoiteyhteenvetojen muodostuminen."""

    def test_ennen_paivitysta_ei_yhteenvetoja(self, velvoite_setup):
        _, ennen = velvoite_setup
        assert ennen["yhteenveto"] == 0, \
            "Ennen update_velvoitteet-ajoa ei pitäisi olla avoimia yhteenvetoja"

    def test_yhteenvetoja_muodostuu(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            avoimet = conn.execute(
                text("SELECT count(*) FROM jkr.velvoiteyhteenveto WHERE loppupvm IS NULL")
            ).scalar()
        assert avoimet > 0, "update_velvoitteet ei muodostanut yhtään velvoiteyhteenvetoa"

    def test_jokaisella_567_kohteella_on_yhteenveto(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            ilman = conn.execute(text(
                "SELECT count(*) FROM jkr.kohde k "
                "WHERE k.kohdetyyppi_id IN (5, 6, 7) "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM jkr.velvoiteyhteenveto vy "
                "  WHERE vy.kohde_id = k.id AND vy.loppupvm IS NULL)"
            )).scalar()
        assert ilman == 0, \
            f"{ilman} kohteella (tyyppi 5/6/7) ei ole velvoiteyhteenvetoa"

    def test_yhteenveto_vain_kohdetyypeille_567(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            virheelliset = conn.execute(text(
                "SELECT count(*) FROM jkr.velvoiteyhteenveto vy "
                "JOIN jkr.kohde k ON k.id = vy.kohde_id "
                "WHERE vy.loppupvm IS NULL AND k.kohdetyyppi_id NOT IN (5, 6, 7)"
            )).scalar()
        assert virheelliset == 0, (
            "Velvoiteyhteenvetoja ei saa muodostua muille kuin kohdetyypeille 5/6/7"
        )

    def test_jokainen_yhteenveto_viittaa_malliin(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            orvot = conn.execute(text(
                "SELECT count(*) FROM jkr.velvoiteyhteenveto vy "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM jkr.velvoiteyhteenvetomalli m "
                "  WHERE m.id = vy.velvoiteyhteenvetomalli_id)"
            )).scalar()
        assert orvot == 0, "Velvoiteyhteenveto viittaa olemattomaan malliin"

    def test_paivitys_on_idempotentti(self, velvoite_setup):
        engine, _ = velvoite_setup
        with engine.connect() as conn:
            ennen = conn.execute(
                text("SELECT count(*) FROM jkr.velvoiteyhteenveto WHERE loppupvm IS NULL")
            ).scalar()
            conn.execute(text("SELECT jkr.update_velvoitteet()"))
            conn.commit()
            jalkeen = conn.execute(
                text("SELECT count(*) FROM jkr.velvoiteyhteenveto WHERE loppupvm IS NULL")
            ).scalar()
        assert ennen == jalkeen, (
            "update_velvoitteet ei ole idempotentti velvoiteyhteenvedoille: "
            f"{ennen} -> {jalkeen}"
        )
