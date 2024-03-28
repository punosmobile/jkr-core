import datetime
import re
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, root_validator, validator

from jkrimporter.model import Paatostulos, Tapahtumalaji


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
    tyhjennysvali: Optional[int] = None  # AKP does not need tyhjennysvali to be valid
    tyhjennysvali2: Optional[int] = None
    kertaaviikossa: Optional[int] = None
    kertaaviikossa2: Optional[int] = None
    Voimassaoloviikotalkaen: int
    Voimassaoloviikotasti: int
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
        if value == "Aluekeräyspiste":
            value = "Aluekeräys"
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
        "Voimassaoloviikotalkaen",
        "Voimassaoloviikotasti",
        "Voimassaoloviikotalkaen2",
        "Voimassaoloviikotasti2",
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

    @validator(
        "kaynnit",
        "kertaaviikossa",
        "kertaaviikossa2",
        "tyhjennysvali",
        "tyhjennysvali2",
        pre=True
    )
    def validate_kaynnit(cls, value):
        if isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return None
        return value

    @root_validator(pre=True)
    def validate_optional_fields(cls, values):
        tyhjennysvali2 = values.get("tyhjennysvali2")
        voimassaoloviikotalkaen2 = values.get("Voimassaoloviikotalkaen2")
        voimassaoloviikotasti2 = values.get("Voimassaoloviikotasti2")

        if tyhjennysvali2 is not None:
            if voimassaoloviikotalkaen2 is None or voimassaoloviikotasti2 is None:
                raise ValueError("If tyhjennysvali2 is not empty, Voimassaoloviikotalkaen2 and Voimassaoloviikotasti2 must not be empty.")
        return values


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
    lahiosoite: Optional[str] = Field(alias="Lähiosoite")
    Postinumero: Optional[str]
    Postitoimipaikka: Optional[str]
    rawdata: Optional[Dict[str, str]] = None

    @validator("voimassaalkaen", "voimassaasti", pre=True)
    def parse_date(value: Union[date, str]):
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        return value

    # strip "vastaanottaja" from vastaanottaja
    @validator("vastaanottaja", pre=True)
    def parse_vastaanottaja(value: str):
        if type(value) is not str:
            return None
        words = value.split()
        if words[0] == "vastaanottaja":
            return value[14:]
        return value

    @validator("paatos", pre=True)
    def parse_paatos(value: str):
        if type(value) is not str:
            return None
        words = value.lower().split()
        for laji in Tapahtumalaji:
            if " ".join(words[:-1]) == laji.value.lower():
                for tulos in Paatostulos:
                    if words[-1] == tulos.value.lower():
                        return laji.value + " " + tulos.value
        return None

    @root_validator
    def validate_dates(cls, values):
        voimassaalkaen = values.get("voimassaalkaen")
        voimassaasti = values.get("voimassaasti")
        if voimassaalkaen is not None and voimassaasti is not None:
            if voimassaalkaen >= voimassaasti:
                raise ValueError(
                    "Voimassaalkaen-päivämäärän on oltava ennen voimassaasti-päivämäärää."
                )
        return values


