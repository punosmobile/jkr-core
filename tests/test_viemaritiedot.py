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
from jkrimporter.providers.lahti.models import (
    ViemariIlmoitus,
    ViemariLopetusIlmoitus
)
from jkrimporter.providers.lahti.viemaritiedosto import (
    ViemariIlmoitustiedosto,
    ViemariLopetustiedosto,
)
from jkrimporter.providers.db.services.viemariliitos import (
    find_existing_viemariliitos,
    get_viemariliitokset_for_kohde,
    insert_viemariliitos,
    update_viemariliitos_loppupvm
)


class TestParseDate:
    """Testit päivämäärän parsinnalle."""

    def test_parse_date_from_date_object(self):
        """Päivämäärä date-objektista."""
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm(date(2024, 1, 15)) == date(2024, 1, 15)

    def test_parse_date_from_datetime(self):
        """Päivämäärä datetime-objektista."""
        from datetime import datetime
        assert ViemariLopetusIlmoitus.parse_viemariverkosto_loppupvm(datetime(2024, 1, 15, 10, 30)) == date(2024, 1, 15)

    def test_parse_date_finnish_format_with_time(self):
        """Päivämäärä suomalaisesta formaatista kellonajan kanssa."""
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm("1.1.2023 10.19.00") == date(2023, 1, 1)
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm("15.6.2024 14:30:00") == date(2024, 6, 15)

    def test_parse_date_iso_format(self):
        """Päivämäärä ISO-formaatista."""
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm("2024-01-15") == date(2024, 1, 15)

    def test_parse_date_none_values(self):
        """Tyhjät arvot palauttavat None."""
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm(None) is None
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm("") is None

    def test_parse_date_strips_whitespace(self):
        """Ylimääräiset välilyönnit poistetaan."""
        assert ViemariIlmoitus.parse_viemariverkosto_alkupvm("  15.1.2024  ") == date(2024, 1, 15)

class TestviemaritiedotRow:
    """Testit ViemariIlmoitus-dataluokalle."""

    def test_init_one_viemari_object(self):
        """Yksittäinen viemari."""
        row = ViemariIlmoitus(
            **{
                "Viemäriverkosto alkupvm": date(2024, 1, 10),
                "PRT": "103456789A",
            }
        )

        assert row.prt == "103456789A"
        assert row.viemariverkosto_alkupvm == date(2024, 1, 10)

class TestviemaritiedotLopetusRow:
    """Testit ViemariLopetusIlmoitus-dataluokalle."""

    def test_init_one_viemari_lopetus_object(self):
        """Yksittäisen viemarin poisto."""
        row = ViemariLopetusIlmoitus(
            **{
                "Viemäriverkosto loppupvm": date(2024, 6, 1),
                "PRT":"103456789A",
            }
        )

        assert row.prt == "103456789A"
        assert row.viemariverkosto_loppupvm == date(2024, 6, 1)


class TestKaivotiedosto:
    """Testit Viemäröinnin Excel-lukijalle."""

    def test_read_aloitus_file(self, datadir):
        """Lukee Viemaritietojen aloitustiedoston."""
        filepath = Path(datadir) / "viemari_aloitus.xlsx"
        tiedosto = ViemariIlmoitustiedosto(filepath)
        
        viemarit = tiedosto.viemariilmoitukset
        
        assert len(viemarit) == 4
        
        # Tarkista ensimmäinen rivi
        first = viemarit[0]
        assert first.prt == "103456789A"
        assert first.viemariverkosto_alkupvm == date(2024, 1, 10)

    def test_rawdata_preserved(self, datadir):
        """Alkuperäinen data säilytetään."""
        filepath = Path(datadir) / "viemari_aloitus.xlsx"
        tiedosto = ViemariIlmoitustiedosto(filepath)
        
        viemarit = tiedosto.viemariilmoitukset
        
        assert viemarit[0].rawdata is not None
        assert "PRT" in viemarit[0].rawdata

    def test_skip_rows_without_prt(self, datadir):
        """Ohittaa rivit joilta puuttuu PRT tai päivämäärä."""
        filepath = Path(datadir) / "viemari_virheellinen.xlsx"
        tiedosto = ViemariIlmoitustiedosto(filepath)
        
        viemarit = tiedosto.viemariilmoitukset
        
        # Molemmat rivit pitäisi ohittaa (puuttuva PRT tai päivämäärä)
        assert len(viemarit) == 0

    def test_file_with_wrong_headers(self, datadir):
        """Ohittaa tiedostot joilta on otsikkovirhe."""
        filepath = Path(datadir) / "viemari_otsikkovirhe.xlsx"

        viemarit = []

        try:
            tiedosto = ViemariIlmoitustiedosto(filepath)
        
            viemarit = tiedosto.viemariilmoitukset
        except RuntimeError:
            print("Otsikkovirhe havaittu, tiedosto ohitettu.")
        # Molemmat rivit pitäisi ohittaa (tiedosto ei kelpaa)
        assert len(viemarit) == 0


class TestViemarinLopetusTiedosto:
    """Testit ViemärinLopetusTiedosto Excel-lukijalle."""

    def test_read_lopetus_file(self, datadir):
        """Lukee viemärien lopetustiedoston."""
        filepath = Path(datadir) / "viemari_lopetus.xlsx"
        tiedosto = ViemariLopetustiedosto(filepath)
        
        lopetukset = tiedosto.lopetusilmoitukset
        
        assert len(lopetukset) == 2
        
        # Tarkista ensimmäinen rivi
        first = lopetukset[0]
        assert first.prt == "103456789A"
        assert first.viemariverkosto_loppupvm == date(2025, 1, 10)  # Loppupvm

    def test_rawdata_preserved(self, datadir):
            """Alkuperäinen data säilytetään."""
            filepath = Path(datadir) / "viemari_lopetus.xlsx"
            tiedosto = ViemariLopetustiedosto(filepath)
            
            viemarit = list(tiedosto.lopetusilmoitukset)
            
            assert viemarit[0].rawdata is not None
            assert "PRT" in viemarit[0].rawdata