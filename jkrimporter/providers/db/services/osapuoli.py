from typing import TYPE_CHECKING

from jkrimporter.model import Asiakas

from .. import codes
from ..codes import OsapuolenlajiTyyppi, OsapuolenrooliTyyppi
from ..models import KohteenOsapuolet, Osapuoli
from ..utils import is_asoy

if TYPE_CHECKING:
    from jkrimporter.model import Asiakas as JkrAsiakas


def create_or_update_haltija_osapuoli(session, kohde, asiakas: "Asiakas"):
    """
    Luo kohteelle haltijaosapuolen

    TODO: päivitä haltijan/asiakakkaan yhteystiedot (ml. poistaminen) #26
    """

    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.ASIAKAS]
    db_haltijat = (
        kohteen_osapuoli.osapuoli
        for kohteen_osapuoli in kohde.kohteen_osapuolet_collection
        if kohteen_osapuoli.osapuolenrooli == asiakasrooli
    )

    exists = any(
        db_haltija.nimi == asiakas.haltija.nimi
        and db_haltija.katuosoite == asiakas.haltija.osoite.katunimi
        for db_haltija in db_haltijat
    )
    if not exists:
        jatteenhaltija = Osapuoli(
            nimi=asiakas.haltija.nimi,
            katuosoite=asiakas.haltija.osoite.katunimi,
            postinumero=asiakas.haltija.osoite.postinumero,
            postitoimipaikka=asiakas.haltija.osoite.postitoimipaikka,
            ytunnus=asiakas.haltija.ytunnus,
        )
        if is_asoy(asiakas.haltija.nimi):
            jatteenhaltija.osapuolenlaji = codes.osapuolenlajit[
                OsapuolenlajiTyyppi.ASOY
            ]

        kohteen_osapuoli = KohteenOsapuolet(
            kohde=kohde, osapuoli=jatteenhaltija, osapuolenrooli=asiakasrooli
        )

        session.add(kohteen_osapuoli)


def create_or_update_yhteystieto_osapuoli(session, kohde, asiakas: "JkrAsiakas"):
    yhteystietorooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.YHTEYSTIETO]

    db_yhteyshenkilo = next(
        (
            kohteen_osapuoli.osapuoli
            for kohteen_osapuoli in kohde.kohteen_osapuolet_collection
            if kohteen_osapuoli.osapuolenrooli == yhteystietorooli
        ),
        None,
    )
    if db_yhteyshenkilo:
        if (
            db_yhteyshenkilo.nimi != asiakas.yhteyshenkilo.nimi
            or db_yhteyshenkilo.katuosoite != asiakas.yhteyshenkilo.osoite.katunimi
            or db_yhteyshenkilo.postinumero != asiakas.yhteyshenkilo.osoite.postinumero
            or db_yhteyshenkilo.postitoimipaikka
            != asiakas.yhteyshenkilo.osoite.postitoimipaikka
            or db_yhteyshenkilo.ytunnus != asiakas.yhteyshenkilo.ytunnus
        ):
            db_yhteyshenkilo.nimi = asiakas.yhteyshenkilo.nimi
            db_yhteyshenkilo.katuosoite = asiakas.yhteyshenkilo.osoite.katunimi
            db_yhteyshenkilo.postinumero = asiakas.yhteyshenkilo.osoite.postinumero
            db_yhteyshenkilo.postitoimipaikka = (
                asiakas.yhteyshenkilo.osoite.postitoimipaikka
            )
            db_yhteyshenkilo.ytunnus = asiakas.yhteyshenkilo.ytunnus
    else:
        yhteyshenkilo = Osapuoli(
            nimi=asiakas.yhteyshenkilo.nimi,
            katuosoite=asiakas.yhteyshenkilo.osoite.katunimi,
            postinumero=asiakas.yhteyshenkilo.osoite.postinumero,
            postitoimipaikka=asiakas.yhteyshenkilo.osoite.postitoimipaikka,
            ytunnus=asiakas.yhteyshenkilo.ytunnus,
        )

        kohteen_osapuoli = KohteenOsapuolet(
            kohde=kohde, osapuoli=yhteyshenkilo, osapuolenrooli=yhteystietorooli
        )
        session.add(kohteen_osapuoli)
