import datetime
import logging
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

from openpyxl.reader.excel import load_workbook
from pydantic import BaseModel, Field, ValidationError, root_validator, validator

from jkrimporter.datasheets import (
    CsvSheetCollection,
    ExcelFileSheetCollection,
    ExcelSheetCollection,
    SiirtotiedostoSheet,
)
from jkrimporter.utils.validators import (
    date_pre_validator,
    date_range_root_validator,
    int_validator,
    split_by_comma,
    trim_ytunnus,
)

logger = logging.getLogger(__name__)


class Jatelaji(str, Enum):
    seka = "Sekajäte"
    energia = "Energia"
    bio = "Biojäte"
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
    urakoitsija: str
    asiakasnumero: str
    rakennustunnus: Optional[str] = None
    kohde_katuosoite: str
    kohde_posti: str
    kimppa: Optional[bool] = False
    kimppa_asiakasnumero: Optional[str] = None
    haltija_nimi: str
    haltija_yhteyshlo: str
    haltija_osoite: str
    haltija_posti: str
    haltija_maa: str
    haltija_ulkomainen_osoite: Optional[str] = None
    alkupvm: datetime.date
    loppupvm: datetime.date
    jatelaji: str
    kaynnit: int
    astiat: float
    tyhjennysvali: int
    voimassaoloviikotalkaen: int
    voimassaoloviikotasti: int


# class Asiakas(BaseModel):
#     asiakasnumero: str
#     alkupvm: Optional[datetime.date]
#     loppupvm: Optional[datetime.date] = Field(alias="lopetuspvm")
#     kiinteistotunnukset: List[str] = Field(alias="kiinteistötunnukset")
#     rakennustunnukset: List[str]
#     haltija_nimi: str
#     haltija_ytunnus: Optional[str]
#     kohde_katuosoite: str
#     kohde_postinumero: Optional[str]
#     kohde_postitoimipaikka: Optional[str]
#     kohde_kunta: Optional[str]
#     yhteyshenkilo_nimi: Optional[str] = Field(alias="yhteyshenkilö_nimi")
#     yhteyshenkilo_katuosoite: Optional[str] = Field(alias="yhteyshenkilö_katuosoite")
#     yhteyshenkilo_postinumero: Optional[str] = Field(alias="yhteyshenkilö_postinumero")
#     yhteyshenkilo_postitoimipaikka: Optional[str] = Field(
#         alias="yhteyshenkilö_postitoimipaikka"
#     )
#     yhteyshenkilo_erikoisosoite: Optional[str] = Field(
#         alias="yhteyshenkilö_erikoisosoite"
#     )

#     def __init__(self, *args, **data):
#         data["rakennustunnukset"] = split_by_comma(data["rakennustunnukset"])
#         data["kiinteistötunnukset"] = split_by_comma(data["kiinteistötunnukset"])
#         data["haltija_ytunnus"] = trim_ytunnus(data["haltija_ytunnus"])

#         super().__init__(*args, **data)

#     # Validators
#     _date_validator = date_pre_validator("alkupvm", "loppupvm")
#     _date_range_validator = date_range_root_validator()

#     @validator("yhteyshenkilo_nimi", pre=True)
#     def trim_str(value):
#         if isinstance(value, str):
#             value = value.strip()
#         return value


class AsiakastiedotSheet(SiirtotiedostoSheet[Asiakas]):
    @staticmethod
    def _obj_from_dict(data):
        return Asiakas.parse_obj(data)


# class Tyhjennystapahtuma(BaseModel):
#     asiakasnumero: str
#     jatelaji: str = Field(alias="jätelaji")
#     pvm: Optional[datetime.date]
#     tyhjennyskerrat: Optional[int]
#     massa: Optional[int]
#     tilavuus: Optional[int]

#     # Validators
#     _date_validator = date_pre_validator("pvm")

#     @validator("massa", "tilavuus", pre=True)
#     def replace_comma(cls, v: str):
#         if isinstance(v, str):
#             v = v.replace(",", ".").replace(" ", "")
#         return int(float(v))


# class TyhjennystapahtumatSheet(SiirtotiedostoSheet[Tyhjennystapahtuma]):
#     @staticmethod
#     def _obj_from_dict(data):
#         return Tyhjennystapahtuma.parse_obj(data)