class Ilmoitus(BaseModel):
    Vastausaika: datetime.date
    vastuuhenkilo_etunimi: Optional[str] = Field(
        None, alias="Kompostoinnin vastuuhenkilön yhteystiedot:Etunimi"
    )
    vastuuhenkilo_sukunimi: Optional[str] = Field(
        None, alias="Kompostoinnin vastuuhenkilön yhteystiedot:Sukunimi"
    )
    vastuuhenkilo_postinumero: str = Field(
        alias="Kompostoinnin vastuuhenkilön yhteystiedot:Postinumero"
    )  # Note, etunollat pitäisi lisätä. Pitäisi olla 5 numeroinen numerosarja.
    vastuuhenkilo_postitoimipaikka: str = Field(
        alias="Kompostoinnin vastuuhenkilön yhteystiedot:Postitoimipaikka"
    )
    vastuuhenkilo_osoite: str = Field(
        alias="Kompostoinnin vastuuhenkilön yhteystiedot:Postiosoite"
    )
    onko_kimppa: str = Field(alias="Kompostoria käyttävien rakennusten lukumäärä")
    prt: List[str] = Field(
        alias="1. Kompostoria käyttävän rakennuksen tiedot:Käsittelijän lisäämä tunniste"
    )
    onko_hyvaksytty: str = Field(
        alias="1. Kompostoria käyttävän rakennuksen tiedot:Viranomaisen lisäämä tarkenne"
    )
    voimassaasti: Union[datetime.date, str] = Field(alias="Voimassaolopäivä")
    sijainti_prt: List[str] = Field(
        alias="Rakennuksen tiedot, jossa kompostori sijaitsee:Käsittelijän lisäämä tunniste"
    )
    kayttaja_etunimi: Optional[str] = Field(
        None, alias="1. Kompostoria käyttävän rakennuksen tiedot:Haltijan etunimi"
    )
    kayttaja_sukunimi: Optional[str] = Field(
        None, alias="1. Kompostoria käyttävän rakennuksen tiedot:Haltijan sukunimi"
    )
    # Store the original row.
    rawdata: Optional[Dict[str, str]]

    @validator("Vastausaika", pre=True)
    def parse_vastausaika(value: Union[date, str]):
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        return value

    @validator("vastuuhenkilo_postinumero")
    def add_zeros(value: str):
        if len(value) < 5:
            return "0" * (5 - len(value)) + value
        return value

    @validator("voimassaasti", pre=True)
    def parse_voimassaasti(value: Union[date, str]):
        if isinstance(value, str):
            try:
                # Some rows come with milliseconds included
                parsed_date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Most come without milliseconds.
                parsed_date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            reformatted_date = parsed_date.strftime("%Y-%m-%d")
            return reformatted_date
        return value

    @validator('sijainti_prt', 'prt', pre=True)
    def parse_prts(value: str):
        if isinstance(value, str):
            return value.split(',')
        return value

    @root_validator
    def check_vastuuhenkilo_names(cls, values):
        etunimi = values.get('vastuuhenkilo_etunimi')
        sukunimi = values.get('vastuuhenkilo_sukunimi')
        if etunimi is None and sukunimi is None:
            raise ValueError(
                "Suku- ja etunimi eivät saa olla tyhjiä."
            )
        return values

    @root_validator
    def check_kayttaja_names(cls, values):
        etunimi = values.get('kayttaja_etunimi')
        sukunimi = values.get('kayttaja_sukunimi')
        if etunimi is None and sukunimi is None:
            raise ValueError(
                "Suku- ja etunimi eivät saa olla tyhjiä."
            )
        return values

    @root_validator
    def validate_dates(cls, values):
        voimassaalkaen = values.get("Vastausaika")
        voimassaasti = values.get("voimassaasti")
        if voimassaalkaen is not None and voimassaasti is not None:
            if voimassaalkaen >= voimassaasti:
                raise ValueError(
                    "Vastausaika-päivämäärän on oltava ennen voimassaolopäivä-päivämäärää."
                )
        return values


class LopetusIlmoitus(BaseModel):
    Vastausaika: datetime.date  # Kompostoinnin päättymisen ajankohta.
    prt: List[str] = Field(
        alias="Rakennuksen tiedot:Käsittelijän lisäämä tunniste"
    )
    etunimi: Optional[str] = Field(
        None, alias="Kompostoinnin vastuuhenkilö:Etunimi"
    )
    sukunimi: Optional[str] = Field(
        None, alias="Kompostoinnin vastuuhenkilö:Sukunimi"
    )
    rawdata: Optional[Dict[str, str]]

    @validator('prt', pre=True)
    def parse_prts(value: str):
        if isinstance(value, str):
            return value.split(',')
        return value

    @validator("Vastausaika", pre=True)
    def parse_vastausaika(value: Union[date, str]):
        if type(value) is str and "." in value:
            return datetime.datetime.strptime(value, "%d.%m.%Y").date()
        return value

    @root_validator
    def check_name(cls, values):
        etunimi = values.get('etunimi')
        sukunimi = values.get('sukunimi')
        if etunimi is None and sukunimi is None:
            raise ValueError(
                "Suku- ja etunimi eivät saa olla tyhjiä."
            )
        return values
