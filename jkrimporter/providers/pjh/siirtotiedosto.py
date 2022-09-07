import datetime
import logging
import os
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Generic, Iterator, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, ValidationError, root_validator, validator

from jkrimporter.datasheets import (
    CsvSheetCollection,
    ExcelFileSheetCollection,
    ExcelSheetCollection,
    SheetCollection,
)
from jkrimporter.utils.date import parse_date_string

logger = logging.getLogger(__name__)


def split_by_comma(value: Union[str, None]) -> List[str]:
    if value is None:
        return []
    return value.split(",") if value else []


def trim_ytunnus(value: Union[str, None]) -> Union[str, None]:
    if value is None:
        return value

    ytunnus = value.strip()

    if ytunnus in ("-", "000"):
        ytunnus = None

    return ytunnus


def normalize_date(v: Union[datetime.date, str, None]) -> Union[datetime.date, None]:
    if isinstance(v, str):
        if v:
            return parse_date_string(v)
        else:
            return None

    return v


def date_pre_validator(*attributes):
    return validator(*attributes, allow_reuse=True, pre=True)(normalize_date)


T = TypeVar("T")


def empty_to_none(v: Union[T, None]) -> Optional[T]:
    if not v:
        return None

    return v


def int_validator(*attributes):
    return validator(*attributes, allow_reuse=True, pre=True)(empty_to_none)


def check_alkupvm_lt_loppupvm(cls, values):
    alku, loppu = values.get("alkupvm"), values.get("loppupvm")
    if alku is not None and loppu is not None and loppu < alku:
        raise ValueError("alkupvm must be less than loppupvm")
    return values


def date_range_root_validator():
    return root_validator(allow_reuse=True)(check_alkupvm_lt_loppupvm)


T = TypeVar("T")


class SiirtotiedostoSheet(Generic[T], metaclass=ABCMeta):
    def __init__(self, sheet_collection: SheetCollection, sheet_name: str):
        self._sheet = sheet_collection._open_sheet(sheet_name)
        self._error_sheet = sheet_collection._open_error_sheet(
            sheet_name, self._sheet.headers
        )

    @abstractmethod
    def _obj_from_dict(data) -> T:
        raise NotImplementedError

    def __iter__(self) -> Iterator[T]:
        for row in self._sheet:
            try:
                obj = self._obj_from_dict(row)
            except ValidationError as e:
                error = "; ".join(
                    f"{''.join(error['loc'])}: {error['msg']}" for error in e.errors()
                )
                row_with_error = {**row, "virhe": error}
                self._error_sheet.writerow(row_with_error)
                continue

            yield obj


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


class Meta(BaseModel):
    alkupvm: datetime.date
    loppupvm: datetime.date

    _date_validator = date_pre_validator("alkupvm", "loppupvm")
    _date_range_validator = date_range_root_validator()


class MetaSheet(SiirtotiedostoSheet[Meta]):
    @staticmethod
    def _obj_from_dict(data):
        return Meta.parse_obj(data)


class Asiakas(BaseModel):
    asiakasnumero: str
    alkupvm: Optional[datetime.date]
    loppupvm: Optional[datetime.date] = Field(alias="lopetuspvm")
    kiinteistotunnukset: List[str] = Field(alias="kiinteistötunnukset")
    rakennustunnukset: List[str]
    haltija_nimi: str
    haltija_ytunnus: Optional[str]
    kohde_katuosoite: str
    kohde_postinumero: Optional[str]
    kohde_postitoimipaikka: Optional[str]
    kohde_kunta: Optional[str]
    yhteyshenkilo_nimi: Optional[str] = Field(alias="yhteyshenkilö_nimi")
    yhteyshenkilo_katuosoite: Optional[str] = Field(alias="yhteyshenkilö_katuosoite")
    yhteyshenkilo_postinumero: Optional[str] = Field(alias="yhteyshenkilö_postinumero")
    yhteyshenkilo_postitoimipaikka: Optional[str] = Field(
        alias="yhteyshenkilö_postitoimipaikka"
    )
    yhteyshenkilo_erikoisosoite: Optional[str] = Field(
        alias="yhteyshenkilö_erikoisosoite"
    )

    def __init__(self, *args, **data):
        data["rakennustunnukset"] = split_by_comma(data["rakennustunnukset"])
        data["kiinteistötunnukset"] = split_by_comma(data["kiinteistötunnukset"])
        data["haltija_ytunnus"] = trim_ytunnus(data["haltija_ytunnus"])

        super().__init__(*args, **data)

    # Validators
    _date_validator = date_pre_validator("alkupvm", "loppupvm")
    _date_range_validator = date_range_root_validator()

    @validator("yhteyshenkilo_nimi", pre=True)
    def trim_str(value):
        if isinstance(value, str):
            value = value.strip()
        return value


class AsiakastiedotSheet(SiirtotiedostoSheet[Asiakas]):
    @staticmethod
    def _obj_from_dict(data):
        return Asiakas.parse_obj(data)


class Tyhjennystapahtuma(BaseModel):
    asiakasnumero: str
    jatelaji: str = Field(alias="jätelaji")
    pvm: Optional[datetime.date]
    tyhjennyskerrat: Optional[int]
    massa: Optional[int]
    tilavuus: Optional[int]

    # Validators
    _date_validator = date_pre_validator("pvm")

    @validator("massa", "tilavuus", pre=True)
    def replace_comma(cls, v: str):
        if isinstance(v, str):
            v = v.replace(",", ".").replace(" ", "")
        return int(float(v))


