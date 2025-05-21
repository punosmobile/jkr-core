from sqlalchemy import select, desc
from sqlalchemy.exc import NoResultFound
from datetime import datetime
from jkrimporter.model import Asiakas, Jatelaji, JkrIlmoitukset, SopimusTyyppi
from jkrimporter.providers.db.models import (
    Kohde,
    KohteenOsapuolet,
    Osapuoli,
    RakennuksenVanhimmat,
    DVVPoimintaPvm
)
from .. import codes
from ..codes import OsapuolenlajiTyyppi, OsapuolenrooliTyyppi
from ..utils import is_asoy



def create_or_update_haltija_osapuoli(
    session, kohde, asiakas: "Asiakas", update_contacts: bool
):
    """
    Luo kohteelle haltijaosapuolet jätelajeittain
    """

    # Dictionary containing unique entries based on nimi, osoite and jatelaji.
    unique_entries = {}

    # Iterate all asiakas.sopimukset.
    for sopimus in asiakas.sopimukset:
        key = (asiakas.haltija.nimi, str(asiakas.haltija.osoite), sopimus.jatelaji)

        if key not in unique_entries:
            unique_entries[key] = sopimus
        elif sopimus.sopimustyyppi == SopimusTyyppi.kimppasopimus:
            # Prefer kimppasopimus.
            unique_entries[key] = sopimus

    for sopimus in unique_entries.values():
        if sopimus.sopimustyyppi == SopimusTyyppi.kimppasopimus:
            if sopimus.asiakas_on_isanta:
                if sopimus.jatelaji == Jatelaji.sekajate:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.SEKAJATE_KIMPPAISANTA]
                elif sopimus.jatelaji == Jatelaji.bio:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.BIOJATE_KIMPPAISANTA]
                elif sopimus.jatelaji == Jatelaji.lasi:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.LASI_KIMPPAISANTA]
                elif sopimus.jatelaji == Jatelaji.kartonki:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.KARTONKI_KIMPPAISANTA]
                elif sopimus.jatelaji == Jatelaji.metalli:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.METALLI_KIMPPAISANTA]
                elif sopimus.jatelaji == Jatelaji.muovi:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.MUOVI_KIMPPAISANTA]
                else:
                    print("Skipping sopimus with unknown jätelaji " + sopimus.jatelaji + " in kimppasopimus")
                    continue
            else:
                if sopimus.jatelaji == Jatelaji.sekajate:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.SEKAJATE_KIMPPAOSAKAS]
                elif sopimus.jatelaji == Jatelaji.bio:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.BIOJATE_KIMPPAOSAKAS]
                elif sopimus.jatelaji == Jatelaji.lasi:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.LASI_KIMPPAOSAKAS]
                elif sopimus.jatelaji == Jatelaji.kartonki:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.KARTONKI_KIMPPAOSAKAS]
                elif sopimus.jatelaji == Jatelaji.metalli:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.METALLI_KIMPPAOSAKAS]
                elif sopimus.jatelaji == Jatelaji.muovi:
                    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.MUOVI_KIMPPAOSAKAS]
                else:
                    print("Skipping sopimus with unknown jätelaji " + sopimus.jatelaji + " in kimppasopimus")
                    continue
        else:
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
                print("Skipping sopimus with unknown jätelaji " + sopimus.jatelaji + " in sopimus")
                continue

        # Filter osapuoli by the same tiedontuottaja. This way, we don't
        # override data coming from other tiedontuottajat, including DVV.
        tiedontuottaja = asiakas.asiakasnumero.jarjestelma

        # Query existing osapuoli entries for the given tiedontuottaja and asiakasrooli
        existing_osapuoli_entries = session.query(KohteenOsapuolet).filter(
            KohteenOsapuolet.osapuoli.has(
                tiedontuottaja_tunnus=tiedontuottaja,
                nimi=asiakas.haltija.nimi,
                katuosoite=str(asiakas.haltija.osoite),
            ),
            KohteenOsapuolet.osapuolenrooli == asiakasrooli,
        ).all()

        # Delete existing osapuoli entries
        for existing_entry in existing_osapuoli_entries:
            session.delete(existing_entry)

        # Create new osapuoli entry
        jatteenhaltija = Osapuoli(
            nimi=asiakas.haltija.nimi,
            katuosoite=str(asiakas.haltija.osoite),
            postinumero=asiakas.haltija.osoite.postinumero,
            postitoimipaikka=asiakas.haltija.osoite.postitoimipaikka,
            ytunnus=asiakas.haltija.ytunnus,
            tiedontuottaja_tunnus=asiakas.asiakasnumero.jarjestelma,
        )

        if is_asoy(asiakas.haltija.nimi):
            jatteenhaltija.osapuolenlaji = codes.osapuolenlajit[OsapuolenlajiTyyppi.ASOY]

        kohteen_osapuoli = KohteenOsapuolet(
            kohde=kohde, osapuoli=jatteenhaltija, osapuolenrooli=asiakasrooli
        )

        session.add(kohteen_osapuoli)

    # Commit changes to the database
    session.commit()


