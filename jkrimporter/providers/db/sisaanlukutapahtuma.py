import os
import sys
import traceback
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from jkrimporter.providers.db.database import engine

# Thread-local kerääjä yhteenvetotiedoille
_local = threading.local()


def _build_komento_string(args=None):
    """Rakentaa komentorivin sys.argv:sta tai annetuista argumenteista.

    Jos sisaanluku_komento() on asettanut korvaavan komennon (esim. batch_import
    ajaa alikomentoja funktiokutsuina), käytetään sitä sys.argv:n sijaan.
    """
    if args is not None:
        return " ".join(str(a) for a in args)
    override = getattr(_local, "komento_override", None)
    if override:
        return override
    return " ".join(sys.argv)


@contextmanager
def sisaanluku_komento(komento: str):
    """Asettaa tuontilokiin kirjattavan komennon lohkon ajaksi.

    batch_import kutsuu alikomentoja suoraan Python-funktioina, jolloin sys.argv
    on koko batch-komento ja jokainen tiedosto kirjautuisi samalla komennolla.

    Käyttö:
        with sisaanluku_komento("jkr import_paatokset polku.xlsx"):
            import_paatokset(polku)
    """
    edellinen = getattr(_local, "komento_override", None)
    _local.komento_override = komento
    try:
        yield
    finally:
        _local.komento_override = edellinen


def lisaa_lisatieto(msg: str):
    """Lisää yhteenvetorivi sisäänlukutapahtuman lisätietoihin.

    Kutsutaan niissä kohdissa koodissa, joissa halutaan kirjata
    oleellinen koostetieto (esim. kohdentumattomien-määrät).
    Tulostaa viestin myös konsolille.

    Käyttö:
        lisaa_lisatieto(f"Kohdentumatta: {len(kohdentumattomat)} kpl")
    """
    print(msg)
    kooste = getattr(_local, "kooste", None)
    if kooste is not None:
        kooste.append(msg)


def kirjaa_sisaanluku_alku(session, komento: str) -> int:
    """Kirjaa sisäänlukutapahtuman alun ja palauttaa tapahtuman id:n."""
    result = session.execute(
        text(
            "INSERT INTO jkr.sisaanluku_tapahtuma (komento, alkuaika, status) "
            "VALUES (:komento, :alkuaika, 'käynnissä') RETURNING id"
        ),
        {"komento": komento, "alkuaika": datetime.now(timezone.utc)},
    )
    tapahtuma_id = result.scalar()
    session.commit()
    return tapahtuma_id


def kirjaa_sisaanluku_loppu(session, tapahtuma_id: int, status: str = "valmis", lisatiedot: str = None):
    """Päivittää sisäänlukutapahtuman loppuajan ja statuksen."""
    session.execute(
        text(
            "UPDATE jkr.sisaanluku_tapahtuma "
            "SET loppuaika = :loppuaika, status = :status, lisatiedot = :lisatiedot "
            "WHERE id = :id"
        ),
        {
            "loppuaika": datetime.now(timezone.utc),
            "status": status,
            "lisatiedot": lisatiedot,
            "id": tapahtuma_id,
        },
    )
    session.commit()


@contextmanager
def sisaanlukutapahtuma(komento: str = None):
    """Context manager joka kirjaa sisäänlukutapahtuman alun ja lopun.
    Kerää lisätiedot lisaa_lisatieto()-kutsuista.

    Käyttö:
        with sisaanlukutapahtuma():
            # ... sisäänlukukoodi ...
            lisaa_lisatieto("Lisätty: 45 kohdetta")
            lisaa_lisatieto("Kohdentumatta: 3 kpl")

    Sisäkkäinen kutsu (esim. import_and_create_kohteet → create_dvv_kohteet)
    ei luo uutta riviä: lisätiedot ja mahdollinen virhe kirjautuvat ulomman
    tapahtuman riville.
    """
    aktiivinen_id = getattr(_local, "tapahtuma_id", None)
    if aktiivinen_id is not None:
        yield aktiivinen_id
        return

    if komento is None:
        komento = _build_komento_string()

    # Alustetaan koosteen kerääjä. API asettaa JKR_RUNNER-muuttujaan ajon
    # käynnistäjän; komentoriviltä ajettaessa sitä ei ole.
    _local.kooste = []
    runner = os.environ.get("JKR_RUNNER")
    if runner:
        _local.kooste.append(f"runner={runner}")

    with Session(engine) as session:
        tapahtuma_id = kirjaa_sisaanluku_alku(session, komento)
        _local.tapahtuma_id = tapahtuma_id
        try:
            yield tapahtuma_id
            lisatiedot = "\n".join(_local.kooste) if _local.kooste else None
            kirjaa_sisaanluku_loppu(
                session, tapahtuma_id, status="valmis", lisatiedot=lisatiedot
            )
        except Exception as e:
            kooste_teksti = "\n".join(_local.kooste) if _local.kooste else ""
            virheviesti = traceback.format_exc()
            lisatiedot = kooste_teksti + "\n--- virhe ---\n" + virheviesti if kooste_teksti else virheviesti
            kirjaa_sisaanluku_loppu(
                session, tapahtuma_id, status="virhe", lisatiedot=lisatiedot
            )
            raise
        finally:
            _local.kooste = None
            _local.tapahtuma_id = None
