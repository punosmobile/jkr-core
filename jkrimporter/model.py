from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Union

from jkrimporter.utils.intervals import Interval

Kiinteistonumero = str
Rakennustunnus = str


@dataclass
class Osoite:
    katunimi: Optional[str] = None
    osoitenumero: Optional[str] = None
    huoneistotunnus: Optional[str] = None
    postinumero: Optional[str] = None
    postitoimipaikka: Optional[str] = None
    kunta: Optional[str] = None
    erikoisosoite: Optional[str] = None

    def osoite_rakennus(self):
        osoite = ""
        if self.katunimi:
            osoite += self.katunimi.title()
        if self.osoitenumero:
            osoite += f" {self.osoitenumero}"
        if self.postinumero:
            osoite += f", {self.postinumero}"
        if self.postitoimipaikka:
            osoite += f" {self.postitoimipaikka.title()}"

        return osoite

    def katuosoite(self):
        osoite = ""
        if self.katunimi:
            osoite += self.katunimi.title()
        if self.osoitenumero:
            osoite += f" {self.osoitenumero}"
        if self.huoneistotunnus:
            osoite += f" {self.huoneistotunnus}"

        return osoite

    def __str__(self):
        osoite = ""
        if self.katunimi:
            osoite += self.katunimi.title()
        if self.osoitenumero:
            osoite += f" {self.osoitenumero}"
        if self.huoneistotunnus:
            osoite += f" {self.huoneistotunnus}"
        if self.postinumero:
            osoite += f", {self.postinumero}"
        if self.postitoimipaikka:
            osoite += f" {self.postitoimipaikka.title()}"

        return osoite


@dataclass
class Yhteystieto:
    nimi: str
    osoite: Osoite
    ytunnus: Optional[str] = None
    henkilotunnus: Optional[str] = None


@dataclass
class Omistaja:
    nimi: str
    osoite: Osoite
    ytunnus: Optional[str] = None
    henkilotunnus: Optional[str] = None


@dataclass
class VanhinAsukas:
    nimi: str
    osoite: Osoite
    henkilotunnus: Optional[str] = None


@dataclass
class Asukas:
    nimi: str
    osoite: Osoite
    henkilotunnus: Optional[str] = None


@dataclass
class Yritys:
    nimi: str
    osoite: Osoite
    ytunnus: str


class Tunnus(NamedTuple):
    jarjestelma: str
    tunnus: str


class Jatelaji(str, Enum):
    bio = "Biojäte"                    # 1
    sekajate = "Sekajäte"              # 2
    kartonki = "Kartonki"              # 3
    lasi = "Lasi"                      # 4
    liete = "Liete"                    # 5
    mustaliete = "Musta liete"         # 6
    harmaaliete = "Harmaa liete"       # 7
    metalli = "Metalli"                # 8
    muovi = "Muovi"                    # 9
    pahvi = "Pahvi"                    # 10
    paperi = "Paperi"                  # 11
    perusmaksu = "Perusmaksu"          # 12
    energia = "Energia"                # 13
    aluekerays = "Aluekeräyspiste"     # 14
    monilokero = "Monilokero"          # 15
    muu = "Muu"                        # 99


class KeraysvalineTyyppi(str, Enum):
    PINTA = "PINTA"                    # 1
    SYVA = "SYVÄ"                      # 2
    SAOSTUSSAILIO = "Saostussäiliö"    # 3 (uudelleennimetty: oli "SAKO")
    UMPISAILIO = "Umpisäiliö"          # 4 (uudelleennimetty: oli "UMPI")
    RULLAKKO = "RULLAKKO"              # 5
    SAILIO = "SÄILIÖ"                  # 6
    PIENPUHDISTAMO = "Pienpuhdistamo"  # 7 (uudelleennimetty: oli "PIENPUHDISTAMO")
    PIKAKONTTI = "PIKAKONTTI"          # 8
    NOSTOKONTTI = "NOSTOKONTTI"        # 9
    VAIHTOLAVA = "VAIHTOLAVA"          # 10
    JATESAKKI = "JÄTESÄKKI"            # 11
    PURISTINSAILIO = "PURISTINSÄILIÖ"  # 12
    PURISTIN = "PURISTIN"              # 13
    VAIHTOLAVASAILIO = "VAIHTOLAVASÄILIÖ"  # 14
    PAALI = "PAALI"                    # 15
    MONILOKERO = "MONILOKERO"          # 16
    MUU = "Muu"                        # 99


class Keskeytys(NamedTuple):
    alkupvm: date
    loppupvm: date
    selite: Optional[str]


@dataclass
class Keraysvaline:
    maara: int
    tilavuus: Optional[int] = None
    tyyppi: Optional[KeraysvalineTyyppi] = None
    kohde_id: Optional[int] = None


class Tyhjennysvali(NamedTuple):
    alkuvko: int
    loppuvko: int
    tyhjennysvali: float
    kertaaviikossa: Optional[int] = None


@dataclass
class Tyhjennystapahtuma:
    jatelaji: Jatelaji
    alkupvm: Optional[date]
    loppupvm: Optional[date]
    tyhjennyskerrat: int
    tilavuus: Optional[int]
    massa: Optional[int] = None
    lietteentyhjennyspaiva: Optional[date] = None  # LIETE-aineisto: erillinen tyhjennyspäivä
    jatteen_kuvaus: Optional[str] = None  # LAH-449: LIETE-aineiston "Jätteen kuvaus" (keräysvälinetyyppi)


