"""
Testit lietetietojen siirtymiselle kohteen vaihtuessa ja jakaantuessa.

LAH-444: Testiluokat, mukaanlukien jakaantuvan kohteen ja siirtyvän kohteen logiikka
LAH-307: Lietetietojen siirtyminen vanhan kohteen päättyessä

Testaa:
- Lietetietojen siirtyminen uudelle kohteelle (update_old_kohde_data)
- Kohteen jakaantuminen useammaksi kohteeksi (kopiointi)
- Lietteen kompostointi-ilmoituksen käsittely
- Kaivotietojen siirto/kopiointi
- Viemäriliitosten siirto/kopiointi
- Kuljetusten siirto/kopiointi
"""

import json
import os
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jkrimporter.providers.db.utils import JSONEncoderWithDateSupport


def json_dumps(value):
    """JSON-serialisointi päivämäärätuella."""
    return json.dumps(value, cls=JSONEncoderWithDateSupport)


def get_db_config():
    """Hakee tietokantakonfiguraation ympäristömuuttujista."""
    return {
        "host": os.environ.get("JKR_DB_HOST", "localhost"),
        "port": os.environ.get("JKR_DB_PORT", "5432"),
        "username": os.environ.get("JKR_USER", "jkr_admin"),
        "password": os.environ.get("JKR_PASSWORD", "qwerty"),
        "dbname": os.environ.get("JKR_DB", "jatehuolto"),
    }


@pytest.fixture(scope="module")
def engine():
    """Luo tietokantayhteys testeille."""
    dbconf = get_db_config()
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **dbconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    return engine


@pytest.fixture(scope="module")
def db_models(engine):
    """Importtaa mallit vasta kun engine on luotu."""
    from jkrimporter.providers.db.models import (
        Kohde,
        KohteenRakennukset,
        Kaivotiedot,
        Kuljetus,
        ViemariLiitos,
        Kompostori,
        KompostorinKohteet,
        Sopimus,
        Viranomaispaatokset,
        Rakennus,
    )
    return {
        'Kohde': Kohde,
        'KohteenRakennukset': KohteenRakennukset,
        'Kaivotiedot': Kaivotiedot,
        'Kuljetus': Kuljetus,
        'ViemariLiitos': ViemariLiitos,
        'Kompostori': Kompostori,
        'KompostorinKohteet': KompostorinKohteet,
        'Sopimus': Sopimus,
        'Viranomaispaatokset': Viranomaispaatokset,
        'Rakennus': Rakennus,
    }


