ALTER TABLE jkr.kohde
ADD COLUMN perusmaksurekisterikohde boolean DEFAULT NULL;

COMMENT ON COLUMN jkr.kohde.perusmaksurekisterikohde IS 'Tieto siitä, onko kohde perusmaksurekisteristä';

-- Lisätään indeksi perusmaksurekisterikohde-kentälle
CREATE INDEX idx_kohde_perusmaksurekisterikohde ON jkr.kohde (perusmaksurekisterikohde);