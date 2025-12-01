"""
Kaivotietojen virheraportointi.

LAH-415: Kaivotiedot ja kaivotiedon lopetus tietojen vienti kantaan.
"""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

logger = logging.getLogger(__name__)


def get_kaivotiedot_error_filename(prefix: str = "kaivotiedot") -> str:
    """Luo virheraportin tiedostonimi aikaleimalla."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_kohdentumattomat_{timestamp}.csv"


def export_kohdentumattomat_kaivotiedot(
    output_dir: Union[str, Path],
    kohdentumattomat: List[Dict[str, str]],
    prefix: str = "kaivotiedot"
) -> Path:
    """
    Vie kohdentumattomat kaivotiedot CSV-tiedostoon.
    
    Määrittelyn mukaan: Sarakkeiden otsikot ja tietosisältö sama kuin sisään ajetussa aineistossa.
    
    Args:
        output_dir: Hakemisto johon tiedosto tallennetaan
        kohdentumattomat: Lista kohdentumattomista riveistä (rawdata-dictionaryt)
        prefix: Tiedostonimen etuliite
        
    Returns:
        Polku luotuun tiedostoon
    """
    if not kohdentumattomat:
        logger.info("Ei kohdentumattomia kaivotietoja")
        return None
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = get_kaivotiedot_error_filename(prefix)
    filepath = output_path / filename
    
    # Käytä ensimmäisen rivin avaimia otsikoina
    fieldnames = list(kohdentumattomat[0].keys())
    
    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(kohdentumattomat)
    
    logger.info(f"Kohdentumattomat kaivotiedot ({len(kohdentumattomat)} kpl) tallennettu: {filepath}")
    
    return filepath


def export_kohdentumattomat_kaivotiedon_lopetukset(
    output_dir: Union[str, Path],
    kohdentumattomat: List[Dict[str, str]]
) -> Path:
    """
    Vie kohdentumattomat kaivotiedon lopetukset CSV-tiedostoon.
    
    Args:
        output_dir: Hakemisto johon tiedosto tallennetaan
        kohdentumattomat: Lista kohdentumattomista riveistä
        
    Returns:
        Polku luotuun tiedostoon
    """
    return export_kohdentumattomat_kaivotiedot(
        output_dir, 
        kohdentumattomat, 
        prefix="kaivotiedon_lopetukset"
    )
