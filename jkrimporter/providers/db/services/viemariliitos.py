import logging
from datetime import date
from typing import List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import Session


def find_existing_viemariliitos(
    session: Session,
    kohde_id: int,
    prt: str,
    alkupvm: date
) -> bool:
    """
    Tarkistaa onko sama viemäriliitos jo olemassa.
    
    Määrittelyn mukaan: Jos kohteella on jo sama tieto, sitä ei viedä päälle.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        prt: Pysyvä rakennustunnus
        alkupvm: Alkupäivämäärä
        
    Returns:
        True jos löytyy, False muuten
    """
    from jkrimporter.providers.db.models import Base

    # Haetaan Kaivotieto-taulu reflektoimalla
    Viemariliitos = Base.classes.viemari_liitos

    query = select(Viemariliitos.id).where(
        and_(
            Viemariliitos.kohde_id == kohde_id,
            Viemariliitos.rakennus_prt == prt,
            Viemariliitos.viemariverkosto_alkupvm == alkupvm
        )
    )

    result = session.execute(query).scalars().first()
    return result is not None



def insert_viemariliitos(
    session: Session,
    kohde_id: int,
    alkupvm: date,
    prt: str,
) -> Tuple[bool, str]:
    """
    Lisää uuden viemäriverkostoliitoksen kohteelle.
    
    Määrittelyn mukaan: Jos kohteella on jo sama tieto, sitä ei viedä päälle.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        alkupvm: Alkupäivämäärä
        prt: Pysyvä rakennustunnus
        
    Returns:
        Tuple (onnistui: bool, viesti: str)
    """
    from jkrimporter.providers.db.models import Base

    Viemariliitos = Base.classes.viemari_liitos

    # Tarkista onko jo olemassa
    if find_existing_viemariliitos(session, kohde_id, prt, alkupvm):
        return False, f"Viemäriliitos {prt} alkupvm {alkupvm} on jo olemassa kohteella {kohde_id}"

    # Luo uusi viemariliitos
    viemariliitos = Viemariliitos(
        kohde_id=kohde_id,
        viemariverkosto_alkupvm=alkupvm,
        rakennus_prt=prt,
    )

    session.add(viemariliitos)

    return True, f"Lisätty viemäriliitos {viemariliitos.viemariverkosto_alkupvm} {viemariliitos.rakennus_prt} kohteelle {kohde_id}"

def update_viemariliitos_loppupvm(
    session: Session,
    kohde_id: int,
    loppupvm: date
) -> Tuple[int, str]:
    """
    Päivittää viemäriliitoksien loppupäivämäärän.
    
    Määrittelyn mukaan: Lopetus edellyttää että samalla kohteella on vastaava tieto alkanut.
    Mikäli kohteella on useita samoja alkaneita viemäriliitoksia, lopetuspäivämäärä lopettaa 
    kaikki liitokset.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        loppupvm: Loppupäivämäärä
        
    Returns:
        Tuple (päivitettyjen määrä: int, viesti: str)
    """
    from jkrimporter.providers.db.models import Base

    Viemariliitos = Base.classes.viemari_liitos

    # Etsi kaikki aktiiviset viemäriliitokset kohteessa
    query = select(Viemariliitos).where(
        and_(
            Viemariliitos.kohde_id == kohde_id,
            Viemariliitos.viemariverkosto_loppupvm.is_(None)  # Vain aktiiviset
        )
    )

    viemariliitokset = session.execute(query).scalars().all()

    if not viemariliitokset:
        return 0, f"Ei löytynyt aktiivista viemariliitosta kohteelta {kohde_id}"

    # Päivitä loppupvm kaikille
    updated_count = 0
    for viemariliitos in viemariliitokset:
        viemariliitos.viemariverkosto_loppupvm = loppupvm
        updated_count += 1

    return updated_count, f"Päivitetty {updated_count} viemäriliitoksen loppupvm kohteelle {kohde_id}"


def get_viemariliitokset_for_kohde(
    session: Session,
    kohde_id: int,
    only_active: bool = True
) -> List:
    """
    Hakee kohteen viemäriliitokset.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        only_active: Jos True, palauttaa vain aktiiviset (loppupvm is None)
        
    Returns:
        Lista viemäriliitoksista
    """
    from jkrimporter.providers.db.models import Base

    Viemariliitos = Base.classes.viemari_liitos

    query = select(Viemariliitos).where(Viemariliitos.kohde_id == kohde_id)

    if only_active:
        query = query.where(Viemariliitos.viemariverkosto_loppupvm.is_(None))

    return session.execute(query).scalars().all()
