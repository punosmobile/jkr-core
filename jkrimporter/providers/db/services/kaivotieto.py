"""
Kaivotietojen tietokantapalvelut.

LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.
"""

import logging
from datetime import date
from typing import List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from jkrimporter.providers.lahti.kaivo_models import KaivotietoTyyppi

if TYPE_CHECKING:
    from jkrimporter.providers.db.models import Kohde

logger = logging.getLogger(__name__)


# Kartoitus KaivotietoTyyppi -> tietokanta-id
KAIVOTIETOTYYPPI_ID_MAP = {
    KaivotietoTyyppi.KANTOVESI: 1,
    KaivotietoTyyppi.SAOSTUSSAILIO: 2,
    KaivotietoTyyppi.PIENPUHDISTAMO: 3,
    KaivotietoTyyppi.UMPISAILIO: 4,
    KaivotietoTyyppi.VAIN_HARMAAT_VEDET: 5,
}


def get_kaivotietotyyppi_id(tyyppi: KaivotietoTyyppi) -> int:
    """Palauttaa kaivotietotyypin tietokanta-id:n."""
    return KAIVOTIETOTYYPPI_ID_MAP[tyyppi]


def find_kohde_by_single_prt(session: Session, prt: str) -> Optional["Kohde"]:
    """
    Etsii kohteen yksittäisen PRT:n perusteella.
    
    Args:
        session: Tietokantaistunto
        prt: Pysyvä rakennustunnus
        
    Returns:
        Kohde tai None jos ei löydy
    """
    from jkrimporter.providers.db.models import Kohde, KohteenRakennukset, Rakennus
    
    query = (
        select(Kohde)
        .join(KohteenRakennukset, KohteenRakennukset.kohde_id == Kohde.id)
        .join(Rakennus, Rakennus.id == KohteenRakennukset.rakennus_id)
        .where(
            and_(
                Rakennus.prt == prt,
                Kohde.loppupvm.is_(None)  # Vain aktiiviset kohteet
            )
        )
    )
    
    result = session.execute(query).scalars().first()
    return result


def find_existing_kaivotieto(
    session: Session,
    kohde_id: int,
    kaivotietotyyppi_id: int,
    alkupvm: date
) -> bool:
    """
    Tarkistaa onko sama kaivotieto jo olemassa.
    
    Määrittelyn mukaan: Jos kohteella on jo sama tieto, sitä ei viedä päälle.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        kaivotietotyyppi_id: Kaivotietotyypin id
        alkupvm: Alkupäivämäärä
        
    Returns:
        True jos löytyy, False muuten
    """
    from jkrimporter.providers.db.models import Base
    
    # Haetaan Kaivotieto-taulu reflektoimalla
    Kaivotieto = Base.classes.kaivotieto
    
    query = select(Kaivotieto.id).where(
        and_(
            Kaivotieto.kohde_id == kohde_id,
            Kaivotieto.kaivotietotyyppi_id == kaivotietotyyppi_id,
            Kaivotieto.alkupvm == alkupvm
        )
    )
    
    result = session.execute(query).scalars().first()
    return result is not None


def find_existing_kaivotieto_by_type(
    session: Session,
    kohde_id: int,
    kaivotietotyyppi_id: int
) -> bool:
    """
    Tarkistaa onko kohteella jo sama kaivotietotyyppi (millään alkupvm:llä).
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        kaivotietotyyppi_id: Kaivotietotyypin id
        
    Returns:
        True jos löytyy, False muuten
    """
    from jkrimporter.providers.db.models import Base
    
    Kaivotieto = Base.classes.kaivotieto
    
    query = select(Kaivotieto.id).where(
        and_(
            Kaivotieto.kohde_id == kohde_id,
            Kaivotieto.kaivotietotyyppi_id == kaivotietotyyppi_id,
            Kaivotieto.loppupvm.is_(None)  # Vain aktiiviset
        )
    )
    
    result = session.execute(query).scalars().first()
    return result is not None


