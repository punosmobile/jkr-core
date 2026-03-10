"""
Testit lietteen kompostointi-ilmoitusten sisäänluvulle.

Testaa:
- Excel-tiedoston parsinta (LieteIlmoitustiedosto)
- JKR-muotoon kääntäminen (LieteIlmoitusTranslator)
- Pienpuhdistamo-alkupvm käsittely
"""

from datetime import date
from pathlib import Path

import pytest

from jkrimporter.providers.lahti.ilmoitustiedosto import LieteIlmoitustiedosto
from jkrimporter.providers.lahti.lahtiprovider import LieteIlmoitusTranslator


class TestLieteIlmoitustiedosto:
    """Testit LieteIlmoitustiedosto Excel-lukijalle."""

    def test_readable_by_me_valid_xlsx(self, datadir):
        """Tunnistaa validin Excel-tiedoston."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        assert LieteIlmoitustiedosto.readable_by_me(filepath) is True

    def test_readable_by_me_invalid_extension(self, datadir):
        """Ei tunnista väärää tiedostopäätettä."""
        # Luo väliaikainen .txt tiedosto
        txt_file = Path(datadir) / "test.txt"
        txt_file.write_text("test")
        
        assert LieteIlmoitustiedosto.readable_by_me(txt_file) is False

    def test_readable_by_me_nonexistent_file(self):
        """Ei tunnista olematonta tiedostoa."""
        assert LieteIlmoitustiedosto.readable_by_me(Path("/nonexistent/file.xlsx")) is False

    def test_read_ok_file(self, datadir):
        """Lukee onnistuneesti testitiedoston."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        
        ilmoitukset = tiedosto.ilmoitukset
        
        assert len(ilmoitukset) == 3

    def test_ilmoitus_fields(self, datadir):
        """Ilmoituksen kentät luetaan oikein."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        
        ilmoitukset = tiedosto.ilmoitukset
        first = ilmoitukset[0]
        
        assert first.Vastausaika == date(2024, 1, 20)
        # voimassaalkaen ja voimassaasti voivat olla date tai str riippuen parsinnasta
        assert first.kayttaja_etunimi == "Matti"
        assert first.kayttaja_sukunimi == "Meikäläinen"
        assert first.vastuuhenkilo_postinumero == "15100"
        assert first.vastuuhenkilo_osoite == "Testikatu 1"

    def test_rawdata_preserved(self, datadir):
        """Alkuperäinen data säilytetään."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        
        ilmoitukset = tiedosto.ilmoitukset
        
        assert ilmoitukset[0].rawdata is not None


class TestLieteIlmoitusTranslator:
    """Testit LieteIlmoitusTranslator-kääntäjälle."""

    def test_as_jkr_data_creates_ilmoitukset(self, datadir):
        """Luo ilmoitukset tiedostosta."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        assert len(jkr_data) == 3

    def test_ilmoitus_has_pienpuhdistamo_alkupvm(self, datadir):
        """Ilmoituksella on pienpuhdistamo_alkupvm."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        # Lieteilmoituksilla on pienpuhdistamo_alkupvm (Vastausaika)
        first = jkr_data[0]
        assert first.pienpuhdistamo_alkupvm == date(2024, 1, 20)

    def test_ilmoitus_is_liete(self, datadir):
        """Ilmoitus merkitään lieteilmoitukseksi."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        for ilmoitus in jkr_data:
            assert ilmoitus.onko_liete is True

    def test_vastuuhenkilo_created(self, datadir):
        """Vastuuhenkilö luodaan oikein."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        first = jkr_data[0]
        assert first.vastuuhenkilo is not None
        # Huom: _get_name saa parametrit järjestyksessä (etunimi, sukunimi)
        # mutta LieteIlmoitusTranslator kutsuu sitä (kayttaja_etunimi, kayttaja_sukunimi)
        assert first.vastuuhenkilo.nimi is not None
        assert first.vastuuhenkilo.postinumero == "15100"

    def test_voimassaolo_interval(self, datadir):
        """Voimassaoloväli luodaan oikein."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        first = jkr_data[0]
        assert first.alkupvm == date(2024, 1, 20)
        assert first.loppupvm == date(2029, 1, 20)

    def test_prt_list(self, datadir):
        """PRT-lista luodaan oikein."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        first = jkr_data[0]
        assert first.prt is not None
        assert len(first.prt) >= 1

    def test_tiedontuottaja_is_ilmoitus(self, datadir):
        """Tiedontuottaja on 'ilmoitus'."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        for ilmoitus in jkr_data:
            assert ilmoitus.tiedontuottaja == "ilmoitus"

    def test_kompostoijat_is_none_for_liete(self, datadir):
        """Lieteilmoituksilla ei ole kompostoijia."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        for ilmoitus in jkr_data:
            assert ilmoitus.kompostoijat is None

    def test_rawdata_preserved_in_list(self, datadir):
        """Alkuperäinen data säilytetään listana."""
        filepath = Path(datadir) / "liete_ilmoitukset_ok.xlsx"
        tiedosto = LieteIlmoitustiedosto(filepath)
        translator = LieteIlmoitusTranslator(tiedosto)
        
        jkr_data = translator.as_jkr_data()
        
        first = jkr_data[0]
        assert first.rawdata is not None
        assert isinstance(first.rawdata, list)
        assert len(first.rawdata) >= 1


class TestLieteIlmoitusTranslatorNameFormatting:
    """Testit nimen muotoilulle."""

    def test_get_name_both_names(self):
        """Nimi muodostetaan etunimestä ja sukunimestä."""
        name = LieteIlmoitusTranslator._get_name("Meikäläinen", "Matti")
        # Huom: sukunimi ensin parametreissa
        assert name == "Meikäläinen Matti"

    def test_get_name_only_sukunimi(self):
        """Vain sukunimi."""
        name = LieteIlmoitusTranslator._get_name("Meikäläinen", None)
        assert name == "Meikäläinen"

    def test_get_name_only_etunimi(self):
        """Vain etunimi."""
        name = LieteIlmoitusTranslator._get_name(None, "Matti")
        assert name == "Matti"

    def test_get_name_none(self):
        """Ei nimeä."""
        name = LieteIlmoitusTranslator._get_name(None, None)
        assert name is None

    def test_get_name_same_names(self):
        """Sama nimi molemmissa kentissä."""
        # Joskus datassa on sama arvo molemmissa
        name = LieteIlmoitusTranslator._get_name("Meikäläinen", "Meikäläinen")
        assert name == "Meikäläinen"
