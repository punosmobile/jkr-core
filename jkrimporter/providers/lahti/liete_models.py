"""
LIETE-aineiston datamallit.

LIETE-aineisto sisältää kuljetustietoja, päätöksiä ja kompostointitietoja
jotka eroavat rakenteeltaan normaalista siirtotiedostosta.
"""

import datetime
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, validator


class LieteKuljetusRow(BaseModel):
    """
    LIETE kuljetustietojen rivimalli.
    
    Vastaa LIETE-rekisterin kuljetustiedosto-Excel:n rakennetta.
    """
    id_tunnus: Optional[str] = Field(alias="ID-tunnus")
    siirron_alkamisaika: Optional[datetime.date] = Field(alias="Siirron alkamisaika")
    jatteen_tuottaja: Optional[str] = Field(alias="Jätteen tuottaja tai muu haltija")
    tuottajan_osoite: Optional[str] = Field(alias="Jätteen tuottajan/haltijan osoite")
    tuottajan_katuosoite: Optional[str] = Field(alias="Jätteen tuottajan/haltijan katuosoite")
    tuottajan_postinumero: Optional[str] = Field(alias="Jätteen tuottajan/haltijan postinumero")
    siirron_alkamispaikka: Optional[str] = Field(alias="Siirron alkamispaikka")
    alkamispaikan_katuosoite: Optional[str] = Field(alias="Siirron alkamispaikan katuosoite")
    alkamispaikan_postinumero: Optional[str] = Field(alias="Siirron alkamispaikan postinumero")
    kuljettaja: Optional[str] = Field(alias="Kuljettaja")
    vastaanottaja: Optional[str] = Field(alias="Vastaanottaja")
    siirron_paattymispaikka: Optional[str] = Field(alias="Siirron päättymispaikka")
    paattymispaikan_katuosoite: Optional[str] = Field(alias="Siirron päättymispaikan katuosoite")
    paattymispaikan_postinumero: Optional[str] = Field(alias="Siirron päättymispaikan postinumero")
    siirron_paattymisaika: Optional[datetime.date] = Field(alias="Siirron päättymisaika")
    jate: Optional[str] = Field(alias="Jäte")
    jatteen_kuvaus: Optional[str] = Field(alias="Jätteen kuvaus")
    jatteen_paino_t: Optional[float] = Field(alias="Jätteen paino (t)")
    jatteen_tilavuus_m3: Optional[float] = Field(alias="Jätteen tilavuus (m³)")
    kiinteistotunnus: Optional[str] = Field(alias="Kiinteistötunnus")
    pysyva_rakennustunnus: Optional[str] = Field(alias="Pysyvä rakennustunnus")
    lietteen_tyyppi: Optional[str] = Field(alias="Lietteen tyyppi")

    @validator("siirron_alkamisaika", "siirron_paattymisaika", pre=True)
    def parse_date(cls, v):
        """Parsii päivämäärät eri formaateista."""
        if v is None or v == "":
            return None
        if isinstance(v, datetime.date):
            return v
        if isinstance(v, datetime.datetime):
            return v.date()
        if isinstance(v, str):
            # Yritä eri formaatteja
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
                try:
                    return datetime.datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
        return None

    @validator("jatteen_paino_t", "jatteen_tilavuus_m3", pre=True)
    def parse_float(cls, v):
        """Parsii desimaaliluvut, korvaa pilkut pisteillä."""
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Korvaa pilkku pisteellä ja poista välilyönnit
            v = v.replace(",", ".").replace(" ", "")
            try:
                return float(v)
            except ValueError:
                return None
        return None

    @validator("pysyva_rakennustunnus", "kiinteistotunnus", pre=True)
    def clean_tunnus(cls, v):
        """Puhdistaa tunnukset tyhjistä arvoista."""
        if v is None or v == "" or str(v).strip() == "":
            return None
        return str(v).strip()

    class Config:
        # Salli alias-kenttien käyttö
        allow_population_by_field_name = True
