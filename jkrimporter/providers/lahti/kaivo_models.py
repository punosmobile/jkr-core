"""
Kaivotietojen datamallit.

LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional


class KaivotietoTyyppi(str, Enum):
    """Kaivotietotyypit lietevelvoitteiden hallintaan."""
    KANTOVESI = "Kantovesi"
    SAOSTUSSAILIO = "Saostussäiliö"
    PIENPUHDISTAMO = "Pienpuhdistamo"
    UMPISAILIO = "Umpisäiliö"
    VAIN_HARMAAT_VEDET = "Vain harmaat vedet"


# Kartoitus Excel-sarakkeiden nimistä kaivotietotyyppeihin
EXCEL_SARAKE_TO_KAIVOTIETOTYYPPI: Dict[str, KaivotietoTyyppi] = {
    "Kantovesi": KaivotietoTyyppi.KANTOVESI,
    "Saostussäiliö": KaivotietoTyyppi.SAOSTUSSAILIO,
    "Pienpuhdistamo": KaivotietoTyyppi.PIENPUHDISTAMO,
    "Umpisäiliö": KaivotietoTyyppi.UMPISAILIO,
    "Vain harmaat vedet": KaivotietoTyyppi.VAIN_HARMAAT_VEDET,
}


@dataclass
class KaivotiedotRow:
    """
    Yksi rivi kaivotiedot Excel-tiedostosta.
    
    Yksi rivi voi sisältää useita kaivotietotyyppejä (boolean-arvot).
    """
    vastausaika: date
    prt: str
    etunimi: Optional[str] = None
    sukunimi: Optional[str] = None
    katuosoite: Optional[str] = None
    postinumero: Optional[str] = None
    postitoimipaikka: Optional[str] = None
    kantovesi: bool = False
    saostussailio: bool = False
    pienpuhdistamo: bool = False
    umpisailio: bool = False
    vain_harmaat_vedet: bool = False
    tietolahde: Optional[str] = None
    
    # Alkuperäinen rivi virheraporttia varten
    rawdata: Optional[Dict[str, str]] = None
    
    def get_kaivotietotyypit(self) -> List[KaivotietoTyyppi]:
        """
        Palauttaa listan kaivotietotyypeistä, jotka ovat true tällä rivillä.
        """
        tyypit = []
        if self.kantovesi:
            tyypit.append(KaivotietoTyyppi.KANTOVESI)
        if self.saostussailio:
            tyypit.append(KaivotietoTyyppi.SAOSTUSSAILIO)
        if self.pienpuhdistamo:
            tyypit.append(KaivotietoTyyppi.PIENPUHDISTAMO)
        if self.umpisailio:
            tyypit.append(KaivotietoTyyppi.UMPISAILIO)
        if self.vain_harmaat_vedet:
            tyypit.append(KaivotietoTyyppi.VAIN_HARMAAT_VEDET)
        return tyypit
    
    def get_osapuoli_nimi(self) -> Optional[str]:
        """Palauttaa osapuolen nimen (etunimi + sukunimi)."""
        if self.etunimi and self.sukunimi:
            return f"{self.etunimi} {self.sukunimi}"
        elif self.sukunimi:
            return self.sukunimi
        elif self.etunimi:
            return self.etunimi
        return None


@dataclass
class KaivotiedonLopetusRow:
    """
    Yksi rivi kaivotiedon lopetus Excel-tiedostosta.
    
    Sama rakenne kuin aloitustiedostossa, mutta vastausaika on loppupvm.
    """
    vastausaika: date  # Tämä on loppupvm
    prt: str
    etunimi: Optional[str] = None
    sukunimi: Optional[str] = None
    katuosoite: Optional[str] = None
    postinumero: Optional[str] = None
    postitoimipaikka: Optional[str] = None
    kantovesi: bool = False
    saostussailio: bool = False
    pienpuhdistamo: bool = False
    umpisailio: bool = False
    vain_harmaat_vedet: bool = False
    tietolahde: Optional[str] = None
    
    # Alkuperäinen rivi virheraporttia varten
    rawdata: Optional[Dict[str, str]] = None
    
    def get_kaivotietotyypit(self) -> List[KaivotietoTyyppi]:
        """
        Palauttaa listan kaivotietotyypeistä, jotka lopetetaan.
        """
        tyypit = []
        if self.kantovesi:
            tyypit.append(KaivotietoTyyppi.KANTOVESI)
        if self.saostussailio:
            tyypit.append(KaivotietoTyyppi.SAOSTUSSAILIO)
        if self.pienpuhdistamo:
            tyypit.append(KaivotietoTyyppi.PIENPUHDISTAMO)
        if self.umpisailio:
            tyypit.append(KaivotietoTyyppi.UMPISAILIO)
        if self.vain_harmaat_vedet:
            tyypit.append(KaivotietoTyyppi.VAIN_HARMAAT_VEDET)
        return tyypit
