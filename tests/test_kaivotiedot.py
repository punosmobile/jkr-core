"""
Testit kaivotietojen sisäänluvulle.

Testaa:
- Excel-tiedoston parsinta (Kaivotiedosto, KaivotiedonLopetusTiedosto)
- Datamallit (KaivotiedotRow, KaivotiedonLopetusRow)
- Boolean-parsinta
- Kaivotietotyyppien tunnistus
- Tietokantapalvelut (insert, update, find)
"""

from datetime import date
from pathlib import Path

import pytest
from jkrimporter.providers.lahti.kaivo_models import (
    KaivotiedotRow,
    KaivotiedonLopetusRow,
    KaivotietoTyyppi,
    EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI,
)
from jkrimporter.providers.lahti.kaivotiedosto import (
    Kaivotiedosto,
    KaivotiedonLopetusTiedosto,
    _parse_bool,
    _parse_date,
    _parse_str,
)
from jkrimporter.providers.db.services.kaivotieto import (
    KAIVOTIETOTYYPPI_ID_MAP,
    get_kaivotietotyyppi_id,
)


class TestParseBool:
    """Testit boolean-parsinnalle."""

    def test_parse_bool_true_values(self):
        """Eri true-arvot tunnistetaan."""
        assert _parse_bool(True) is True
        assert _parse_bool(1) is True
        assert _parse_bool(1.0) is True
        assert _parse_bool("1") is True
        assert _parse_bool("x") is True
        assert _parse_bool("X") is True
        assert _parse_bool("kyllä") is True
        assert _parse_bool("Kyllä") is True
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("on") is True

    def test_parse_bool_false_values(self):
        """Eri false-arvot tunnistetaan."""
        assert _parse_bool(False) is False
        assert _parse_bool(0) is False
        assert _parse_bool(0.0) is False
        assert _parse_bool(None) is False
        assert _parse_bool("") is False

    def test_parse_bool_column_name_match(self):
        """Sarakkeen nimi arvona tulkitaan true."""
        assert _parse_bool("Pienpuhdistamo", "Pienpuhdistamo") is True
        assert _parse_bool("pienpuhdistamo", "Pienpuhdistamo") is True
        assert _parse_bool("Saostussäiliö", "Saostussäiliö") is True

    def test_parse_bool_any_text_is_true(self):
        """Mikä tahansa ei-tyhjä teksti tulkitaan true."""
        assert _parse_bool("jotain tekstiä") is True
        assert _parse_bool("abc") is True


class TestParseDate:
    """Testit päivämäärän parsinnalle."""

    def test_parse_date_from_date_object(self):
        """Päivämäärä date-objektista."""
        assert _parse_date(date(2024, 1, 15)) == date(2024, 1, 15)

    def test_parse_date_from_datetime(self):
        """Päivämäärä datetime-objektista."""
        from datetime import datetime
        assert _parse_date(datetime(2024, 1, 15, 10, 30)) == date(2024, 1, 15)

    def test_parse_date_finnish_format(self):
        """Päivämäärä suomalaisesta formaatista."""
        assert _parse_date("15.1.2024") == date(2024, 1, 15)
        assert _parse_date("1.1.2024") == date(2024, 1, 1)

    def test_parse_date_finnish_format_with_time(self):
        """Päivämäärä suomalaisesta formaatista kellonajan kanssa."""
        assert _parse_date("1.1.2023 10.19.00") == date(2023, 1, 1)
        assert _parse_date("15.6.2024 14:30:00") == date(2024, 6, 15)

    def test_parse_date_iso_format(self):
        """Päivämäärä ISO-formaatista."""
        assert _parse_date("2024-01-15") == date(2024, 1, 15)

    def test_parse_date_none_values(self):
        """Tyhjät arvot palauttavat None."""
        assert _parse_date(None) is None
        assert _parse_date("") is None

    def test_parse_date_strips_whitespace(self):
        """Ylimääräiset välilyönnit poistetaan."""
        assert _parse_date("  15.1.2024  ") == date(2024, 1, 15)


class TestParseStr:
    """Testit merkkijonon parsinnalle."""

    def test_parse_str_normal(self):
        """Normaali merkkijono."""
        assert _parse_str("testi") == "testi"

    def test_parse_str_strips_whitespace(self):
        """Välilyönnit poistetaan."""
        assert _parse_str("  testi  ") == "testi"

    def test_parse_str_none_values(self):
        """Tyhjät arvot palauttavat None."""
        assert _parse_str(None) is None
        assert _parse_str("") is None
        assert _parse_str("   ") is None


