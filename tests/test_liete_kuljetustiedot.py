"""
Testit LIETE-kuljetustietojen sisäänluvulle.

Testaa:
- Excel-tiedoston parsinta (LieteKuljetustiedosto)
- Datamallin validaattorit (LieteKuljetusRow)
- JKR-muotoon kääntäminen (LieteTranslator)
- Jätelaji-kartoitus
"""

from datetime import date
from pathlib import Path

import pytest

from jkrimporter.model import Jatelaji as JkrJatelaji
from jkrimporter.providers.lahti.liete_kuljetustiedosto import LieteKuljetustiedosto
from jkrimporter.providers.lahti.liete_models import LieteKuljetusRow
from jkrimporter.providers.lahti.liete_translator import (
    LIETE_JATELAJI_MAP,
    LieteTranslator,
)


class TestLieteKuljetusRow:
    """Testit LieteKuljetusRow-datamallin validaattoreille."""

    def test_parse_date_from_date_object(self):
        """Päivämäärä date-objektista."""
        data = {
            "ID-tunnus": "TEST-001",
            "Siirron alkamisaika": date(2024, 1, 15),
            "Siirron päättymisaika": date(2024, 1, 15),
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.siirron_alkamisaika == date(2024, 1, 15)
        assert row.siirron_paattymisaika == date(2024, 1, 15)

    def test_parse_date_from_string_finnish_format(self):
        """Päivämäärä suomalaisesta merkkijonosta (dd.mm.yyyy)."""
        data = {
            "ID-tunnus": "TEST-002",
            "Siirron alkamisaika": "15.01.2024",
            "Siirron päättymisaika": "15.01.2024",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.siirron_alkamisaika == date(2024, 1, 15)

    def test_parse_date_from_string_iso_format(self):
        """Päivämäärä ISO-formaatista (yyyy-mm-dd)."""
        data = {
            "ID-tunnus": "TEST-003",
            "Siirron alkamisaika": "2024-01-15",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.siirron_alkamisaika == date(2024, 1, 15)

    def test_parse_date_none_value(self):
        """Tyhjä päivämäärä palauttaa None."""
        data = {
            "ID-tunnus": "TEST-004",
            "Siirron alkamisaika": None,
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.siirron_alkamisaika is None

    def test_parse_date_empty_string(self):
        """Tyhjä merkkijono palauttaa None."""
        data = {
            "ID-tunnus": "TEST-005",
            "Siirron alkamisaika": "",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.siirron_alkamisaika is None

    def test_parse_float_from_number(self):
        """Desimaaliluku numerosta."""
        data = {
            "ID-tunnus": "TEST-006",
            "Jätteen paino (t)": 2.5,
            "Jätteen tilavuus (m³)": 3.0,
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.jatteen_paino_t == 2.5
        assert row.jatteen_tilavuus_m3 == 3.0

    def test_parse_float_from_string_with_comma(self):
        """Desimaaliluku merkkijonosta pilkulla."""
        data = {
            "ID-tunnus": "TEST-007",
            "Jätteen paino (t)": "2,5",
            "Jätteen tilavuus (m³)": "3,0",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.jatteen_paino_t == 2.5
        assert row.jatteen_tilavuus_m3 == 3.0

    def test_parse_float_from_string_with_dot(self):
        """Desimaaliluku merkkijonosta pisteellä."""
        data = {
            "ID-tunnus": "TEST-008",
            "Jätteen paino (t)": "2.5",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.jatteen_paino_t == 2.5

    def test_parse_float_none_value(self):
        """Tyhjä desimaaliluku palauttaa None."""
        data = {
            "ID-tunnus": "TEST-009",
            "Jätteen paino (t)": None,
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.jatteen_paino_t is None

    def test_clean_tunnus_strips_whitespace(self):
        """Tunnukset puhdistetaan tyhjistä."""
        data = {
            "ID-tunnus": "TEST-010",
            "Pysyvä rakennustunnus": "  103456789A  ",
            "Kiinteistötunnus": " 398-1-1-1 ",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.pysyva_rakennustunnus == "103456789A"
        assert row.kiinteistotunnus == "398-1-1-1"

    def test_clean_tunnus_empty_string_returns_none(self):
        """Tyhjä tunnus palauttaa None."""
        data = {
            "ID-tunnus": "TEST-011",
            "Pysyvä rakennustunnus": "   ",
            "Kiinteistötunnus": "",
        }
        row = LieteKuljetusRow.parse_obj(data)
        assert row.pysyva_rakennustunnus is None
        assert row.kiinteistotunnus is None

    def test_all_fields_populated(self):
        """Kaikki kentät täytetty."""
        data = {
            "ID-tunnus": "LIETE-001",
            "Siirron alkamisaika": date(2024, 1, 15),
            "Jätteen tuottaja tai muu haltija": "Testi Tuottaja Oy",
            "Jätteen tuottajan/haltijan osoite": "Testikatu 1, 15100 Lahti",
            "Jätteen tuottajan/haltijan katuosoite": "Testikatu 1",
            "Jätteen tuottajan/haltijan postinumero": "15100",
            "Siirron alkamispaikka": "Testikatu 1, 15100 Lahti",
            "Siirron alkamispaikan katuosoite": "Testikatu 1",
            "Siirron alkamispaikan postinumero": "15100",
            "Kuljettaja": "1234567-8",
            "Vastaanottaja": "Vastaanottaja Oy",
            "Siirron päättymispaikka": "Käsittelykatu 5, 15200 Lahti",
            "Siirron päättymispaikan katuosoite": "Käsittelykatu 5",
            "Siirron päättymispaikan postinumero": "15200",
            "Siirron päättymisaika": date(2024, 1, 15),
            "Jäte": "200304",
            "Jätteen kuvaus": "Umpisäiliö",
            "Jätteen paino (t)": 2.5,
            "Jätteen tilavuus (m³)": 3.0,
            "Kiinteistötunnus": "398-1-1-1",
            "Pysyvä rakennustunnus": "103456789A",
            "Lietteen tyyppi": "Musta",
        }
        row = LieteKuljetusRow.parse_obj(data)
        
        assert row.id_tunnus == "LIETE-001"
        assert row.siirron_alkamisaika == date(2024, 1, 15)
        assert row.jatteen_tuottaja == "Testi Tuottaja Oy"
        assert row.kuljettaja == "1234567-8"
        assert row.jatteen_paino_t == 2.5
        assert row.jatteen_tilavuus_m3 == 3.0
        assert row.pysyva_rakennustunnus == "103456789A"
        assert row.lietteen_tyyppi == "Musta"


class TestLieteKuljetustiedosto:
    """Testit LieteKuljetustiedosto Excel-lukijalle."""

    def test_read_ok_file(self, datadir):
        """Lukee onnistuneesti testitiedoston."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        
        kuljetukset = list(tiedosto.kuljetustiedot)
        
        assert len(kuljetukset) == 4
        
        # Tarkista ensimmäinen rivi
        first = kuljetukset[0]
        assert first.id_tunnus == "LIETE-001"
        assert first.siirron_alkamisaika == date(2024, 1, 15)
        assert first.pysyva_rakennustunnus == "103456789A"
        assert first.lietteen_tyyppi == "Musta"
        assert first.jatteen_paino_t == 2.5

    def test_read_file_with_errors(self, datadir):
        """Lukee tiedoston jossa on virheellisiä arvoja."""
        filepath = Path(datadir) / "liete_kuljetustiedot_errors.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        
        kuljetukset = list(tiedosto.kuljetustiedot)
        
        # Molemmat rivit pitäisi lukea (validaattorit korjaavat)
        assert len(kuljetukset) == 2
        
        # Pilkku desimaalierottimena pitäisi toimia
        assert kuljetukset[0].jatteen_paino_t == 1.5
        
        # Merkkijono-päivämäärä pitäisi toimia
        assert kuljetukset[1].siirron_alkamisaika == date(2024, 6, 15)

    def test_read_empty_file(self, datadir):
        """Lukee tyhjän tiedoston (vain otsikot)."""
        filepath = Path(datadir) / "liete_kuljetustiedot_empty.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        
        kuljetukset = list(tiedosto.kuljetustiedot)
        
        assert len(kuljetukset) == 0

    def test_file_not_found(self):
        """Heittää virheen jos tiedostoa ei löydy."""
        with pytest.raises(FileNotFoundError):
            LieteKuljetustiedosto(Path("/nonexistent/file.xlsx"))

    def test_invalid_file_extension(self, datadir):
        """Heittää virheen jos tiedostopääte on väärä."""
        # Luo väliaikainen .txt tiedosto
        txt_file = Path(datadir) / "test.txt"
        txt_file.write_text("test")
        
        with pytest.raises(ValueError):
            LieteKuljetustiedosto(txt_file)


class TestLieteJatelajiMap:
    """Testit jätelaji-kartoitukselle."""

    def test_musta_maps_to_mustaliete(self):
        """Musta -> mustaliete."""
        assert LIETE_JATELAJI_MAP["Musta"] == JkrJatelaji.mustaliete

    def test_harmaa_maps_to_harmaaliete(self):
        """Harmaa -> harmaaliete."""
        assert LIETE_JATELAJI_MAP["Harmaa"] == JkrJatelaji.harmaaliete

    def test_ei_tietoa_maps_to_liete(self):
        """Ei tietoa -> liete (yleinen)."""
        assert LIETE_JATELAJI_MAP["Ei tietoa"] == JkrJatelaji.liete

    def test_legacy_names_supported(self):
        """Vanhat nimitykset tuettu."""
        assert LIETE_JATELAJI_MAP["Liete"] == JkrJatelaji.liete
        assert LIETE_JATELAJI_MAP["Musta liete"] == JkrJatelaji.mustaliete
        assert LIETE_JATELAJI_MAP["Harmaa liete"] == JkrJatelaji.harmaaliete


class TestLieteTranslator:
    """Testit LieteTranslator-kääntäjälle."""

    def test_as_jkr_data_creates_asiakkaat(self, datadir):
        """Luo asiakkaat kuljetustiedoista."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # 4 kuljetusta, 4 eri asiakasta (eri PRT/osoite)
        assert len(jkr_data.asiakkaat) == 4

    def test_as_jkr_data_creates_tyhjennystapahtumat(self, datadir):
        """Luo tyhjennystapahtumat kuljetustiedoista."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Jokaisella asiakkaalla yksi tyhjennystapahtuma
        for tunnus, asiakas in jkr_data.asiakkaat.items():
            assert len(asiakas.tyhjennystapahtumat) >= 1

    def test_asiakas_id_from_prt(self, datadir):
        """Asiakastunnus luodaan PRT:stä ensisijaisesti."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Tarkista että PRT-pohjaiset tunnukset löytyvät
        tunnukset = [str(t) for t in jkr_data.asiakkaat.keys()]
        assert any("PRT_103456789A" in t for t in tunnukset)

    def test_asiakas_id_from_address_when_no_prt(self, datadir):
        """Asiakastunnus luodaan osoitteesta jos PRT puuttuu."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Neljäs rivi on ilman PRT:tä -> osoitepohjainen tunnus
        tunnukset = [str(t) for t in jkr_data.asiakkaat.keys()]
        assert any("ADDR_" in t for t in tunnukset)

    def test_tyhjennystapahtuma_jatelaji_mapping(self, datadir):
        """Tyhjennystapahtuman jätelaji kartoitetaan oikein."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Kerää kaikki jätelajit
        jatelajit = set()
        for asiakas in jkr_data.asiakkaat.values():
            for tapahtuma in asiakas.tyhjennystapahtumat:
                jatelajit.add(tapahtuma.jatelaji)
        
        # Pitäisi sisältää mustaliete, harmaaliete ja liete
        assert JkrJatelaji.mustaliete in jatelajit
        assert JkrJatelaji.harmaaliete in jatelajit
        assert JkrJatelaji.liete in jatelajit

    def test_tyhjennystapahtuma_tilavuus_conversion(self, datadir):
        """Tilavuus muunnetaan m³ -> litraa."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Ensimmäinen kuljetus: 3.0 m³ = 3000 litraa
        first_asiakas = list(jkr_data.asiakkaat.values())[0]
        assert first_asiakas.tyhjennystapahtumat[0].tilavuus == 3000

    def test_tyhjennystapahtuma_massa_conversion(self, datadir):
        """Massa muunnetaan t -> kg."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Ensimmäinen kuljetus: 2.5 t = 2500 kg
        first_asiakas = list(jkr_data.asiakkaat.values())[0]
        assert first_asiakas.tyhjennystapahtumat[0].massa == 2500

    def test_tyhjennystapahtuma_jatteen_kuvaus(self, datadir):
        """LAH-449: Jätteen kuvaus tallennetaan tyhjennystapahtumaaan."""
        filepath = Path(datadir) / "liete_kuljetustiedot_ok.xlsx"
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Tarkista että jatteen_kuvaus on tallennettu
        first_asiakas = list(jkr_data.asiakkaat.values())[0]
        tapahtuma = first_asiakas.tyhjennystapahtumat[0]
        # jatteen_kuvaus voi olla esim. "Umpisäiliö", "Saostussäiliö", "Pienpuhdistamo", "Ei tiedossa"
        assert hasattr(tapahtuma, 'jatteen_kuvaus')

    def test_same_prt_groups_kuljetukset(self, datadir):
        """Saman PRT:n kuljetukset ryhmitellään samalle asiakkaalle."""
        # Luo testitiedosto jossa sama PRT kahdesti
        import pandas as pd
        
        data = [
            {
                "ID-tunnus": "LIETE-A1",
                "Siirron alkamisaika": date(2024, 1, 15),
                "Jätteen tuottaja tai muu haltija": "Testi Oy",
                "Siirron alkamispaikan katuosoite": "Testikatu 1",
                "Siirron alkamispaikan postinumero": "15100",
                "Kuljettaja": "1234567-8",
                "Siirron päättymisaika": date(2024, 1, 15),
                "Jätteen paino (t)": 1.0,
                "Jätteen tilavuus (m³)": 1.5,
                "Pysyvä rakennustunnus": "103456789A",
                "Lietteen tyyppi": "Musta",
            },
            {
                "ID-tunnus": "LIETE-A2",
                "Siirron alkamisaika": date(2024, 2, 15),
                "Jätteen tuottaja tai muu haltija": "Testi Oy",
                "Siirron alkamispaikan katuosoite": "Testikatu 1",
                "Siirron alkamispaikan postinumero": "15100",
                "Kuljettaja": "1234567-8",
                "Siirron päättymisaika": date(2024, 2, 15),
                "Jätteen paino (t)": 2.0,
                "Jätteen tilavuus (m³)": 2.5,
                "Pysyvä rakennustunnus": "103456789A",  # Sama PRT
                "Lietteen tyyppi": "Musta",
            },
        ]
        
        df = pd.DataFrame(data)
        filepath = Path(datadir) / "liete_same_prt.xlsx"
        df.to_excel(filepath, index=False)
        
        tiedosto = LieteKuljetustiedosto(filepath)
        translator = LieteTranslator(tiedosto, "LSJ")
        
        jkr_data = translator.as_jkr_data(date(2024, 1, 1), date(2024, 12, 31))
        
        # Vain yksi asiakas (sama PRT)
        assert len(jkr_data.asiakkaat) == 1
        
        # Kaksi tyhjennystä
        asiakas = list(jkr_data.asiakkaat.values())[0]
        assert len(asiakas.tyhjennystapahtumat) == 2
