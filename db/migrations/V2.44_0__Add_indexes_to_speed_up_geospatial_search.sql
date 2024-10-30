-- V2.44.0__Add_spatial_indexes.sql
-- Luodaan spatiaaliset indeksit rakennusten geometrioille
CREATE INDEX IF NOT EXISTS idx_rakennus_geom 
ON jkr.rakennus USING GIST (geom);

-- Luodaan indeksit yleisimmin käytetyille hakukentille
CREATE INDEX IF NOT EXISTS idx_rakennus_omistaja 
ON jkr.rakennuksen_omistajat (osapuoli_id);

CREATE INDEX IF NOT EXISTS idx_rakennus_osoite 
ON jkr.osoite (rakennus_id, katu_id, osoitenumero);

CREATE INDEX idx_kohteen_rakennukset_rakennus_id ON jkr.kohteen_rakennukset(rakennus_id);
CREATE INDEX idx_kohteen_osapuolet_osapuoli_rooli ON jkr.kohteen_osapuolet(osapuoli_id, osapuolenrooli_id);

-- Käytetään oikeaa sarakenimeä rakennuksenkayttotarkoitus_koodi
CREATE INDEX IF NOT EXISTS idx_rakennuksenkayttotarkoitus 
ON jkr.rakennus (rakennuksenkayttotarkoitus_koodi);

-- Luodaan materialisoitu näkymä lähellä olevien rakennusten löytämiseen
CREATE MATERIALIZED VIEW IF NOT EXISTS jkr.nearby_buildings AS
SELECT 
    r1.id as rakennus1_id,
    r2.id as rakennus2_id,
    ST_Distance(r1.geom, r2.geom) as distance
FROM jkr.rakennus r1
JOIN jkr.rakennus r2 ON 
    r1.id < r2.id AND
    ST_DWithin(r1.geom, r2.geom, 300)
WHERE
    r1.geom IS NOT NULL AND 
    r2.geom IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_nearby_buildings_r1 
ON jkr.nearby_buildings (rakennus1_id);

CREATE INDEX IF NOT EXISTS idx_nearby_buildings_r2 
ON jkr.nearby_buildings (rakennus2_id);

CREATE INDEX IF NOT EXISTS idx_nearby_buildings_dist 
ON jkr.nearby_buildings (distance);

-- Funktio materialisoidun näkymän päivittämiseen
CREATE OR REPLACE FUNCTION jkr.refresh_nearby_buildings()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW jkr.nearby_buildings;
END;
$$ LANGUAGE plpgsql;