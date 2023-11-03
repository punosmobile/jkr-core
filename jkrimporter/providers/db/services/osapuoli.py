from jkrimporter.model import Asiakas, Jatelaji

from .. import codes
from ..codes import OsapuolenlajiTyyppi, OsapuolenrooliTyyppi
from ..models import KohteenOsapuolet, Osapuoli
from ..utils import is_asoy


def create_or_update_haltija_osapuoli(
    session, kohde, asiakas: "Asiakas", update_contacts: bool
):
    """
    Luo kohteelle haltijaosapuolen
    """

    if len(asiakas.sopimukset) == 0:
        return

    sopimus = asiakas.sopimukset[0]
    if sopimus.jatelaji == Jatelaji.sekajate:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.SEKAJATE_TILAAJA]
    elif sopimus.jatelaji == Jatelaji.bio:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.BIOJATE_TILAAJA]
    elif sopimus.jatelaji == Jatelaji.lasi:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.LASI_TILAAJA]
    elif sopimus.jatelaji == Jatelaji.kartonki:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.KARTONKI_TILAAJA]
    elif sopimus.jatelaji == Jatelaji.liete:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.LIETE_TILAAJA]    
    elif sopimus.jatelaji == Jatelaji.metalli:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.METALLI_TILAAJA]        
    elif sopimus.jatelaji == Jatelaji.muovi:
        asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.MUOVI_TILAAJA]
    else:
        return

    # Filter osapuoli by the same tiedontuottaja. This way, we don't
    # override data coming from other tiedontuottajat, including DVV.
    tiedontuottaja = asiakas.asiakasnumero.jarjestelma
    # this is any asiakas from the same source
    db_haltijat = [
        kohteen_osapuoli.osapuoli
        for kohteen_osapuoli in kohde.kohteen_osapuolet_collection
        if kohteen_osapuoli.osapuolenrooli == asiakasrooli and
        kohteen_osapuoli.osapuoli.tiedontuottaja_tunnus == tiedontuottaja
    ]

    # this is asiakas with the same name and address
    exists = any(
        db_haltija.nimi == asiakas.haltija.nimi
        and db_haltija.katuosoite == str(asiakas.haltija.osoite)
        for db_haltija in db_haltijat
    )
    if not db_haltijat or (update_contacts and not exists):
        print("Haltija changed or not found in db, creating new haltija!")
        # Haltija has changed. We must create a new osapuoli. The old
        # haltija is still valid for the old data, so we don't want to
        # delete them.
        jatteenhaltija = Osapuoli(
            nimi=asiakas.haltija.nimi,
            katuosoite=str(asiakas.haltija.osoite),
            postinumero=asiakas.haltija.osoite.postinumero,
            postitoimipaikka=asiakas.haltija.osoite.postitoimipaikka,
            ytunnus=asiakas.haltija.ytunnus,
            tiedontuottaja_tunnus=asiakas.asiakasnumero.jarjestelma
        )
        if is_asoy(asiakas.haltija.nimi):
            jatteenhaltija.osapuolenlaji = codes.osapuolenlajit[
                OsapuolenlajiTyyppi.ASOY
            ]

        kohteen_osapuoli = KohteenOsapuolet(
            kohde=kohde, osapuoli=jatteenhaltija, osapuolenrooli=asiakasrooli
        )

        session.add(kohteen_osapuoli)
