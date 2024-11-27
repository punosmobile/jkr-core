-- V2.45.0__Add_spatial_indexes.sql
-- Luodaan indeksit nopeampaa päivitystä varten
CREATE INDEX idx_kohteen_rakennukset_rakennus_id ON jkr.kohteen_rakennukset(rakennus_id);
CREATE INDEX idx_kohteen_osapuolet_osapuoli_rooli ON jkr.kohteen_osapuolet(osapuoli_id, osapuolenrooli_id);