class SopimusTyyppi(str, Enum):
    tyhjennyssopimus = "Tyhjennyssopimus"
    kimppasopimus = "Kimppasopimus"
    aluekerayssopimus = "Aluekeräyssopimus"
    putkikerayssopimus = "Putkikeräyssopimus"


@dataclass
class BaseSopimus:
    sopimustyyppi: SopimusTyyppi
    jatelaji: Optional[Jatelaji]
    alkupvm: Optional[date] = None
    loppupvm: Optional[date] = None
    keskeytykset: Optional[List[Keskeytys]] = field(default_factory=list)


@dataclass
class TyhjennysSopimus(BaseSopimus):
    keraysvalineet: Optional[List[Keraysvaline]] = field(default_factory=list)
    tyhjennysvalit: Optional[List[Tyhjennysvali]] = field(default_factory=list)


@dataclass
class KimppaSopimus(TyhjennysSopimus):
    isannan_asiakasnumero: Optional[Tunnus] = None
    asiakas_on_isanta: bool = False


@dataclass
class Asiakas:
    asiakasnumero: Tunnus
    ulkoinen_asiakastieto: dict
    voimassa: Interval
    haltija: Yhteystieto
    yhteyshenkilo: Optional[Yhteystieto] = None
    kiinteistot: List[Kiinteistonumero] = field(default_factory=list)
    rakennukset: List[Rakennustunnus] = field(default_factory=list)
    sopimukset: List[Union[TyhjennysSopimus, KimppaSopimus]] = field(
        default_factory=list
    )
    tyhjennystapahtumat: List[Tyhjennystapahtuma] = field(default_factory=list)


ToimituspaikkaID = int


@dataclass
class ToimitusPaikka(Yritys):
    id: ToimituspaikkaID


@dataclass
class Toimitus:
    toimituspaikka_id: ToimituspaikkaID
    jatelaji: Jatelaji
    kayntikerrat: Optional[int]
    massa: int
    tilavuus: int


@dataclass
class JkrData:
    # The dates may be empty. This means that the total time span of the imported data
    # is unknown. Each asiakastieto may have different start and end dates, when
    # importing combined client data in a batch.
    alkupvm: Optional[date] = None
    loppupvm: Optional[date] = None
    asiakkaat: Dict[Tunnus, Asiakas] = field(default_factory=dict)
    toimituspaikat: Dict[ToimituspaikkaID, ToimitusPaikka] = field(default_factory=dict)
    toimitukset: List[Toimitus] = field(default_factory=list)


class Tapahtumalaji(Enum):
    PERUSMAKSU = "Perusmaksu"
    AKP = "AKP"
    TYHJENNYSVALI = "Tyhjennysväli"
    KESKEYTTAMINEN = "Keskeyttäminen"
    ERILLISKERAYKSESTA_POIKKEAMINEN = "Erilliskeräyksestä poikkeaminen"
    MUU = "Muu poikkeaminen"


class Paatostulos(Enum):
    KIELTEINEN = "kielteinen"
    MYONTEINEN = "myönteinen"


class AKPPoistoSyy(str, Enum):
    PIHAPIIRI = "Pihapiiri"
    MATKA = "Pitkä matka"
    EIKAYTOSSA = "Ei käytössä"


@dataclass
class Paatos:
    paatosnumero: str
    vastaanottaja: str
    paatostulos: Paatostulos
    tapahtumalaji: Tapahtumalaji
    alkupvm: date
    loppupvm: date
    prt: Rakennustunnus
    tyhjennysvali: Optional[int] = None
    akppoistosyy: Optional[AKPPoistoSyy] = None
    jatetyyppi: Optional[Jatelaji] = None
    rawdata: Optional[Dict[str, str]] = None


@dataclass
class IlmoituksenHenkilo:
    nimi: str
    osoite: Optional[str] = None
    postinumero: Optional[str] = None
    postitoimipaikka: Optional[str] = None
    rakennus: Optional[List[str]] = None  # kompostoijan prt


@dataclass
class JkrIlmoitukset:
    alkupvm: date
    loppupvm: date
    voimassa: Interval
    vastuuhenkilo: IlmoituksenHenkilo
    kompostoijat: List[IlmoituksenHenkilo]
    pienpuhdistamo_alkupwm: date
    onko_kimppa: str
    onko_liete: bool
    tiedontuottaja: str
    sijainti_prt: List[str]
    prt: List[str]
    rawdata: Optional[List[Dict[str, str]]] = None


@dataclass
class LopetusIlmoitus:
    Vastausaika: date
    nimi: str
    prt: List[str]
    rawdata: Optional[Dict[str, str]] = None


@dataclass
class ViemariIlmoitus:
    viemariverkosto_alkupvm: date
    prt: List[str]
    rawdata: Optional[List[Dict[str, str]]] = None

@dataclass
class ViemariLopetusIlmoitus:
    viemariverkosto_loppupvm: date
    prt: List[str]
    rawdata: Optional[List[Dict[str, str]]] = None
