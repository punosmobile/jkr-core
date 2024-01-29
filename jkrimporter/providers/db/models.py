import warnings

from geoalchemy2 import Geometry  # noqa: F401, must be imported for Geometry reflect
from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.ext.automap import automap_base, generate_relationship
from sqlalchemy.orm import backref, relationship

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


# def generate_relationship(
#     base, direction, return_fn, attrname, local_cls, referred_cls, **kw
# ):
#     if local_cls.__name__.lower() == "rakennus":
#         print(
#             direction,
#             return_fn,
#             attrname,
#             local_cls.__name__,
#             referred_cls.__name__,
#             kw,
#         )
#         print("")
#     if return_fn is backref:
#         return return_fn(attrname, **kw)
#     elif return_fn is relationship:
#         return return_fn(referred_cls, **kw)
#     else:
#         raise TypeError("Unknown relationship function: %s" % return_fn)


# Define any association tables that need to be directly insertable.
# Sqlalchemy only generates them automatically if they have extra columns.
class KohteenRakennukset(Base):
    __tablename__ = "kohteen_rakennukset"
    __table_args__ = {"schema": "jkr"}
    rakennus_id = Column(ForeignKey("jkr.rakennus.id"), primary_key=True)
    kohde_id = Column(ForeignKey("jkr.kohde.id"), primary_key=True)


# Rest of the tables can be defined automatically
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="Skipped unsupported reflection of expression-based index idx_osoite_lower_katu_fi",
    )
    # warnings.simplefilter("ignore", category=sa_exc.SAWarning)

    Base.prepare(
        engine,
        name_for_scalar_relationship=name_for_scalar,
        name_for_collection_relationship=name_for_collection,
        # generate_relationship=generate_relationship,
        reflect=True,
        reflection_options={"schema": "jkr"},
    )


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
RakennuksenOmistajat = Base.classes.rakennuksen_omistajat  # has extra fields
RakennuksenVanhimmat = Base.classes.rakennuksen_vanhimmat  # has extra fields
Rakennus = Base.classes.rakennus
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


# Add associations to association tables with extra fields.
# Vanhimmat:
Rakennus.vanhimmat = relationship(RakennuksenVanhimmat, back_populates="rakennus")
RakennuksenVanhimmat.rakennus = relationship(Rakennus, back_populates="vanhimmat")
Osapuoli.kotirakennukset = relationship(RakennuksenVanhimmat, back_populates="osapuoli")
RakennuksenVanhimmat.osapuoli = relationship(Osapuoli, back_populates="kotirakennukset")

# Omistajat:
Rakennus.omistajat = relationship(RakennuksenOmistajat, back_populates="rakennus")
RakennuksenOmistajat.rakennus = relationship(Rakennus, back_populates="omistajat")
Osapuoli.omistetut_rakennukset = relationship(
    RakennuksenOmistajat, back_populates="osapuoli"
)
RakennuksenOmistajat.osapuoli = relationship(
    Osapuoli, back_populates="omistetut_rakennukset"
)

if __name__ == "__main__":
    ...
    """
    from sqlalchemy import func as sqlalchemyFunc
    from sqlalchemy import select

    print("Sopimus:", [field for field in dir(Sopimus) if not field.startswith("_")])
    print("Kohde:", [field for field in dir(Kohde) if not field.startswith("_")])
    print("Rakennus:", [field for field in dir(Rakennus) if not field.startswith("_")])

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        s = select(Rakennus).limit(1)
        r = session.execute(s).scalar_one()
        print(r.kohde_collection)

        k = session.get(Kohde, 9038)

        print(f"sopimukset: {k.sopimus_collection}")
        for s in k.sopimus_collection:
            print(dir(s))
        print(f"kimpat: {k.kimppasopimus_collection}")
    """

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
    "Taajama",
    "Tapahtumalaji",
    "Tiedontuottaja",
    "Tyhjennysvali",
    "UlkoinenAsiakastieto",
    "Velvoite",
    "Velvoitemalli",
    "Viranomaispaatokset",
]