class TestKaivotiedotRow:
    """Testit KaivotiedotRow-dataluokalle."""

    def test_get_kaivotietotyypit_single(self):
        """Yksittäinen kaivotietotyyppi."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            saostussailio=True,
        )
        tyypit = row.get_kaivotietotyypit()
        
        assert len(tyypit) == 1
        assert KaivotietoTyyppi.SAOSTUSSAILIO in tyypit

    def test_get_kaivotietotyypit_multiple(self):
        """Useita kaivotietotyyppejä."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            kantovesi=True,
            umpisailio=True,
        )
        tyypit = row.get_kaivotietotyypit()
        
        assert len(tyypit) == 2
        assert KaivotietoTyyppi.KANTOVESI in tyypit
        assert KaivotietoTyyppi.UMPISAILIO in tyypit

    def test_get_kaivotietotyypit_all(self):
        """Kaikki kaivotietotyypit."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            kantovesi=True,
            saostussailio=True,
            pienpuhdistamo=True,
            umpisailio=True,
            vain_harmaat_vedet=True,
        )
        tyypit = row.get_kaivotietotyypit()
        
        assert len(tyypit) == 5

    def test_get_kaivotietotyypit_none(self):
        """Ei yhtään kaivotietotyyppiä."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
        )
        tyypit = row.get_kaivotietotyypit()
        
        assert len(tyypit) == 0

    def test_get_osapuoli_nimi_full(self):
        """Osapuolen nimi etunimi + sukunimi."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            etunimi="Matti",
            sukunimi="Meikäläinen",
        )
        assert row.get_osapuoli_nimi() == "Matti Meikäläinen"

    def test_get_osapuoli_nimi_only_sukunimi(self):
        """Osapuolen nimi vain sukunimi."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            sukunimi="Meikäläinen",
        )
        assert row.get_osapuoli_nimi() == "Meikäläinen"

    def test_get_osapuoli_nimi_only_etunimi(self):
        """Osapuolen nimi vain etunimi."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
            etunimi="Matti",
        )
        assert row.get_osapuoli_nimi() == "Matti"

    def test_get_osapuoli_nimi_none(self):
        """Osapuolen nimi puuttuu."""
        row = KaivotiedotRow(
            vastausaika=date(2024, 1, 10),
            prt="103456789A",
        )
        assert row.get_osapuoli_nimi() is None


class TestKaivotiedonLopetusRow:
    """Testit KaivotiedonLopetusRow-dataluokalle."""

    def test_get_kaivotietotyypit(self):
        """Lopetusrivin kaivotietotyypit."""
        row = KaivotiedonLopetusRow(
            vastausaika=date(2024, 6, 1),
            prt="103456789A",
            saostussailio=True,
        )
        tyypit = row.get_kaivotietotyypit()
        
        assert len(tyypit) == 1
        assert KaivotietoTyyppi.SAOSTUSSAILIO in tyypit


class TestKaivotiedosto:
    """Testit Kaivotiedosto Excel-lukijalle."""

    def test_read_aloitus_file(self, datadir):
        """Lukee kaivotietojen aloitustiedoston."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        assert len(kaivotiedot) == 4
        
        # Tarkista ensimmäinen rivi
        first = kaivotiedot[0]
        assert first.prt == "103456789A"
        assert first.vastausaika == date(2024, 1, 10)
        assert first.saostussailio is True
        assert first.pienpuhdistamo is False

    def test_boolean_parsing_x(self, datadir):
        """Boolean-parsinta 'x'-arvolla."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Ensimmäinen rivi: Saostussäiliö = "x"
        assert kaivotiedot[0].saostussailio is True

    def test_boolean_parsing_type_name(self, datadir):
        """Boolean-parsinta tyypin nimellä."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Toinen rivi: Pienpuhdistamo = "Pienpuhdistamo"
        assert kaivotiedot[1].pienpuhdistamo is True

    def test_boolean_parsing_number(self, datadir):
        """Boolean-parsinta numerolla."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Kolmas rivi: Kantovesi = "1"
        assert kaivotiedot[2].kantovesi is True

    def test_multiple_types_per_row(self, datadir):
        """Useita kaivotietotyyppejä samalla rivillä."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Neljäs rivi: Saostussäiliö ja Vain harmaat vedet
        fourth = kaivotiedot[3]
        tyypit = fourth.get_kaivotietotyypit()
        
        assert len(tyypit) == 2
        assert KaivotietoTyyppi.SAOSTUSSAILIO in tyypit
        assert KaivotietoTyyppi.VAIN_HARMAAT_VEDET in tyypit

    def test_rawdata_preserved(self, datadir):
        """Alkuperäinen data säilytetään."""
        filepath = Path(datadir) / "kaivotiedot_aloitus.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        assert kaivotiedot[0].rawdata is not None
        assert "PRT" in kaivotiedot[0].rawdata

    def test_skip_rows_without_prt(self, datadir):
        """Ohittaa rivit joilta puuttuu PRT."""
        filepath = Path(datadir) / "kaivotiedot_virheellinen.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Molemmat rivit pitäisi ohittaa (puuttuva PRT tai päivämäärä)
        assert len(kaivotiedot) == 0

    def test_skip_rows_without_date(self, datadir):
        """Ohittaa rivit joilta puuttuu päivämäärä."""
        filepath = Path(datadir) / "kaivotiedot_virheellinen.xlsx"
        tiedosto = Kaivotiedosto(filepath)
        
        kaivotiedot = list(tiedosto.kaivotiedot)
        
        # Toinen rivi: puuttuva päivämäärä
        assert len(kaivotiedot) == 0