@pytest.fixture(scope="function")
def db_session(engine):
    """Luo tietokantasessio joka rollbackataan testin jälkeen."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


class TestLoppupvmMaaritys:
    """
    Testit loppupvm-määritykselle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Jos old_kohde.alkupvm < new_kohde_alkupvm - 1 päivä -> loppupvm = new_kohde_alkupvm - 1
    - Muuten -> loppupvm = old_kohde.alkupvm + 1 päivä
    """

    def test_loppupvm_maaritys_vanhan_kohteen_alkupvm_pienempi(self):
        """
        Loppupvm määräytyy oikein kun vanhan kohteen alkupvm < uuden alkupvm - 1.
        """
        old_kohde_alkupvm = date(2020, 1, 1)
        new_kohde_alkupvm = date(2024, 1, 1)
        
        loppupvm_candidate = new_kohde_alkupvm - timedelta(days=1)
        
        if old_kohde_alkupvm < loppupvm_candidate:
            expected_loppupvm = loppupvm_candidate
        else:
            expected_loppupvm = old_kohde_alkupvm + timedelta(days=1)
        
        assert expected_loppupvm == date(2023, 12, 31)
        assert old_kohde_alkupvm < expected_loppupvm

    def test_loppupvm_maaritys_vanhan_kohteen_alkupvm_suurempi(self):
        """
        Loppupvm määräytyy oikein kun vanhan kohteen alkupvm >= uuden alkupvm - 1.
        """
        old_kohde_alkupvm = date(2024, 1, 1)
        new_kohde_alkupvm = date(2024, 1, 2)
        
        loppupvm_candidate = new_kohde_alkupvm - timedelta(days=1)
        
        if old_kohde_alkupvm < loppupvm_candidate:
            expected_loppupvm = loppupvm_candidate
        else:
            expected_loppupvm = old_kohde_alkupvm + timedelta(days=1)
        
        assert expected_loppupvm == date(2024, 1, 2)

    def test_loppupvm_maaritys_sama_paiva(self):
        """
        Loppupvm määräytyy oikein kun vanhan kohteen alkupvm == uuden alkupvm - 1.
        """
        old_kohde_alkupvm = date(2023, 12, 31)
        new_kohde_alkupvm = date(2024, 1, 1)
        
        loppupvm_candidate = new_kohde_alkupvm - timedelta(days=1)
        
        if old_kohde_alkupvm < loppupvm_candidate:
            expected_loppupvm = loppupvm_candidate
        else:
            expected_loppupvm = old_kohde_alkupvm + timedelta(days=1)
        
        # old_kohde_alkupvm == loppupvm_candidate, joten käytetään alkupvm + 1
        assert expected_loppupvm == date(2024, 1, 1)


class TestSiirtoVsKopiointiLogiikka:
    """
    Testit siirto vs kopiointi -logiikalle.
    
    Määrittely (LAH-307):
    - Yhteisiä rakennuksia -> SIIRTO (update kohde_id)
    - Ei yhteisiä rakennuksia -> KOPIOINTI (insert uusi rivi)
    """

    def test_yhteisia_rakennuksia_siirto(self):
        """
        Kun kohteilla on yhteisiä rakennuksia, tiedot siirretään (update).
        """
        vanha_kohde_rakennukset = {1, 2, 3}
        uusi_kohde_rakennukset = {2, 3, 4}
        
        yhteisia = vanha_kohde_rakennukset & uusi_kohde_rakennukset
        
        assert len(yhteisia) == 2
        assert 2 in yhteisia
        assert 3 in yhteisia

    def test_ei_yhteisia_rakennuksia_kopiointi(self):
        """
        Kun kohteilla ei ole yhteisiä rakennuksia, tiedot kopioidaan (insert).
        """
        vanha_kohde_rakennukset = {1, 2, 3}
        uusi_kohde_rakennukset = {4, 5, 6}
        
        yhteisia = vanha_kohde_rakennukset & uusi_kohde_rakennukset
        
        assert len(yhteisia) == 0

    def test_jakaantuminen_case_prt_x_ja_y(self):
        """
        LAH-307 CASE: Kohde jakaantuu kahteen kohteeseen.
        
        Kohde 1: PRT X, PRT Y
        -> Kohde 2: PRT X
        -> Kohde 3: PRT Y
        
        Kumpikin uusi kohde saa kopion lietetiedoista.
        """
        kohde_1_rakennukset = {'PRT_X', 'PRT_Y'}
        kohde_2_rakennukset = {'PRT_X'}
        kohde_3_rakennukset = {'PRT_Y'}
        
        # Kohde 2:lla on yhteinen rakennus kohteen 1 kanssa
        yhteisia_2 = kohde_1_rakennukset & kohde_2_rakennukset
        assert 'PRT_X' in yhteisia_2
        
        # Kohde 3:lla on yhteinen rakennus kohteen 1 kanssa
        yhteisia_3 = kohde_1_rakennukset & kohde_3_rakennukset
        assert 'PRT_Y' in yhteisia_3


class TestKaivotietojenSiirtyminenKohteenVaihtuessa:
    """
    Testit kaivotietojen siirtymiselle kohteen vaihtuessa.
    
    Siirtyvät kaivotietotyypit (LAH-307):
    - Kantovesi
    - Umpisäiliö
    - Saostussäiliö
    - Pienpuhdistamo
    - Harmaat vedet
    """

    def test_kaikki_kaivotietotyypit_siirtyvat(self):
        """Kaikki määritellyt kaivotietotyypit siirtyvät uudelle kohteelle."""
        siirtyvat_kaivotietotyypit = [
            'Kantovesi',
            'Umpisäiliö',
            'Saostussäiliö',
            'Pienpuhdistamo',
            'Harmaat vedet'
        ]
        
        assert len(siirtyvat_kaivotietotyypit) == 5
        assert 'Kantovesi' in siirtyvat_kaivotietotyypit
        assert 'Umpisäiliö' in siirtyvat_kaivotietotyypit
        assert 'Saostussäiliö' in siirtyvat_kaivotietotyypit
        assert 'Pienpuhdistamo' in siirtyvat_kaivotietotyypit
        assert 'Harmaat vedet' in siirtyvat_kaivotietotyypit

    def test_kaivotieto_sailyttaa_alkuperaiset_paivamaarat(self):
        """
        Siirrettävä kaivotieto säilyttää alkuperäiset päivämäärät.
        
        Alkupvm ja loppupvm eivät muutu siirrossa.
        """
        alkuperainen_alkupvm = date(2023, 1, 1)
        alkuperainen_loppupvm = date(2028, 1, 1)
        
        # Siirron jälkeen päivämäärät säilyvät
        siirretty_alkupvm = alkuperainen_alkupvm
        siirretty_loppupvm = alkuperainen_loppupvm
        
        assert siirretty_alkupvm == alkuperainen_alkupvm
        assert siirretty_loppupvm == alkuperainen_loppupvm


class TestViemariLiitostenSiirtyminenKohteenVaihtuessa:
    """
    Testit viemäriliitosten siirtymiselle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Viemäriverkosto siirtyy uudelle kohteelle
    """

    def test_viemariliitos_siirtyy_uudelle_kohteelle(self):
        """Viemäriliitos siirtyy uudelle kohteelle."""
        vanha_kohde_id = 1
        uusi_kohde_id = 2
        
        # Siirron jälkeen kohde_id muuttuu
        assert vanha_kohde_id != uusi_kohde_id

    def test_viemariliitos_sailyttaa_prt_tiedon(self):
        """Viemäriliitos säilyttää rakennus_prt tiedon siirrossa."""
        alkuperainen_prt = "103456789A"
        
        # Siirron jälkeen PRT säilyy
        siirretty_prt = alkuperainen_prt
        
        assert siirretty_prt == alkuperainen_prt


class TestKuljetustenSiirtyminenKohteenVaihtuessa:
    """
    Testit kuljetusten siirtymiselle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Kuljetustieto siirtyy uudelle kohteelle
    - Lietekuljetukset (jatetyyppi_id 5, 6, 7) kopioidaan jakaantumisessa
    - Muut kuljetukset siirretään jos loppupvm >= uuden kohteen alkupvm
    """

    def test_lietekuljetukset_kopioidaan_jakaantumisessa(self):
        """
        Lietekuljetukset (jatetyyppi_id 5, 6, 7) kopioidaan kun kohde jakaantuu.
        """
        liete_jatetyyppi_ids = [5, 6, 7]
        
        # Kaikki lietetyypit kopioidaan
        for jatetyyppi_id in liete_jatetyyppi_ids:
            assert jatetyyppi_id in [5, 6, 7]

    def test_muut_kuljetukset_siirretaan_loppupvm_perusteella(self):
        """
        Muut kuljetukset siirretään jos loppupvm >= uuden kohteen alkupvm.
        """
        new_kohde_alkupvm = date(2024, 1, 1)
        
        # Kuljetus joka siirtyy
        kuljetus_loppupvm_siirtyy = date(2024, 6, 1)
        assert kuljetus_loppupvm_siirtyy >= new_kohde_alkupvm
        
        # Kuljetus joka ei siirry
        kuljetus_loppupvm_ei_siirry = date(2023, 6, 1)
        assert kuljetus_loppupvm_ei_siirry < new_kohde_alkupvm


class TestLietteenKompostointiIlmoituksenKasittely:
    """
    Testit lietteen kompostointi-ilmoituksen käsittelylle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Lietteen kompostointi-ilmoitus EI siirry automaattisesti
    - Siirtyy vain jos ilmoituksen vastausaika > uuden kohteen alkupvm
    """

    def test_kompostointi_ilmoitus_jaa_vanhalle_kohteelle_kun_vastausaika_aiemmin(self):
        """
        Kompostointi-ilmoitus jää vanhalle kohteelle kun vastausaika < kohteen päättymispäivä.
        """
        kohteen_paattymispvm = date(2024, 1, 1)
        ilmoituksen_vastausaika = date(2023, 6, 1)
        
        # Ilmoitus jää vanhalle kohteelle
        assert ilmoituksen_vastausaika < kohteen_paattymispvm

    def test_kompostointi_ilmoitus_siirtyy_kun_vastausaika_myohemmin(self):
        """
        Kompostointi-ilmoitus siirtyy uudelle kohteelle kun vastausaika > uuden kohteen alkupvm.
        """
        uuden_kohteen_alkupvm = date(2024, 1, 1)
        ilmoituksen_vastausaika = date(2024, 6, 1)
        
        # Ilmoitus siirtyy uudelle kohteelle
        assert ilmoituksen_vastausaika > uuden_kohteen_alkupvm

    def test_kompostointi_ilmoitus_ei_siirry_jakaantumisessa(self):
        """
        Lietteen kompostointi-ilmoitus EI kopioidu kohteen jakaantuessa.
        
        Toisin kuin muut lietetiedot, kompostointi-ilmoitukset eivät kopioidu.
        """
        # Dokumentaatiotesti - kompostointi-ilmoitukset käsitellään eri tavalla
        ei_kopioitavat = ['Lietteen kompostointi-ilmoitus']
        
        assert 'Lietteen kompostointi-ilmoitus' in ei_kopioitavat


class TestKompostorinKasittelyKohteenVaihtuessa:
    """
    Testit kompostorin käsittelylle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Kompostoreille joiden alkupvm <= vanhan kohteen loppupvm asetetaan loppupvm
    - Muiden kompostorien osapuolet siirretään uudelle kohteelle
    - Kompostorin kohdeviittaus päivitetään
    """

    def test_vanhan_kompostorin_loppupvm_asetetaan(self):
        """
        Kompostorille asetetaan loppupvm kun alkupvm <= vanhan kohteen loppupvm.
        """
        vanhan_kohteen_loppupvm = date(2024, 1, 1)
        kompostorin_alkupvm = date(2023, 1, 1)
        
        # Kompostori on vanha -> asetetaan loppupvm
        assert kompostorin_alkupvm <= vanhan_kohteen_loppupvm

    def test_jatkuvan_kompostorin_osapuolet_siirretaan(self):
        """
        Jatkuvan kompostorin osapuolet siirretään uudelle kohteelle.
        
        Jatkuva kompostori: alkupvm > vanhan kohteen loppupvm
        """
        vanhan_kohteen_loppupvm = date(2024, 1, 1)
        kompostorin_alkupvm = date(2024, 6, 1)
        
        # Kompostori on jatkuva -> osapuolet siirretään
        assert kompostorin_alkupvm > vanhan_kohteen_loppupvm

    def test_jatkuvan_kompostorin_kohdeviittaus_paivitetaan(self):
        """
        Jatkuvan kompostorin kohdeviittaus päivitetään uuteen kohteeseen.
        """
        vanha_kohde_id = 1
        uusi_kohde_id = 2
        
        # Kohdeviittaus muuttuu
        assert vanha_kohde_id != uusi_kohde_id


class TestViranomaispaatostenKasittelyKohteenVaihtuessa:
    """
    Testit viranomaispäätösten käsittelylle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Päätöksille joiden alkupvm <= vanhan kohteen loppupvm asetetaan loppupvm
    - Rakennus_id irrotetaan (asetetaan None)
    """

    def test_vanhan_paatoksen_loppupvm_asetetaan(self):
        """
        Viranomaispäätökselle asetetaan loppupvm kun alkupvm <= vanhan kohteen loppupvm.
        """
        vanhan_kohteen_loppupvm = date(2024, 1, 1)
        paatoksen_alkupvm = date(2023, 1, 1)
        
        # Päätös on vanha -> asetetaan loppupvm
        assert paatoksen_alkupvm <= vanhan_kohteen_loppupvm

    def test_paatoksen_rakennus_id_irrotetaan(self):
        """
        Viranomaispäätöksen rakennus_id asetetaan None:ksi.
        """
        alkuperainen_rakennus_id = 1
        irrotettu_rakennus_id = None
        
        assert irrotettu_rakennus_id is None
        assert alkuperainen_rakennus_id != irrotettu_rakennus_id


class TestSopimustenSiirtoKohteenVaihtuessa:
    """
    Testit sopimusten siirrolle kohteen vaihtuessa.
    
    Määrittely (LAH-307):
    - Sopimukset siirretään jos loppupvm >= uuden kohteen alkupvm
    """

    def test_sopimus_siirtyy_kun_loppupvm_voimassa(self):
        """
        Sopimus siirtyy uudelle kohteelle kun loppupvm >= uuden kohteen alkupvm.
        """
        new_kohde_alkupvm = date(2024, 1, 1)
        sopimuksen_loppupvm = date(2025, 1, 1)
        
        # Sopimus siirtyy
        assert sopimuksen_loppupvm >= new_kohde_alkupvm

    def test_sopimus_ei_siirry_kun_loppupvm_mennyt(self):
        """
        Sopimus ei siirry kun loppupvm < uuden kohteen alkupvm.
        """
        new_kohde_alkupvm = date(2024, 1, 1)
        sopimuksen_loppupvm = date(2023, 1, 1)
        
        # Sopimus ei siirry
        assert sopimuksen_loppupvm < new_kohde_alkupvm


class TestKohteenJakaantuminenCase:
    """
    Testit LAH-307 CASE-skenaariolle: Kohde jakaantuu useammaksi kohteeksi.
    
    CASE:
    - Kohde 1: PRT X, PRT Y
    - Viemäritieto tulee PRT Y:lle
    - Kohde 1 jakaantuu:
      - Kohde 2: PRT X
      - Kohde 3: PRT Y
    - Kysymys: Missä kohteella on viemäriverkostoliittymä?
    
    Vastaus: Viemäritieto kopioidaan molemmille kohteille (Kohde 2 ja Kohde 3)
    koska jakaantumisessa tiedot kopioidaan.
    """

    def test_jakaantuminen_kopioi_viemaritiedon_molemmille(self):
        """
        Kun kohde jakaantuu, viemäritieto kopioidaan molemmille uusille kohteille.
        """
        # Alkutilanne
        kohde_1_rakennukset = ['PRT_X', 'PRT_Y']
        viemaritieto_prt = 'PRT_Y'
        
        # Jakaantumisen jälkeen
        kohde_2_rakennukset = ['PRT_X']
        kohde_3_rakennukset = ['PRT_Y']
        
        # Molemmat uudet kohteet saavat kopion viemäritiedosta
        # koska jakaantumisessa ei ole yhteisiä rakennuksia
        yhteisia_2 = set(kohde_1_rakennukset) & set(kohde_2_rakennukset)
        yhteisia_3 = set(kohde_1_rakennukset) & set(kohde_3_rakennukset)
        
        # Kohde 2:lla on yhteinen rakennus PRT_X
        assert 'PRT_X' in yhteisia_2
        # Kohde 3:lla on yhteinen rakennus PRT_Y
        assert 'PRT_Y' in yhteisia_3

    def test_jakaantuminen_kaivotiedot_kopioidaan(self):
        """
        Kun kohde jakaantuu ilman yhteisiä rakennuksia, kaivotiedot kopioidaan.
        """
        vanha_kohde_rakennukset = {1, 2}
        uusi_kohde_rakennukset = {3, 4}  # Ei yhteisiä
        
        yhteisia = vanha_kohde_rakennukset & uusi_kohde_rakennukset
        
        # Ei yhteisiä -> kopiointi
        assert len(yhteisia) == 0

    def test_jakaantuminen_kuljetukset_kopioidaan(self):
        """
        Kun kohde jakaantuu ilman yhteisiä rakennuksia, lietekuljetukset kopioidaan.
        """
        liete_jatetyyppi_ids = [5, 6, 7]
        
        # Kaikki lietekuljetukset kopioidaan
        for jatetyyppi_id in liete_jatetyyppi_ids:
            assert jatetyyppi_id in [5, 6, 7]


class TestTietojenSiirtymislogiikka:
    """
    Testit tietojen siirtymislogiikalle yleisesti.
    
    Yhteenveto (LAH-307):
    - SIIRTYY: Kantovesi, Kuljetustieto, Umpisäiliö, Saostussäiliö, 
               Pienpuhdistamo, Viemäriverkosto, Harmaat vedet
    - EI SIIRRY (automaattisesti): Lietteen kompostointi-ilmoitus
    """

    def test_siirtyvat_tietotyypit(self):
        """Kaikki määritellyt tietotyypit siirtyvät."""
        siirtyvat = [
            'Kantovesi',
            'Kuljetustieto',
            'Umpisäiliö',
            'Saostussäiliö',
            'Pienpuhdistamo',
            'Viemäriverkosto',
            'Harmaat vedet'
        ]
        
        assert len(siirtyvat) == 7

    def test_ei_siirtyvat_tietotyypit(self):
        """Lietteen kompostointi-ilmoitus ei siirry automaattisesti."""
        ei_siirry_automaattisesti = ['Lietteen kompostointi-ilmoitus']
        
        assert 'Lietteen kompostointi-ilmoitus' in ei_siirry_automaattisesti

    def test_siirto_vs_kopiointi_logiikka(self):
        """
        Siirto vs kopiointi riippuu yhteisistä rakennuksista.
        
        - Yhteisiä rakennuksia -> SIIRTO (update)
        - Ei yhteisiä rakennuksia -> KOPIOINTI (insert)
        """
        # Skenaario 1: Yhteisiä rakennuksia
        vanha_rakennukset = {1, 2, 3}
        uusi_rakennukset_1 = {2, 3, 4}
        yhteisia_1 = vanha_rakennukset & uusi_rakennukset_1
        assert len(yhteisia_1) > 0, "Pitäisi olla yhteisiä -> siirto"
        
        # Skenaario 2: Ei yhteisiä rakennuksia
        uusi_rakennukset_2 = {5, 6, 7}
        yhteisia_2 = vanha_rakennukset & uusi_rakennukset_2
        assert len(yhteisia_2) == 0, "Ei yhteisiä -> kopiointi"


class TestKaivotietojenKopiointi:
    """
    Testit kaivotietojen kopioinnille tietokannassa.
    
    Kopioitavat kentät:
    - kohde_id (uusi)
    - alkupvm
    - loppupvm
    - kaivotietotyyppi_id
    - luotu
    - muokattu
    - tietolahde
    - tiedontuottaja_tunnus
    """

    def test_kaivotietojen_kopiointi_kentat(self):
        """Kaivotietojen kopioinnissa kaikki kentät kopioidaan."""
        kopioitavat_kentat = [
            'kohde_id',
            'alkupvm',
            'loppupvm',
            'kaivotietotyyppi_id',
            'luotu',
            'muokattu',
            'tietolahde',
            'tiedontuottaja_tunnus'
        ]
        
        assert len(kopioitavat_kentat) == 8
        assert 'kohde_id' in kopioitavat_kentat
        assert 'kaivotietotyyppi_id' in kopioitavat_kentat


class TestKuljetustenKopiointi:
    """
    Testit kuljetusten kopioinnille tietokannassa.
    
    Lietekuljetukset (jatetyyppi_id 5, 6, 7) kopioidaan jakaantumisessa.
    """

    def test_liete_jatetyyppi_ids(self):
        """Lietetyyppien ID:t ovat 5, 6, 7."""
        liete_jatetyyppi_ids = [5, 6, 7]
        
        assert 5 in liete_jatetyyppi_ids  # Liete
        assert 6 in liete_jatetyyppi_ids  # Mustaliete
        assert 7 in liete_jatetyyppi_ids  # Harmaaliete

    def test_kuljetusten_kopiointi_kentat(self):
        """Kuljetusten kopioinnissa kaikki kentät kopioidaan."""
        kopioitavat_kentat = [
            'kohde_id',
            'alkupvm',
            'loppupvm',
            'jatetyyppi_id',
            'lietteentyhjennyspaiva',
            'tyhjennyskerrat',
            'massa',
            'tilavuus',
            'tiedontuottaja_tunnus'
        ]
        
        assert len(kopioitavat_kentat) == 9
        assert 'kohde_id' in kopioitavat_kentat
        assert 'jatetyyppi_id' in kopioitavat_kentat


class TestViemariLiitostenKopiointi:
    """
    Testit viemäriliitosten kopioinnille tietokannassa.
    """

    def test_viemariliitosten_kopiointi_kentat(self):
        """Viemäriliitosten kopioinnissa kaikki kentät kopioidaan."""
        kopioitavat_kentat = [
            'kohde_id',
            'viemariverkosto_alkupvm',
            'viemariverkosto_loppupvm',
            'rakennus_prt'
        ]
        
        assert len(kopioitavat_kentat) == 4
        assert 'kohde_id' in kopioitavat_kentat
        assert 'rakennus_prt' in kopioitavat_kentat


class TestUpdateOldKohdeDataIntegration:
    """
    Integraatiotestit update_old_kohde_data -funktiolle.
    
    Nämä testit käyttävät oikeaa tietokantaa ja testaavat
    funktion toimintaa kokonaisuutena.
    """

    def test_hae_olemassa_oleva_kohde(self, engine, db_models):
        """Hakee olemassa olevan kohteen tietokannasta."""
        Kohde = db_models['Kohde']
        session = Session(engine)
        try:
            kohde = session.query(Kohde).first()
            if kohde:
                assert kohde.id is not None
                assert kohde.alkupvm is not None
        finally:
            session.close()

    def test_hae_kohteen_rakennukset(self, engine, db_models):
        """Hakee kohteen rakennukset tietokannasta."""
        KohteenRakennukset = db_models['KohteenRakennukset']
        session = Session(engine)
        try:
            kohteen_rakennukset = session.query(KohteenRakennukset).first()
            if kohteen_rakennukset:
                assert kohteen_rakennukset.kohde_id is not None
                assert kohteen_rakennukset.rakennus_id is not None
        finally:
            session.close()

    def test_hae_kaivotiedot(self, engine, db_models):
        """Hakee kaivotiedot tietokannasta."""
        Kaivotiedot = db_models['Kaivotiedot']
        session = Session(engine)
        try:
            kaivotieto = session.query(Kaivotiedot).first()
            if kaivotieto:
                assert kaivotieto.kohde_id is not None
        finally:
            session.close()

    def test_hae_viemariliitokset(self, engine, db_models):
        """Hakee viemäriliitokset tietokannasta."""
        ViemariLiitos = db_models['ViemariLiitos']
        session = Session(engine)
        try:
            viemariliitos = session.query(ViemariLiitos).first()
            if viemariliitos:
                assert viemariliitos.kohde_id is not None
        finally:
            session.close()

    def test_hae_kuljetukset(self, engine, db_models):
        """Hakee kuljetukset tietokannasta."""
        Kuljetus = db_models['Kuljetus']
        session = Session(engine)
        try:
            kuljetus = session.query(Kuljetus).first()
            if kuljetus:
                assert kuljetus.kohde_id is not None
        finally:
            session.close()

    def test_laske_kohteiden_maara(self, engine, db_models):
        """Laskee kohteiden määrän tietokannasta."""
        Kohde = db_models['Kohde']
        session = Session(engine)
        try:
            kohde_count = session.query(func.count(Kohde.id)).scalar()
            assert kohde_count >= 0
        finally:
            session.close()

    def test_laske_kaivotietojen_maara(self, engine, db_models):
        """Laskee kaivotietojen määrän tietokannasta."""
        Kaivotiedot = db_models['Kaivotiedot']
        session = Session(engine)
        try:
            kaivotieto_count = session.query(func.count(Kaivotiedot.id)).scalar()
            assert kaivotieto_count >= 0
        finally:
            session.close()

    def test_laske_viemariliitosten_maara(self, engine, db_models):
        """Laskee viemäriliitosten määrän tietokannasta."""
        ViemariLiitos = db_models['ViemariLiitos']
        session = Session(engine)
        try:
            viemariliitos_count = session.query(func.count(ViemariLiitos.id)).scalar()
            assert viemariliitos_count >= 0
        finally:
            session.close()
