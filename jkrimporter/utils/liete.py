"""
LIETE-aineiston apufunktiot.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def export_kohdentumattomat_liete_kuljetukset(
    output_dir: str, 
    kohdentumattomat: List[Dict[str, Any]]
) -> None:
    """
    Tallentaa kohdentamattomat LIETE-kuljetukset CSV-tiedostoon.
    
    Args:
        output_dir: Hakemisto johon tiedosto tallennetaan
        kohdentumattomat: Lista kohdentumattomista kuljetuksista
    """
    if not kohdentumattomat:
        logger.info("Ei kohdentumattomia LIETE-kuljetuksia tallennettavaksi")
        return
    
    output_path = Path(output_dir) / "kohdentumattomat_liete_kuljetukset.csv"
    
    try:
        with open(output_path, mode='w', encoding='utf-8', newline='') as csv_file:
            # Käytä ensimmäisen rivin avaimia sarakeotsikoina
            if kohdentumattomat:
                # Hae ulkoinen_asiakastieto ja muunna se dict:ksi jos se on objekti
                first_item = kohdentumattomat[0]
                ulkoinen = first_item.get("ulkoinen_asiakastieto")
                
                if hasattr(ulkoinen, '__dict__'):
                    # Objekti, käytä sen attribuutteja
                    sample_dict = ulkoinen.__dict__
                elif hasattr(ulkoinen, 'dict'):
                    # Pydantic-malli
                    sample_dict = ulkoinen.dict()
                elif isinstance(ulkoinen, dict):
                    sample_dict = ulkoinen
                else:
                    logger.warning(f"Tuntematon ulkoinen_asiakastieto tyyppi: {type(ulkoinen)}")
                    sample_dict = {}
                
                fieldnames = list(sample_dict.keys()) if sample_dict else []
                
                if not fieldnames:
                    logger.warning("Ei sarakkeita kohdentumattomille LIETE-kuljetuksille")
                    return
                
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                
                for item in kohdentumattomat:
                    ulkoinen = item.get("ulkoinen_asiakastieto")
                    
                    if hasattr(ulkoinen, '__dict__'):
                        row_dict = ulkoinen.__dict__
                    elif hasattr(ulkoinen, 'dict'):
                        row_dict = ulkoinen.dict()
                    elif isinstance(ulkoinen, dict):
                        row_dict = ulkoinen
                    else:
                        continue
                    
                    # Muunna kaikki arvot merkkijonoiksi
                    row_dict = {k: str(v) if v is not None else '' for k, v in row_dict.items()}
                    writer.writerow(row_dict)
        
        logger.info(f"Tallennettu {len(kohdentumattomat)} kohdentamatonta LIETE-kuljetusta tiedostoon: {output_path}")
        print(f"Kohdentamattomat LIETE-kuljetukset ({len(kohdentumattomat)} kpl) tallennettu: {output_path}")
        
    except Exception as e:
        logger.exception(f"Virhe tallennettaessa kohdentumattomia LIETE-kuljetuksia: {e}")
        print(f"VIRHE: Kohdentumattomien LIETE-kuljetusten tallennus epäonnistui: {e}")
