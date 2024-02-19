from jkrimporter.model import Asiakas, Jatelaji, SopimusTyyppi, JkrIlmoitukset

from .. import codes
from ..codes import OsapuolenlajiTyyppi, OsapuolenrooliTyyppi
from ..models import KohteenOsapuolet, Osapuoli, Kohde
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
    session, kohde, ilmoitus: "JkrIlmoitukset",  # update_contacts: bool, Lisää kohdentamisen jälkeen kohde.
):
    """
    Luo kohteelle kompostin yhteyshenkilo
    """
    # This can be removed after kohdennus code is added.
    kohde = session.query(Kohde).filter_by(id=kohde).first()

    asiakasrooli = codes.osapuolenroolit[OsapuolenrooliTyyppi.KOMPOSTI_YHTEYSHENKILO]
    existing_osapuoli_entries = session.query(KohteenOsapuolet).filter(
            KohteenOsapuolet.osapuoli.has(
                tiedontuottaja_tunnus="ilmoitus",
                nimi=ilmoitus.vastuuhenkilo.nimi,
                katuosoite=str(ilmoitus.vastuuhenkilo.osoite),
            ),
            KohteenOsapuolet.osapuolenrooli == asiakasrooli,
        ).all()

    # Delete existing osapuoli entries
    for existing_entry in existing_osapuoli_entries:
        session.delete(existing_entry)

    # Create new osapuoli entry
    kompostinyhteyshenkilo = Osapuoli(
        nimi=ilmoitus.vastuuhenkilo.nimi,
        katuosoite=str(ilmoitus.vastuuhenkilo.osoite),
        postinumero=ilmoitus.vastuuhenkilo.postinumero,
        postitoimipaikka=ilmoitus.vastuuhenkilo.postitoimipaikka,
        tiedontuottaja_tunnus=ilmoitus.tiedontuottaja,
    )

    if is_asoy(ilmoitus.vastuuhenkilo.nimi):
        kompostinyhteyshenkilo.osapuolenlaji = codes.osapuolenlajit[OsapuolenlajiTyyppi.ASOY]

    #Select kohde that has the id of whats passed to the function as "kohde"
    kohteen_osapuoli = KohteenOsapuolet(
        kohde=kohde, osapuoli=kompostinyhteyshenkilo, osapuolenrooli=asiakasrooli
    )

    session.add(kohteen_osapuoli)
    print(kohteen_osapuoli)
    # Commit changes to the database
    session.commit()

    return kohteen_osapuoli
