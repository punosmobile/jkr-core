import datetime
import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, root_validator, validator

# from jkrimporter.utils.validators import (
#     date_pre_validator,
#     date_range_root_validator,
#     int_validator,
#     split_by_comma,
#     trim_ytunnus,
# )


class Jatelaji(str, Enum):
    aluekerays = "Aluekeräys"
    seka = "Sekajäte"
    energia = "Energia"
    bio = "Bio"
    kartonki = "Kartonki"
    pahvi = "Pahvi"
    metalli = "Metalli"
    lasi = "Lasi"
    paperi = "Paperi"
    muovi = "Muovi"
    liete = "Liete"
    musta_liete = "Musta liete"
    harmaa_liete = "Harmaa liete"


class Asiakas(BaseModel):
    UrakoitsijaId: str
    UrakoitsijankohdeId: str
    Kiinteistotunnus: Optional[str] = None
    Kiinteistonkatuosoite: str
    Kiinteistonposti: str
    kimppa: Optional[bool] = False
    kimppaid: Optional[str] = None
    Haltijannimi: str
    Haltijanyhteyshlo: Optional[str] = None
    Haltijankatuosoite: str
    Haltijanposti: str
    Haltijanmaakoodi: Optional[str] = None
    Haltijanulkomaanpaikkakunta: Optional[str] = None
    Pvmalk: datetime.date
    Pvmasti: datetime.date
    tyyppiIdEWC: Jatelaji
    kaynnit: int = Field(alias="COUNT(kaynnit)")
    astiamaara: float = Field(alias="SUM(astiamaara)")
    koko: Optional[float]
    paino: Optional[float] = Field(alias="SUM(paino)")
    tyhjennysvali: Optional[int] = None
    Voimassaoloviikotalkaen: Optional[int] = None
    Voimassaoloviikotasti: Optional[int] = None
    Kuntatun: Optional[int] = None

    @validator("Kiinteistonkatuosoite", "Haltijankatuosoite", pre=True)
    def fix_katuosoite(value: str):
        # osoite must be in title case for parsing
        value = value.title()
        # asunto abbreviation should be lowercase
        asunto_without_dot_regex = r"([0-9]+[a-z]?\s)(As)(\s[0-9]+$)"
        asunto_with_dot_regex = r"\1as.\3"
        return re.sub(asunto_without_dot_regex, asunto_with_dot_regex, value)

    @validator("Haltijanposti", "Kiinteistonposti", pre=True)
    def fix_double_spaces(value: str):
        while "  " in value:
            value = value.replace("  ", " ")
        return value

    @validator("kimppa", pre=True)
    def parse_kimppa(value: str):
        # no idea why pydantic has trouble with coercing empty strings
        # to boolean
        return bool(value)

    @validator("koko", "paino", pre=True)
    def parse_float(value: str):
        # okay, so floats might have . or , as the separator
        return float(value.replace(",", "."))

    @validator("tyyppiIdEWC", pre=True)
    def parse_jatelaji(value: str):
        if value == "Sekaj":
            value = "Sekajäte"
        return value.title()

    @validator("Pvmalk", "Pvmasti", pre=True)
    def parse_date(value: str):
        # date may be in a variety of formats. Pydantic cannot parse all
        # of them by default
        if "/" in value:
            return value
        if "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()

    @validator(
        "tyhjennysvali", "Voimassaoloviikotalkaen", "Voimassaoloviikotasti", pre=True
    )
    def fix_na(value: str):
        # Many fields may have strings such as #N/A. Parse them to None.
        if value == "#N/A":
            return None
        return value

    @validator("Kuntatun", pre=True)
    def parse_kuntatunnus(value: str):
        # kuntatunnus may be missing. No idea why pydantic has trouble
        # with parsing it as optional None.
        if value:
            return int(value)
        return None
