-- V2.50.1__Add_hapa_and_biohapa_views

-- HAPA kohteiden tunnistamisnäkymä
CREATE OR REPLACE VIEW jkr.v_hapa_kohde AS
SELECT DISTINCT k.id
FROM jkr.kohde k
WHERE k.kohdetyyppi_id = 5;  -- HAPA

-- BIOHAPA kohteiden tunnistamisnäkymä
CREATE OR REPLACE VIEW jkr.v_biohapa_kohde AS
SELECT DISTINCT k.id
FROM jkr.kohde k
WHERE k.kohdetyyppi_id = 6;  -- BIOHAPA

-- Kommentit näkymille
COMMENT ON VIEW jkr.v_hapa_kohde IS 'Näkymä HAPA-tyyppisten kohteiden tunnistamiseen';
COMMENT ON VIEW jkr.v_biohapa_kohde IS 'Näkymä BIOHAPA-tyyppisten kohteiden tunnistamiseen';