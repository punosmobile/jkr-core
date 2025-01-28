ALTER TABLE jkr.kohde
ADD COLUMN lukittu boolean DEFAULT NULL;

COMMENT ON COLUMN jkr.kohde.lukittu IS 'Tieto siitä, onko kohde lukittu';

-- Lisätään indeksi lukittu-kentälle
CREATE INDEX idx_kohde_lukittu ON jkr.kohde (lukittu);