class TyhjennystapahtumatSheet(SiirtotiedostoSheet[Tyhjennystapahtuma]):
    @staticmethod
    def _obj_from_dict(data):
        return Tyhjennystapahtuma.parse_obj(data)


class Tyhjennysvali(BaseModel):
    asiakasnumero: str
    jatelaji: Jatelaji = Field(alias="jätelaji")
    alkupvm: Optional[datetime.date]
    loppupvm: Optional[datetime.date]
    alkuvko: Optional[int] = 1
    loppuvko: Optional[int] = 53
    tyhjennysvali: float = Field(alias="tyhjennysväli")

    # Validators
    _date_validator = date_pre_validator("alkupvm", "loppupvm")
    _date_range_validator = date_range_root_validator()


class TyhjennysvalitSheet(SiirtotiedostoSheet[Tyhjennysvali]):
    @staticmethod
    def _obj_from_dict(data):
        return Tyhjennysvali.parse_obj(data)


class Keraysvaline(BaseModel):
    asiakasnumero: str
    jatelaji: Jatelaji = Field(alias="jätelaji")
    tilavuus: Optional[int]
    maara: int = Field(alias="määrä")
    tyyppi: Optional[str]

    @root_validator
    def check_mandatory_tilavuus(cls, values):
        tilavuus = values.get("tilavuus")
        if tilavuus is None:
            jatelaji = values.get("jatelaji")
            if jatelaji in (Jatelaji.bio):
                raise ValidationError("Tilavuus pakollinen")

        return values

    _int_validator = int_validator("tilavuus")


class KeraysvalineSheet(SiirtotiedostoSheet[Keraysvaline]):
    @staticmethod
    def _obj_from_dict(data):
        return Keraysvaline.parse_obj(data)


class Keskeytys(BaseModel):
    asiakasnumero: str
    jatelaji: Jatelaji = Field(alias="jätelaji")
    alkupvm: datetime.date
    loppupvm: datetime.date
    selite: Optional[str] = None

    _date_validator = date_pre_validator("alkupvm", "loppupvm")
    _date_range_validator = date_range_root_validator()


class KeskeytysSheet(SiirtotiedostoSheet[Keskeytys]):
    @staticmethod
    def _obj_from_dict(data):
        return Keskeytys.parse_obj(data)


class Kimppa(BaseModel):
    asiakasnumero: str
    kimppaisanta: str = Field(alias="kimppaisäntä")
    alkupvm: Optional[datetime.date]
    loppupvm: Optional[datetime.date]
    jatelaji: Optional[Jatelaji] = Field(None, alias="jätelaji")

    # Validators
    _date_validator = date_pre_validator("alkupvm", "loppupvm")
    _date_range_validator = date_range_root_validator()

    @validator("jatelaji", pre=True)
    def empty_to_none(value):
        if isinstance(value, str):
            if not value:
                return None
        return value


class KimppaSheet(SiirtotiedostoSheet[Kimppa]):
    @staticmethod
    def _obj_from_dict(data):
        return Kimppa.parse_obj(data)


class PjhSiirtotiedosto:
    class SheetNames:
        META = "metatiedot"
        ASIAKASTIEDOT = "asiakastiedot"
        TYHJENNYSTAPAHTUMAT = "tyhjennystapahtumat"
        TYHJENNYSVALIT = "tyhjennysvälit"
        KIMPAT = "kimpat"
        KESKEYTYKSET = "keskeytykset"
        KERAYSVALINEET = "keräysvälineet"
        TOIMITUSKOHTEET = "toimituskohteet"
        TOIMITUKSET = "toimitukset"

    def __init__(self, path):
        sheet_collection_cls = PjhSiirtotiedosto._class_getter(path)
        self._sheet_collection = sheet_collection_cls(path)

    @classmethod
    def _class_getter(cls, path):
        sheet_cls = None
        if not path.exists():
            raise FileNotFoundError("path {} does not exists".format(path))
        if os.path.isdir(path):
            dir_content = os.listdir(path)
            if PjhSiirtotiedosto.SheetNames.ASIAKASTIEDOT + ".csv" in dir_content:
                sheet_cls = CsvSheetCollection
            elif PjhSiirtotiedosto.SheetNames.ASIAKASTIEDOT + ".xlsx" in dir_content:
                sheet_cls = ExcelFileSheetCollection
        else:
            _, ext = os.path.splitext(path)
            if ext == "xlsx":
                sheet_cls = ExcelSheetCollection

        return sheet_cls

    @property
    def meta(self):
        return MetaSheet(self._sheet_collection, PjhSiirtotiedosto.SheetNames.META)

    @property
    def asiakastiedot(self):
        return AsiakastiedotSheet(
            self._sheet_collection, PjhSiirtotiedosto.SheetNames.ASIAKASTIEDOT
        )

    @property
    def tyhennystapahtumat(self):
        return TyhjennystapahtumatSheet(
            self._sheet_collection, PjhSiirtotiedosto.SheetNames.TYHJENNYSTAPAHTUMAT
        )

    @property
    def tyhjennysvalit(self):
        return TyhjennysvalitSheet(
            self._sheet_collection, PjhSiirtotiedosto.SheetNames.TYHJENNYSVALIT
        )

    @property
    def keraysvalineet(self):
        return KeraysvalineSheet(
            self._sheet_collection, PjhSiirtotiedosto.SheetNames.KERAYSVALINEET
        )

    @property
    def keskeytykset(self):
        return KeskeytysSheet(
            self._sheet_collection, PjhSiirtotiedosto.SheetNames.KESKEYTYKSET
        )

    @property
    def kimpat(self):
        return KimppaSheet(self._sheet_collection, PjhSiirtotiedosto.SheetNames.KIMPAT)
