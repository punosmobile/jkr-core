ALTER TABLE jkr.osapuoli
    ADD COLUMN nimi text;

UPDATE
    jkr.osapuoli
SET
    nimi = CONCAT_WS(' ', sukunimi, etunimi);

ALTER TABLE jkr.osapuoli
    ALTER COLUMN nimi SET NOT NULL;

ALTER TABLE jkr.osapuoli
    DROP COLUMN etunimi;

ALTER TABLE jkr.osapuoli
    DROP COLUMN sukunimi;