class TestKaivotiedonLopetusTiedosto:
    """Testit KaivotiedonLopetusTiedosto Excel-lukijalle."""

    def test_read_lopetus_file(self, datadir):
        """Lukee kaivotiedon lopetustiedoston."""
        filepath = Path(datadir) / "kaivotiedot_lopetus.xlsx"
        tiedosto = KaivotiedonLopetusTiedosto(filepath)
        
        lopetukset = list(tiedosto.lopetukset)
        
        assert len(lopetukset) == 2
        
        # Tarkista ensimmäinen rivi
        first = lopetukset[0]
        assert first.prt == "103456789A"
        assert first.vastausaika == date(2024, 6, 1)  # Loppupvm
        assert first.saostussailio is True


class TestKaivotietotyyppiIdMap:
    """Testit kaivotietotyyppien ID-kartoitukselle."""

    def test_all_types_have_id(self):
        """Kaikilla tyypeillä on ID."""
        for tyyppi in KaivotietoTyyppi:
            assert tyyppi in KAIVOTIETOTYYPPI_ID_MAP
            assert isinstance(KAIVOTIETOTYYPPI_ID_MAP[tyyppi], int)

    def test_get_kaivotietotyyppi_id(self):
        """get_kaivotietotyyppi_id palauttaa oikean ID:n."""
        assert get_kaivotietotyyppi_id(KaivotietoTyyppi.KANTOVESI) == 1
        assert get_kaivotietotyyppi_id(KaivotietoTyyppi.SAOSTUSSAILIO) == 2
        assert get_kaivotietotyyppi_id(KaivotietoTyyppi.PIENPUHDISTAMO) == 3
        assert get_kaivotietotyyppi_id(KaivotietoTyyppi.UMPISAILIO) == 4
        assert get_kaivotietotyyppi_id(KaivotietoTyyppi.VAIN_HARMAAT_VEDET) == 5


class TestExcelSarakeToKaivotietotyyppi:
    """Testit Excel-sarakkeiden kartoitukselle."""

    def test_all_column_names_mapped(self):
        """Kaikki sarakkeiden nimet kartoitettu."""
        expected_columns = [
            "Kantovesi",
            "Saostussäiliö",
            "Pienpuhdistamo",
            "Umpisäiliö",
            "Vain harmaat vedet",
        ]
        for col in expected_columns:
            assert col in EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI

    def test_column_to_type_mapping(self):
        """Sarakkeet kartoitetaan oikeisiin tyyppeihin."""
        assert EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI["Kantovesi"] == KaivotietoTyyppi.KANTOVESI
        assert EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI["Saostussäiliö"] == KaivotietoTyyppi.SAOSTUSSAILIO
        assert EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI["Pienpuhdistamo"] == KaivotietoTyyppi.PIENPUHDISTAMO
        assert EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI["Umpisäiliö"] == KaivotietoTyyppi.UMPISAILIO
        assert EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI["Vain harmaat vedet"] == KaivotietoTyyppi.VAIN_HARMAAT_VEDET