def create_or_update_komposti_yhteyshenkilo(
    session, kohde: Kohde, ilmoitus: "JkrIlmoitukset",
):
    """
    Luo kohteelle kompostin yhteyshenkilo
    """

    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.KOMPOSTI_YHTEYSHENKILO]
    # Look for existing osapuoli.
    existing_osapuoli_entries = session.query(Osapuoli).join(KohteenOsapuolet).filter(
        Osapuoli.tiedontuottaja_tunnus == "ilmoitus",
        Osapuoli.nimi == ilmoitus.vastuuhenkilo.nimi,
        Osapuoli.katuosoite == str(ilmoitus.vastuuhenkilo.osoite),
        KohteenOsapuolet.osapuolenrooli == asiakasrooli
    ).first()

    if existing_osapuoli_entries:
        return existing_osapuoli_entries

    # Create new osapuoli entry
    print("Creating new osapuoli...")
    kompostin_yhteyshenkilo = Osapuoli(
        nimi=ilmoitus.vastuuhenkilo.nimi,
        katuosoite=str(ilmoitus.vastuuhenkilo.osoite),
        postinumero=ilmoitus.vastuuhenkilo.postinumero,
        postitoimipaikka=ilmoitus.vastuuhenkilo.postitoimipaikka,
        tiedontuottaja_tunnus=ilmoitus.tiedontuottaja,
    )

    if is_asoy(ilmoitus.vastuuhenkilo.nimi):
        kompostin_yhteyshenkilo.osapuolenlaji = (
            codes.osapuolenlajit[OsapuolenlajiTyyppi.ASOY]
        )

    kohteen_osapuoli = KohteenOsapuolet(
        kohde=kohde, osapuoli=kompostin_yhteyshenkilo, osapuolenrooli=asiakasrooli
    )
    session.add(kompostin_yhteyshenkilo, kohteen_osapuoli)

    # Commit changes to the database
    session.commit()

    return kompostin_yhteyshenkilo

def extract_identifier(rakennuksen_vanhin):
    if rakennuksen_vanhin.osapuoli:
        return rakennuksen_vanhin.osapuoli.henkilotunnus or rakennuksen_vanhin.osapuoli.nimi
    return None

def check_building_inhabitant_changes(
    session, rakennus_id: int, poimintapvm: datetime.date
) -> bool:
    """
    Hae rakennuksen nykyiset ja menneet asukkaat sekä tarkista onko niissä yhtäläisyyksiä palauttaa true jos asukkaissa on päällekkäisyyksiä
    tai jos uusi asukas on aloittanut ennen edellistä poiminta päivämäärää
    """

    # Haetaan rakennuksesta poistuneet asukkaat (loppupvm IS NOT NULL)
    poistuneet_query = (
        select(RakennuksenVanhimmat)
        .join(Osapuoli)
        .where(
            RakennuksenVanhimmat.rakennus_id == rakennus_id,
            RakennuksenVanhimmat.loppupvm.isnot(None)
        )
    )
    poistuneet = session.execute(poistuneet_query).scalars().all()

    # Haetaan yhä rakennuksessa asuvat (loppupvm IS NULL)
    asuvat_query = (
        select(RakennuksenVanhimmat)
        .join(Osapuoli)
        .where(
            RakennuksenVanhimmat.rakennus_id == rakennus_id,
            RakennuksenVanhimmat.loppupvm.is_(None)
        )
    )
    asuvat = session.execute(asuvat_query).scalars().all()

    # Luodaan setti henkilötunnuksista
    poistuneet_tunnisteet = set()
    for rv in poistuneet:
        tunniste = extract_identifier(rv)
        if tunniste:
            poistuneet_tunnisteet.add(tunniste)

    asuvat_tunnisteet = set()
    for rv in asuvat:
        tunniste = extract_identifier(rv)
        if tunniste:
            asuvat_tunnisteet.add(tunniste)

    # Tarkistetaan, onko yksikin sama
    onko_yha_asuva_poistunut = bool(poistuneet_tunnisteet & asuvat_tunnisteet)

    # Jos asukkaissa ei ole yhtäläisyyksiä, tarkistetaan onko joku asukkaista muuttanut taloon ennen edellistä poimintapäivää.
    # Tämä voi tapahtua esimerkiksi kahden henkilön asuessa samassa taloudessa josta toinen muuttaa pois
    if  not onko_yha_asuva_poistunut:
        vanha_poiminta_query = (
            select(DVVPoimintaPvm)
            .order_by(desc(DVVPoimintaPvm.poimintapvm))
        )

        try:
            dvv_poiminta = session.execute(vanha_poiminta_query).scalar_one()
        except NoResultFound:
            dvv_poiminta = None

        print(f"DVV_PoimintaPVM: {dvv_poiminta}")

        for asukas in asuvat:
            if asukas.alkupvm < (dvv_poiminta or poimintapvm):
                onko_yha_asuva_poistunut = True

    return onko_yha_asuva_poistunut