# class Tyhjennysvali(BaseModel):
#     asiakasnumero: str
#     jatelaji: Jatelaji = Field(alias="jätelaji")
#     alkupvm: Optional[datetime.date]
#     loppupvm: Optional[datetime.date]
#     alkuvko: Optional[int] = 1
#     loppuvko: Optional[int] = 53
#     tyhjennysvali: float = Field(alias="tyhjennysväli")

#     # Validators
#     _date_validator = date_pre_validator("alkupvm", "loppupvm")
#     _date_range_validator = date_range_root_validator()


# class TyhjennysvalitSheet(SiirtotiedostoSheet[Tyhjennysvali]):
#     @staticmethod
#     def _obj_from_dict(data):
#         return Tyhjennysvali.parse_obj(data)


# class Keraysvaline(BaseModel):
#     asiakasnumero: str
#     jatelaji: Jatelaji = Field(alias="jätelaji")
#     tilavuus: Optional[int]
#     maara: int = Field(alias="määrä")
#     tyyppi: Optional[str]

#     @root_validator
#     def check_mandatory_tilavuus(cls, values):
#         tilavuus = values.get("tilavuus")
#         if tilavuus is None:
#             jatelaji = values.get("jatelaji")
#             if jatelaji in (Jatelaji.bio):
#                 raise ValidationError("Tilavuus pakollinen")

#         return values

#     _int_validator = int_validator("tilavuus")


# class KeraysvalineSheet(SiirtotiedostoSheet[Keraysvaline]):
#     @staticmethod
#     def _obj_from_dict(data):
#         return Keraysvaline.parse_obj(data)


# class Keskeytys(BaseModel):
#     asiakasnumero: str
#     jatelaji: Jatelaji = Field(alias="jätelaji")
#     alkupvm: datetime.date
#     loppupvm: datetime.date
#     selite: Optional[str] = None

#     _date_validator = date_pre_validator("alkupvm", "loppupvm")
#     _date_range_validator = date_range_root_validator()


# class KeskeytysSheet(SiirtotiedostoSheet[Keskeytys]):
#     @staticmethod
#     def _obj_from_dict(data):
#         return Keskeytys.parse_obj(data)


# class Kimppa(BaseModel):
#     asiakasnumero: str
#     kimppaisanta: str = Field(alias="kimppaisäntä")
#     alkupvm: Optional[datetime.date]
#     loppupvm: Optional[datetime.date]
#     jatelaji: Optional[Jatelaji] = Field(None, alias="jätelaji")

#     # Validators
#     _date_validator = date_pre_validator("alkupvm", "loppupvm")
#     _date_range_validator = date_range_root_validator()

#     @validator("jatelaji", pre=True)
#     def empty_to_none(value):
#         if isinstance(value, str):
#             if not value:
#                 return None
#         return value


# class KimppaSheet(SiirtotiedostoSheet[Kimppa]):
#     @staticmethod
#     def _obj_from_dict(data):
#         return Kimppa.parse_obj(data)


class LahtiSiirtotiedosto:
    # Lahti has no set sheet names. It has a directory with different sheets
    # for different providers, all having identical format.

    def __init__(self, path):
        sheet_collection_cls = LahtiSiirtotiedosto._class_getter(path)
        self._sheet_collection = sheet_collection_cls(path)

    @classmethod
    def readable_by_me(cls, path):
        p = Path(path)
        print(path)
        for f in p.iterdir():
            print(f)
            if f.is_file() and f.suffix == ".xlsx":
                print("found excel file")
                try:
                    workbook = load_workbook(
                        filename=f, data_only=True, read_only=True
                    )
                    print(workbook)
                    sheets = workbook.sheetnames
                    if "in" in sheets:
                        return True
                except Exception:
                    pass
        return False

    @classmethod
    def _class_getter(cls, path):
        sheet_cls = None
        if not path.exists():
            raise FileNotFoundError("path {} does not exists".format(path))
        if os.path.isdir(path):
            dir_content = os.listdir(path)
            if LahtiSiirtotiedosto.SheetNames.ASIAKASTIEDOT + ".xlsx" in dir_content:
                sheet_cls = ExcelFileSheetCollection
        else:
            _, ext = os.path.splitext(path)
            if ext == "xlsx":
                sheet_cls = ExcelSheetCollection

        return sheet_cls

    @property
    def kohteet(self):
        return AsiakastiedotSheet(
            self._sheet_collection, LahtiSiirtotiedosto.SheetNames.ASIAKASTIEDOT
        )
