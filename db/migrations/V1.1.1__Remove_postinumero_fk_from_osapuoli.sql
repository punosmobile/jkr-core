ALTER TABLE jkr.osapuoli
    DROP CONSTRAINT IF EXISTS posti_fk CASCADE;

ALTER TABLE jkr.osapuoli RENAME COLUMN posti_numero TO postinumero;

ALTER TABLE jkr.osapuoli
    ALTER COLUMN postinumero TYPE text;

ALTER TABLE jkr.osapuoli
    ADD CONSTRAINT chk_postinumero CHECK (LENGTH(postinumero) = 5);

