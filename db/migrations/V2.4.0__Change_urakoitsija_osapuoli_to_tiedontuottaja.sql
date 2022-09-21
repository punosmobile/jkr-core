-- Sopimus
ALTER TABLE jkr.sopimus ADD COLUMN tiedontuottaja_tunnus text;

ALTER TABLE jkr.sopimus ADD CONSTRAINT tiedontuottaja_fk FOREIGN KEY (tiedontuottaja_tunnus)
REFERENCES jkr_koodistot.tiedontuottaja (tunnus) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;

UPDATE jkr.sopimus SET tiedontuottaja_tunnus='PJH';
ALTER TABLE jkr.sopimus ALTER COLUMN tiedontuottaja_tunnus SET NOT NULL;
ALTER TABLE jkr.sopimus DROP CONSTRAINT IF EXISTS urakoitsija_osapuoli_fk CASCADE;
ALTER TABLE jkr.sopimus DROP COLUMN IF EXISTS urakoitsija_osapuoli_id CASCADE;



-- Kuljetus
ALTER TABLE jkr.kuljetus ADD COLUMN tiedontuottaja_tunnus text;

ALTER TABLE jkr.kuljetus ADD CONSTRAINT tiedontuottaja_fk FOREIGN KEY (tiedontuottaja_tunnus)
REFERENCES jkr_koodistot.tiedontuottaja (tunnus) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;

UPDATE jkr.kuljetus SET tiedontuottaja_tunnus='PJH';
ALTER TABLE jkr.kuljetus ALTER COLUMN tiedontuottaja_tunnus SET NOT NULL;
ALTER TABLE jkr.kuljetus DROP CONSTRAINT IF EXISTS urakoitsija_osapuoli_fk CASCADE;
ALTER TABLE jkr.kuljetus DROP COLUMN IF EXISTS urakoitsija_osapuoli_id CASCADE;
