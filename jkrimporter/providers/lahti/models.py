import datetime
import re
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, validator


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


# AsiakasRow corresponds to one row in source data. In most cases,
# all the asiakas data is presented in one row (= AsiakasRow).
class AsiakasRow(BaseModel):
    UrakoitsijaId: str
    UrakoitsijankohdeId: str
    Kiinteistotunnus: Optional[str] = None
    Kiinteistonkatuosoite: Optional[str] = None
    Kiinteistonposti: str
    Haltijannimi: str
    Haltijanyhteyshlo: Optional[str] = None
    Haltijankatuosoite: Optional[str] = None
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
    tyhjennysvali2: Optional[int] = None
    kertaaviikossa: Optional[int] = None
    kertaaviikossa2: Optional[int] = None
    Voimassaoloviikotalkaen: Optional[int] = None
    Voimassaoloviikotasti: Optional[int] = None
    Voimassaoloviikotalkaen2: Optional[int] = None
    Voimassaoloviikotasti2: Optional[int] = None
    Kuntatun: Optional[int] = None
    palveluKimppakohdeId: Optional[str] = None
    kimpanNimi: Optional[str] = None
    Kimpanyhteyshlo: Optional[str] = None
    Kimpankatuosoite: Optional[str] = None
    Kimpanposti: Optional[str] = None
    Keskeytysalkaen: Optional[datetime.date] = (None,)
    Keskeytysasti: Optional[datetime.date] = (None,)

    # @validator("UrakoitsijankohdeId", pre=True)
    # TODO: Cannot construct id from name. Name is validated later.
    # def construct_missing_id(value: Union[str, None], values: Dict):
    #     print(value)
    #     print(values)
    #     if not value:
    #         try:
    #             value = values["Haltijannimi"].lower().replace(" ", "_")
    #         except AttributeError:
    #             raise ValidationError("Asiakas must have name or id.")
    #     return str(value)

    @validator("Haltijannimi", pre=True)
    def construct_missing_name(value: Union[str, None], values: Dict):
        print(values)
        if not value:
            try:
                value = str(values["UrakoitsijankohdeId"])
            except KeyError:
                raise ValidationError("Asiakas must have name or id.")
        return str(value)

    @validator(
        "Kiinteistonkatuosoite", "Haltijankatuosoite", "Kimpankatuosoite", pre=True
    )
    def fix_katuosoite(value: Union[str, None]):
        # address may be missing
        if not value:
            return None
        # osoite must be in title case for parsing
        value = value.title()
        # asunto abbreviation should be lowercase
        asunto_without_dot_regex = r"([0-9]+[a-z]?\s)(As)(\s[0-9]+$)"
        asunto_with_dot_regex = r"\1as.\3"
        return re.sub(asunto_without_dot_regex, asunto_with_dot_regex, value)

    @validator("Haltijanposti", "Kiinteistonposti", "Kimpanposti", pre=True)
    def fix_posti(value: Union[str, int]):
        # looks like some postiosoite only have postinumero
        value = str(value)
        while "  " in value:
            value = value.replace("  ", " ")
        return value

    # @validator("kimppa", pre=True)
    # def parse_kimppa(value: Union[bool, str]):
    #     # no idea why pydantic has trouble with coercing empty strings
    #     # to boolean
    #     return bool(value)

    @validator("koko", "paino", pre=True)
    def parse_float(value: Union[float, str]):
        # If float wasn't parsed, let's parse them
        # Return none if empty string was parsed
        if value == "":
            return None
        if type(value) is str:
            # we might have . or , as the separator
            return float(value.replace(",", "."))
        return value

    @validator("tyyppiIdEWC", pre=True)
    def parse_jatelaji(value: str):
        if value == "Sekaj":
            value = "Sekajäte"
        if value == "Biojäte":
            value = "Bio"
        if value == "Kartonkipakkaus":
            value = "Kartonki"
        if value == "Muovipakkaus":
            value = "Muovi"
        if value == "Lasipakkaus":
            value = "Lasi"
        return value.title()

    @validator("Pvmalk", "Pvmasti", pre=True)
    def parse_date(value: Union[date, str]):
        # If date wasn't parsed, let's parse them.
        # Date may be in a variety of formats. Pydantic cannot parse all
        # of them by default
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        return value

    @validator("Keskeytysalkaen", "Keskeytysasti", pre=True)
    def parse_date_or_empty(value: Union[date, str]):
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        if value == "#N/A" or value == "":
            return None
        return value

    @validator(
        "tyhjennysvali",
        "Voimassaoloviikotalkaen",
        "Voimassaoloviikotasti",
        "Voimassaoloviikotalkaen2",
        "Voimassaoloviikotasti2",
        "tyhjennysvali2",
        pre=True,
    )
    def fix_na(value: str):
        # Many fields may have strings such as #N/A or empty string. Parse them to None.
        if value == "#N/A" or value == "":
            return None
        return value

    @validator("Kuntatun", pre=True)
    def parse_kuntatunnus(value: str):
        # kuntatunnus may be missing. No idea why pydantic has trouble
        # with parsing it as optional None.
        if value:
            return int(value)
        return None

    @validator("astiamaara", pre=True, always=True)
    def parse_decimal_separator(cls, value):
        if isinstance(value, str):
            # There is atleast one case where SUM(astiamaara) is "0,12"
            # Not sure what to do here, doesn't make sense that 0.12 containers have been emptied.
            # But then again, should this be converted to 0, 1 or 12?
            value = float(value.replace(",", "."))
        return value

    @validator("kaynnit", "kertaaviikossa", "kertaaviikossa2", pre=True)
    def validate_kaynnit(cls, value):
        if isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return None
        return value


