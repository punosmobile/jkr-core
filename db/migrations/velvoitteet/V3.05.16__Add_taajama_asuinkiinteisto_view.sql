-- V3.05.16__Add_taajama_asuinkiinteisto_view.sql
-- LAH-460: Lisätään näkymä taajamassa oleville asuinkiinteistöille biojätevelvoitteita varten

-- Asuinkiinteistöt taajamassa (kohdetyyppi 7)
CREATE OR REPLACE VIEW jkr.v_taajama_asuinkiinteisto AS
SELECT DISTINCT k.id
FROM jkr.kohde k
JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
JOIN jkr.rakennus r ON r.id = kr.rakennus_id
JOIN jkr.taajama t ON ST_Contains(t.geom, r.geom)
WHERE k.kohdetyyppi_id = 7;  -- Asuinkiinteistö

COMMENT ON VIEW jkr.v_taajama_asuinkiinteisto IS 'Näkymä taajamassa sijaitsevien asuinkiinteistöjen tunnistamiseen biojätevelvoitteita varten';
