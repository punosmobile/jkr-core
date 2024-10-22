import warnings

from geoalchemy2 import Geometry  # noqa: F401, must be imported for Geometry reflect
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship

from jkrimporter.providers.db.database import engine

Base = automap_base()

def name_for_scalar(base, local_cls, referred_cls, constraint):
    """Returns a property name for the many side of a one-to-many relationship

    This is needed to make double relationships between tables to work
    """
    if local_cls.__name__ == "sopimus" and referred_cls.__name__ == "kohde":
        if constraint.name == "kohde_fk":
            scalar_name = "kohde"
            return scalar_name
        elif constraint.name == "kimppaisanta_kohde_fk":
            scalar_name = "kimppaisanta_kohde"
            return scalar_name

    return referred_cls.__name__.lower()

def name_for_collection(base, local_cls, referred_cls, constraint):
    """Returns a property name for the one side of a one-to-many relationship

    This is needed to make double relationships between tables to work
    """
    collection_name = referred_cls.__name__.lower() + "_collection"

    if local_cls.__name__ in ("kohde", "sopimus") and referred_cls.__name__ in (
        "kohde",
        "sopimus",
    ):
        if constraint.name == "kohde_fk":
            collection_name = "sopimus_collection"
        elif constraint.name == "kimppaisanta_kohde_fk":
            collection_name = "kimppasopimus_collection"
    # this is needed so that kohde_collection won't map to rakennusehdokkaat.
    # with multiple many-to-many relationships, the mapping order may be random
    # and the second relationship will not get a collection at all.
    if local_cls.__name__ in ("kohde", "rakennus") and referred_cls.__name__ in (
        "kohde",
        "rakennus",
    ):
        if constraint.name == "kohde_fk":
            collection_name = "rakennus_collection"
        elif constraint.name == "ehdokaskohde_fk":
            collection_name = "ehdokasrakennus_collection"
        if constraint.name == "rakennus_fk":
            collection_name = "kohde_collection"
        elif constraint.name == "ehdokasrakennus_fk":
            collection_name = "ehdokaskohde_collection"
    return collection_name

# Define any association tables that need to be directly insertable.
# Sqlalchemy only generates them automatically if they have extra columns.
class KohteenRakennukset(Base):
    __tablename__ = "kohteen_rakennukset"
    __table_args__ = {"schema": "jkr"}
    rakennus_id = Column(ForeignKey("jkr.rakennus.id"), primary_key=True)
    kohde_id = Column(ForeignKey("jkr.kohde.id"), primary_key=True)

class KompostorinKohteet(Base):
    __tablename__ = "kompostorin_kohteet"
    __table_args__ = {"schema": "jkr"}
    kompostori_id = Column(ForeignKey("jkr.kompostori.id"), primary_key=True)
    kohde_id = Column(ForeignKey("jkr.kohde.id"), primary_key=True)

# Määritellään Rakennus-luokka ennen automap_base valmistelua
# jotta voidaan lisätä uusi kenttä
class Rakennus(Base):
    __tablename__ = 'rakennus'
    __table_args__ = {'schema': 'jkr'}
    
    # rakennusluokka_2018 kenttä lisätään tässä
    rakennusluokka_2018 = Column(String(4))

# Reflect database with warnings filtered
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="Skipped unsupported reflection of expression-based index idx_osoite_lower_katu_fi",
    )
    Base.prepare(
        engine,
        name_for_scalar_relationship=name_for_scalar,
        name_for_collection_relationship=name_for_collection,
        reflect=True,
        reflection_options={"schema": "jkr"},
    )

# Get references to all tables through the generated Base classes
AKPPoistoSyy = Base.classes.akppoistosyy
Jatetyyppi = Base.classes.jatetyyppi
Jatteenkuljetusalue = Base.classes.jatteenkuljetusalue
Katu = Base.classes.katu
Keraysvaline = Base.classes.keraysvaline
Keraysvalinetyyppi = Base.classes.keraysvalinetyyppi
Keskeytys = Base.classes.keskeytys
Kiinteisto = Base.classes.kiinteisto
Kohde = Base.classes.kohde
Kohdetyyppi = Base.classes.kohdetyyppi
KohteenOsapuolet = Base.classes.kohteen_osapuolet
Kompostori = Base.classes.kompostori
Kuljetus = Base.classes.kuljetus
Kunta = Base.classes.kunta
Osapuolenlaji = Base.classes.osapuolenlaji
Osapuoli = Base.classes.osapuoli
Osapuolenrooli = Base.classes.osapuolenrooli
Osoite = Base.classes.osoite
Paatostulos = Base.classes.paatostulos
Pohjavesialue = Base.classes.pohjavesialue
Posti = Base.classes.posti
Rakennuksenkayttotarkoitus = Base.classes.rakennuksenkayttotarkoitus
Rakennuksenolotila = Base.classes.rakennuksenolotila
RakennuksenOmistajat = Base.classes.rakennuksen_omistajat
RakennuksenVanhimmat = Base.classes.rakennuksen_vanhimmat
# Rakennus already defined above
Sopimus = Base.classes.sopimus
SopimusTyyppi = Base.classes.sopimustyyppi
Taajama = Base.classes.taajama
Tapahtumalaji = Base.classes.tapahtumalaji
Tiedontuottaja = Base.classes.tiedontuottaja
Tyhjennysvali = Base.classes.tyhjennysvali
UlkoinenAsiakastieto = Base.classes.ulkoinen_asiakastieto
Velvoite = Base.classes.velvoite
Velvoitemalli = Base.classes.velvoitemalli
Viranomaispaatokset = Base.classes.viranomaispaatokset

# Let SQLAlchemy handle all relationships through reflection
# Remove redundant relationship definitions that were causing warnings

__all__ = [
    "AKPPoistoSyy",
    "Jatetyyppi",
    "Jatteenkuljetusalue", 
    "Katu",
    "Keraysvaline",
    "Keskeytys",
    "Kiinteisto",
    "Kohde",
    "Kohdetyyppi",
    "KohteenOsapuolet",
    "KohteenRakennukset",
    "KompostorinKohteet",
    "Kuljetus",
    "Kunta",
    "Osapuolenlaji",
    "Osapuoli", 
    "Osapuolenrooli",
    "Osoite",
    "Paatostulos",
    "Pohjavesialue",
    "Posti",
    "Rakennuksenkayttotarkoitus",
    "Rakennuksenolotila",
    "RakennuksenOmistajat",
    "RakennuksenVanhimmat", 
    "Rakennus",
    "Sopimus",
    "SopimusTyyppi",
    "Taajama",
    "Tapahtumalaji",
    "Tiedontuottaja",
    "Tyhjennysvali",
    "UlkoinenAsiakastieto",
    "Velvoite",
    "Velvoitemalli",
    "Viranomaispaatokset",
]