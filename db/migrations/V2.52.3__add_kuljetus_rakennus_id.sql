ALTER TABLE IF EXISTS jkr.kuljetus
    ADD COLUMN rakennus_id integer;

ALTER TABLE IF EXISTS jkr.kuljetus
ADD CONSTRAINT rakennus_fk FOREIGN KEY (rakennus_id)
REFERENCES jkr.rakennus (id) MATCH FULL
ON UPDATE CASCADE
ON DELETE CASCADE;