class Asiakas(BaseModel):
    UrakoitsijaId: str
    UrakoitsijankohdeId: str
    Kiinteistotunnus: Optional[str] = None
    Kiinteistonkatuosoite: Optional[str] = None
    Kiinteistonposti: str
    Haltijannimi: str
    Haltijanyhteyshlo: Optional[str] = None
    Haltijankatuosoite: Optional[str] = None
    Haltijanposti: str
    Haltijanmaakoodi: Optional[str] = None
    Haltijanulkomaanpaikkakunta: Optional[str] = None
    Pvmalk: datetime.date
    Pvmasti: datetime.date
    tyyppiIdEWC: Jatelaji
    kaynnit: List[int] = []  # käynnit rowwise
    astiamaara: float
    koko: Optional[float]
    paino: List[Union[float, None]] = []  # paino rowwise
    tyhjennysvali: List[Union[int, None]] = (
        []
    )  # [row1_tyhjennysvali, row1_tyhjennysvali2, row2_tyhjennysvali, ...]
    kertaaviikossa: List[Union[int, None]] = (
        []
    )  # [row1_kertaaviikossa, row1_kertaaviikossa2, row2_kertaaviikossa, ...]
    Voimassaoloviikotalkaen: List[Union[int, None]] = (
        []
    )  # [row1_Voimassaoloviikotalkaen, row1_Voimassaoloviikotalkaen2, row2_Voimassaoloviikotalkaen, ...]
    Voimassaoloviikotasti: List[Union[int, None]] = (
        []
    )  # [row1_Voimassaoloviikotasti, row1_Voimassaoloviikotasti2, row2_Voimassaoloviikotasti, ...]
    Kuntatun: Optional[int] = None
    palveluKimppakohdeId: Optional[str] = None
    kimpanNimi: Optional[str] = None
    Kimpanyhteyshlo: Optional[str] = None
    Kimpankatuosoite: Optional[str] = None
    Kimpanposti: Optional[str] = None
    Keskeytysalkaen: Optional[datetime.date] = (None,)
    Keskeytysasti: Optional[datetime.date] = (None,)

    def __init__(self, row: AsiakasRow):
        super().__init__(
            UrakoitsijaId=row.UrakoitsijaId,
            UrakoitsijankohdeId=row.UrakoitsijankohdeId,
            Kiinteistotunnus=row.Kiinteistotunnus,
            Kiinteistonkatuosoite=row.Kiinteistonkatuosoite,
            Kiinteistonposti=row.Kiinteistonposti,
            Haltijannimi=row.Haltijannimi,
            Haltijanyhteyshlo=row.Haltijanyhteyshlo,
            Haltijankatuosoite=row.Haltijankatuosoite,
            Haltijanposti=row.Haltijanposti,
            Haltijanmaakoodi=row.Haltijanmaakoodi,
            Haltijanulkomaanpaikkakunta=row.Haltijanulkomaanpaikkakunta,
            Pvmalk=row.Pvmalk,
            Pvmasti=row.Pvmasti,
            tyyppiIdEWC=row.tyyppiIdEWC,
            kaynnit=[row.kaynnit],
            astiamaara=row.astiamaara,
            koko=row.koko,
            paino=[row.paino],
            Kuntatun=row.Kuntatun,
            palveluKimppakohdeId=row.palveluKimppakohdeId,
            kimpanNimi=row.kimpanNimi,
            Kimpanyhteyshlo=row.Kimpanyhteyshlo,
            Kimpankatuosoite=row.Kimpankatuosoite,
            Kimpanposti=row.Kimpanposti,
            Keskeytysalkaen=row.Keskeytysalkaen,
            Keskeytysasti=row.Keskeytysasti,
        )

        if (
            row.tyhjennysvali
            and row.Voimassaoloviikotalkaen
            and row.Voimassaoloviikotasti
        ):
            self.Voimassaoloviikotalkaen.append(row.Voimassaoloviikotalkaen)
            self.Voimassaoloviikotasti.append(row.Voimassaoloviikotasti)
            self.tyhjennysvali.append(row.tyhjennysvali)
            self.kertaaviikossa.append(row.kertaaviikossa)
        else:
            self.Voimassaoloviikotalkaen.append(None)
            self.Voimassaoloviikotasti.append(None)
            self.tyhjennysvali.append(None)
            self.kertaaviikossa.append(None)

        if (
            row.tyhjennysvali2
            and row.Voimassaoloviikotalkaen2
            and row.Voimassaoloviikotasti2
        ):
            self.Voimassaoloviikotalkaen.append(row.Voimassaoloviikotalkaen2)
            self.Voimassaoloviikotasti.append(row.Voimassaoloviikotasti2)
            self.tyhjennysvali.append(row.tyhjennysvali2)
            self.kertaaviikossa.append(row.kertaaviikossa2)
        else:
            self.Voimassaoloviikotalkaen.append(None)
            self.Voimassaoloviikotasti.append(None)
            self.tyhjennysvali.append(None)
            self.kertaaviikossa.append(None)

    def check_and_add_row(self, row: AsiakasRow):
        # If the data is on multiple rows either tyhjennysvali or kertaaviikossa
        # values are different.
        if (
            self.UrakoitsijaId == row.UrakoitsijaId
            and self.UrakoitsijankohdeId == row.UrakoitsijankohdeId
            and self.Kiinteistotunnus == row.Kiinteistotunnus
            and self.Kiinteistonkatuosoite == row.Kiinteistonkatuosoite
            and self.Kiinteistonposti == row.Kiinteistonposti
            and self.Haltijannimi == row.Haltijannimi
            and self.Haltijanyhteyshlo == row.Haltijanyhteyshlo
            and self.Haltijankatuosoite == row.Haltijankatuosoite
            and self.Haltijanposti == row.Haltijanposti
            and self.Haltijanmaakoodi == row.Haltijanmaakoodi
            and self.Haltijanulkomaanpaikkakunta == row.Haltijanulkomaanpaikkakunta
            and self.Pvmalk == row.Pvmalk
            and self.Pvmasti == row.Pvmasti
            and self.tyyppiIdEWC == row.tyyppiIdEWC
            and self.astiamaara == row.astiamaara
            and self.koko == row.koko
            and self.Kuntatun == row.Kuntatun
            and self.palveluKimppakohdeId == row.palveluKimppakohdeId
            and self.kimpanNimi == row.kimpanNimi
            and self.Kimpanyhteyshlo == row.Kimpanyhteyshlo
            and self.Kimpankatuosoite == row.Kimpankatuosoite
            and self.Kimpanposti == row.Kimpanposti
            and self.Keskeytysalkaen == row.Keskeytysalkaen
            and self.Keskeytysasti == row.Keskeytysasti
        ) and (
            row.tyhjennysvali not in self.tyhjennysvali
            or row.tyhjennysvali2 not in self.tyhjennysvali
            or row.kertaaviikossa not in self.kertaaviikossa
            or row.kertaaviikossa2 not in self.kertaaviikossa
        ):
            self.kaynnit.append(row.kaynnit)
            self.paino.append(row.paino)
            if (
                row.tyhjennysvali
                and row.Voimassaoloviikotalkaen
                and row.Voimassaoloviikotasti
            ):
                self.Voimassaoloviikotalkaen.append(row.Voimassaoloviikotalkaen)
                self.Voimassaoloviikotasti.append(row.Voimassaoloviikotasti)
                self.tyhjennysvali.append(row.tyhjennysvali)
                self.kertaaviikossa.append(row.kertaaviikossa)
            else:
                self.Voimassaoloviikotalkaen.append(None)
                self.Voimassaoloviikotasti.append(None)
                self.tyhjennysvali.append(None)
                self.kertaaviikossa.append(None)

            if (
                row.tyhjennysvali2
                and row.Voimassaoloviikotalkaen2
                and row.Voimassaoloviikotasti2
            ):
                self.Voimassaoloviikotalkaen.append(row.Voimassaoloviikotalkaen2)
                self.Voimassaoloviikotasti.append(row.Voimassaoloviikotasti2)
                self.tyhjennysvali.append(row.tyhjennysvali2)
                self.kertaaviikossa.append(row.kertaaviikossa2)
            else:
                self.Voimassaoloviikotalkaen.append(None)
                self.Voimassaoloviikotasti.append(None)
                self.tyhjennysvali.append(None)
                self.kertaaviikossa.append(None)

            return True

        return False

    def get_kaynnit(self):
        return sum(self.kaynnit)

    def get_paino(self):
        sum = 0
        for item in self.paino:
            if isinstance(item, float):
                sum += item
        return sum * 1000 if sum else None


class Paatos(BaseModel):
    Numero: str
    vastaanottaja: str = Field(alias="Lähettäjä/vastaanottaja")
    prt: str = Field(alias="PRT 1")
    paatos: str = Field(alias="Päätös 1")
    voimassaalkaen: datetime.date = Field(alias="Voimassa alkaen 1")
    voimassaasti: datetime.date = Field(alias="Voimassa asti 1")
    lisatiedot: Optional[str] = Field(alias="Lisätiedot 1")
    lahiosoite: str = Field(alias="Lähiosoite")
    Postinumero: str
    Postitoimipaikka: str

    @validator("voimassaalkaen", "voimassaasti", pre=True)
    def parse_date(value: Union[date, str]):
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        return value
