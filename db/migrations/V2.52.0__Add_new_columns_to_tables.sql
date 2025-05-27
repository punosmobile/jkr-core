ALTER TABLE IF EXISTS jkr.rakennus ADD COLUMN kunta character varying COLLATE pg_catalog."default";

COMMENT ON COLUMN jkr.rakennus.kunta
    IS 'Tieto rakennuksen sijainti kunnasta';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN vakinaisen_osoitteen_alkupaiva date;
COMMENT ON COLUMN jkr.osapuoli.vakinaisen_osoitteen_alkupaiva
    IS 'Alkupäivä vakinaiselle osoitteelle';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN kuolinpaiva date;
COMMENT ON COLUMN jkr.osapuoli.kuolinpaiva
    IS 'Omistaja kuolinpäivä';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN postiosoite_postinumero character varying COLLATE pg_catalog."default";
COMMENT ON COLUMN jkr.osapuoli.postiosoite_postinumero
    IS 'Postiosoitteen postinumero';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN postiosoitteen_postitoimipaikka character varying COLLATE pg_catalog."default";
COMMENT ON COLUMN jkr.osapuoli.postiosoitteen_postitoimipaikka
    IS 'Postiosoitteen postitoimipaikka';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN postiosoite character varying COLLATE pg_catalog."default";
COMMENT ON COLUMN jkr.osapuoli.postiosoite
    IS 'Postiosoite';

ALTER TABLE IF EXISTS jkr.osapuoli ADD COLUMN maakoodi character varying COLLATE pg_catalog."default";
COMMENT ON COLUMN jkr.osapuoli.maakoodi
    IS 'Osapuolen kotimaan koodi';