def insert_kaivotieto(
    session: Session,
    kohde_id: int,
    kaivotietotyyppi: KaivotietoTyyppi,
    alkupvm: date,
    tietolahde: Optional[str] = None,
    tiedontuottaja_tunnus: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Lisää uuden kaivotiedon kohteelle.
    
    Määrittelyn mukaan: Jos kohteella on jo sama tieto, sitä ei viedä päälle.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        kaivotietotyyppi: Kaivotietotyyppi
        alkupvm: Alkupäivämäärä
        tietolahde: Tiedon lähde
        tiedontuottaja_tunnus: Tiedontuottajan tunnus
        
    Returns:
        Tuple (onnistui: bool, viesti: str)
    """
    from jkrimporter.providers.db.models import Base
    
    Kaivotieto = Base.classes.kaivotieto
    
    kaivotietotyyppi_id = get_kaivotietotyyppi_id(kaivotietotyyppi)
    
    # Tarkista onko jo olemassa
    if find_existing_kaivotieto(session, kohde_id, kaivotietotyyppi_id, alkupvm):
        return False, f"Kaivotieto {kaivotietotyyppi.value} alkupvm {alkupvm} on jo olemassa kohteella {kohde_id}"
    
    # Luo uusi kaivotieto
    kaivotieto = Kaivotieto(
        kohde_id=kohde_id,
        kaivotietotyyppi_id=kaivotietotyyppi_id,
        alkupvm=alkupvm,
        tietolahde=tietolahde,
        tiedontuottaja_tunnus=tiedontuottaja_tunnus
    )
    
    session.add(kaivotieto)
    
    return True, f"Lisätty kaivotieto {kaivotietotyyppi.value} kohteelle {kohde_id}"


def update_kaivotieto_loppupvm(
    session: Session,
    kohde_id: int,
    kaivotietotyyppi: KaivotietoTyyppi,
    loppupvm: date
) -> Tuple[int, str]:
    """
    Päivittää kaivotiedon loppupäivämäärän.
    
    Määrittelyn mukaan: Lopetus edellyttää että samalla kohteella on vastaava tieto alkanut.
    Mikäli kohteella on useita samoja alkaneita kaivotietoja, lopetuspäivämäärä lopettaa 
    kaikki vastaavat samannimiset kaivotiedot.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        kaivotietotyyppi: Kaivotietotyyppi
        loppupvm: Loppupäivämäärä
        
    Returns:
        Tuple (päivitettyjen määrä: int, viesti: str)
    """
    from jkrimporter.providers.db.models import Base
    
    Kaivotieto = Base.classes.kaivotieto
    
    kaivotietotyyppi_id = get_kaivotietotyyppi_id(kaivotietotyyppi)
    
    # Etsi kaikki aktiiviset kaivotiedot tällä tyypillä
    query = select(Kaivotieto).where(
        and_(
            Kaivotieto.kohde_id == kohde_id,
            Kaivotieto.kaivotietotyyppi_id == kaivotietotyyppi_id,
            Kaivotieto.loppupvm.is_(None)  # Vain aktiiviset
        )
    )
    
    kaivotiedot = session.execute(query).scalars().all()
    
    if not kaivotiedot:
        return 0, f"Ei löytynyt aktiivista kaivotietoa {kaivotietotyyppi.value} kohteelta {kohde_id}"
    
    # Päivitä loppupvm kaikille
    updated_count = 0
    for kaivotieto in kaivotiedot:
        kaivotieto.loppupvm = loppupvm
        updated_count += 1
    
    return updated_count, f"Päivitetty {updated_count} kaivotiedon {kaivotietotyyppi.value} loppupvm kohteelle {kohde_id}"


def get_kaivotiedot_for_kohde(
    session: Session,
    kohde_id: int,
    only_active: bool = True
) -> List:
    """
    Hakee kohteen kaivotiedot.
    
    Args:
        session: Tietokantaistunto
        kohde_id: Kohteen id
        only_active: Jos True, palauttaa vain aktiiviset (loppupvm is None)
        
    Returns:
        Lista kaivotiedoista
    """
    from jkrimporter.providers.db.models import Base
    
    Kaivotieto = Base.classes.kaivotieto
    
    query = select(Kaivotieto).where(Kaivotieto.kohde_id == kohde_id)
    
    if only_active:
        query = query.where(Kaivotieto.loppupvm.is_(None))
    
    return session.execute(query).scalars().all()
