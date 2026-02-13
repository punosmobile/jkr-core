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
    """Rakentaa komentorivin sys.argv:sta tai annetuista argumenteista."""
    if args is not None:
        return " ".join(str(a) for a in args)
    return " ".join(sys.argv)


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
    """
    if komento is None:
        komento = _build_komento_string()

    # Alustetaan koosteen kerääjä
    _local.kooste = []

    with Session(engine) as session:
        tapahtuma_id = kirjaa_sisaanluku_alku(session, komento)
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
