"""
Kaivotiedot Excel-tiedoston lukija.

LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.

Tiedostorakenne (sarakkeet):
- Vastausaika
- PRT
- Etunimi
- Sukunimi
- Katuosoite
- Postinumero
- Postitoimipaikka
- Kantovesi
- Saostussäiliö
- Pienpuhdistamo
- Umpisäiliö
- Vain harmaat vedet
- Tietolähde
"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional, Union

import pandas as pd

from jkrimporter.datasheets import get_kaivotiedosto_headers
from jkrimporter.providers.lahti.kaivo_models import (
    KaivotiedotRow,
    KaivotiedonLopetusRow,
)

logger = logging.getLogger(__name__)


def _parse_date(value) -> Optional[date]:
    """Parsii päivämäärän eri muodoista."""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Siivoa ylimääräiset välilyönnit
        value_clean = " ".join(value.strip().split())
        
        # Kokeile eri formaatteja (päivämäärä + kellonaika ensin)
        formats = [
            "%d.%m.%Y %H.%M.%S",    # 1.1.2023 10.19.00
            "%d.%m.%Y %H:%M:%S",    # 1.1.2023 10:19:00
            "%d.%m.%Y %H.%M",       # 1.1.2023 10.19
            "%d.%m.%Y %H:%M",       # 1.1.2023 10:19
            "%d.%m.%Y",             # 1.1.2023
            "%Y-%m-%d %H:%M:%S",    # 2023-01-01 10:19:00
            "%Y-%m-%d",             # 2023-01-01
            "%d/%m/%Y",             # 01/01/2023
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value_clean, fmt).date()
            except ValueError:
                continue
    return None


def _parse_bool(value, column_name: str = None) -> bool:
    """
    Parsii boolean-arvon Excel-solusta.
    
    Tukee:
    - Boolean-arvoja (True/False)
    - Numeerisia arvoja (1/0)
    - Tekstiarvoja ("x", "kyllä", "true", "yes", "on", "1")
    - Tekstiarvoja jotka vastaavat sarakkeen nimeä (esim. "Pienpuhdistamo" sarakkeessa Pienpuhdistamo)
    """
    if pd.isna(value) or value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        value_stripped = value.strip()
        value_lower = value_stripped.lower()
        # Yleiset true-arvot
        if value_lower in ("1", "x", "kyllä", "kylla", "true", "yes", "on"):
            return True
        # Jos arvo vastaa sarakkeen nimeä (case-insensitive), tulkitaan true
        if column_name and value_lower == column_name.lower():
            return True
        # Jos solussa on mikä tahansa ei-tyhjä teksti, tulkitaan true
        # (Excel-tiedostossa kaivotietotyyppi on merkitty kirjoittamalla tyypin nimi)
        if value_stripped:
            return True
    return False


def _parse_str(value) -> Optional[str]:
    """Parsii merkkijonon, palauttaa None jos tyhjä."""
    if pd.isna(value) or value is None:
        return None
    result = str(value).strip()
    return result if result else None


class Kaivotiedosto:
    """
    Lukee kaivotiedot (aloitus) Excel-tiedostosta.
    
    Vastausaika tulkitaan kaivotiedon alkupäivämääräksi.
    """
    
    def __init__(self, filepath: Union[str, Path]):
        self._filepath = Path(filepath)
        self._df: Optional[pd.DataFrame] = None
        self._load()
    
    def _load(self):
        """Lataa Excel-tiedoston."""
        logger.info(f"Ladataan kaivotiedot: {self._filepath}")

        try:
            self._df = pd.read_excel(self._filepath)
            logger.info(f"Ladattu {len(self._df)} riviä")
            logger.debug(f"Sarakkeet: {list(self._df.columns)}")
        except Exception as e:
            logger.error(f"Virhe ladattaessa tiedostoa {self._filepath}: {e}")
            raise

        # Validoi otsikot
        expected_headers = get_kaivotiedosto_headers()
        actual_headers = list(self._df.columns)
        missing_headers = [h for h in expected_headers if h not in actual_headers]
        if missing_headers:
            print(f"Tiedosto: {self._filepath}, puuttuvat sarakeotsikot: {missing_headers}")
            raise RuntimeError(
                f"Kaivotiedostosta puuttuu oletettuja sarakeotsikoita: {missing_headers}"
            )

    @property
    def kaivotiedot(self) -> Iterator[KaivotiedotRow]:
        """Iteroi kaivotietorivit."""
        if self._df is None:
            return
        
        for idx, row in self._df.iterrows():
            try:
                # Parsii päivämäärä
                vastausaika = _parse_date(row.get("Vastausaika"))
                if not vastausaika:
                    logger.warning(f"Rivi {idx + 2}: Vastausaika puuttuu, ohitetaan")
                    continue
                
                # Parsii PRT
                prt = _parse_str(row.get("PRT"))
                if not prt:
                    logger.warning(f"Rivi {idx + 2}: PRT puuttuu, ohitetaan")
                    continue
                
                # Luo rawdata virheraporttia varten
                rawdata = {str(k): str(v) if not pd.isna(v) else "" for k, v in row.items()}
                
                yield KaivotiedotRow(
                    vastausaika=vastausaika,
                    prt=prt,
                    etunimi=_parse_str(row.get("Etunimi")),
                    sukunimi=_parse_str(row.get("Sukunimi")),
                    katuosoite=_parse_str(row.get("Katuosoite")),
                    postinumero=_parse_str(row.get("Postinumero")),
                    postitoimipaikka=_parse_str(row.get("Postitoimipaikka")),
                    kantovesi=_parse_bool(row.get("Kantovesi"), "Kantovesi"),
                    saostussailio=_parse_bool(row.get("Saostussäiliö"), "Saostussäiliö"),
                    pienpuhdistamo=_parse_bool(row.get("Pienpuhdistamo"), "Pienpuhdistamo"),
                    umpisailio=_parse_bool(row.get("Umpisäiliö"), "Umpisäiliö"),
                    vain_harmaat_vedet=_parse_bool(row.get("Vain harmaat vedet"), "Vain harmaat vedet"),
                    tietolahde=_parse_str(row.get("Tietolähde")),
                    rawdata=rawdata,
                )
            except Exception as e:
                logger.error(f"Virhe rivillä {idx + 2}: {e}")
                continue


class KaivotiedonLopetusTiedosto:
    """
    Lukee kaivotiedon lopetus Excel-tiedostosta.
    
    Vastausaika tulkitaan kaivotiedon loppupäivämääräksi.
    """
    
    def __init__(self, filepath: Union[str, Path]):
        self._filepath = Path(filepath)
        self._df: Optional[pd.DataFrame] = None
        self._load()
    
    def _load(self):
        """Lataa Excel-tiedoston."""
        logger.info(f"Ladataan kaivotiedon lopetukset: {self._filepath}")

        try:
            self._df = pd.read_excel(self._filepath)
            logger.info(f"Ladattu {len(self._df)} riviä")
            logger.debug(f"Sarakkeet: {list(self._df.columns)}")
        except Exception as e:
            logger.error(f"Virhe ladattaessa tiedostoa {self._filepath}: {e}")
            raise

        # Validoi otsikot
        expected_headers = get_kaivotiedosto_headers()
        actual_headers = list(self._df.columns)
        missing_headers = [h for h in expected_headers if h not in actual_headers]
        if missing_headers:
            print(f"Tiedosto: {self._filepath}, puuttuvat sarakeotsikot: {missing_headers}")
            raise RuntimeError(
                f"Kaivotiedon lopetustiedostosta puuttuu oletettuja sarakeotsikoita: {missing_headers}"
            )

    @property
    def lopetukset(self) -> Iterator[KaivotiedonLopetusRow]:
        """Iteroi lopetusrivit."""
        if self._df is None:
            return
        
        for idx, row in self._df.iterrows():
            try:
                # Parsii päivämäärä
                vastausaika = _parse_date(row.get("Vastausaika"))
                if not vastausaika:
                    logger.warning(f"Rivi {idx + 2}: Vastausaika puuttuu, ohitetaan")
                    continue
                
                # Parsii PRT
                prt = _parse_str(row.get("PRT"))
                if not prt:
                    logger.warning(f"Rivi {idx + 2}: PRT puuttuu, ohitetaan")
                    continue
                
                # Luo rawdata virheraporttia varten
                rawdata = {str(k): str(v) if not pd.isna(v) else "" for k, v in row.items()}
                
                yield KaivotiedonLopetusRow(
                    vastausaika=vastausaika,
                    prt=prt,
                    etunimi=_parse_str(row.get("Etunimi")),
                    sukunimi=_parse_str(row.get("Sukunimi")),
                    katuosoite=_parse_str(row.get("Katuosoite")),
                    postinumero=_parse_str(row.get("Postinumero")),
                    postitoimipaikka=_parse_str(row.get("Postitoimipaikka")),
                    kantovesi=_parse_bool(row.get("Kantovesi"), "Kantovesi"),
                    saostussailio=_parse_bool(row.get("Saostussäiliö"), "Saostussäiliö"),
                    pienpuhdistamo=_parse_bool(row.get("Pienpuhdistamo"), "Pienpuhdistamo"),
                    umpisailio=_parse_bool(row.get("Umpisäiliö"), "Umpisäiliö"),
                    vain_harmaat_vedet=_parse_bool(row.get("Vain harmaat vedet"), "Vain harmaat vedet"),
                    tietolahde=_parse_str(row.get("Tietolähde")),
                    rawdata=rawdata,
                )
            except Exception as e:
                logger.error(f"Virhe rivillä {idx + 2}: {e}")
                continue
