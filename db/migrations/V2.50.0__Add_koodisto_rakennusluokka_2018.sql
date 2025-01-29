-- V2.50.0__Add_koodisto_rakennusluokka_2018.sql
-- object: jkr_koodistot.rakennusluokka_2018 | type: TABLE --
-- DROP TABLE IF EXISTS jkr_koodistot.rakennusluokka_2018 CASCADE;
CREATE TABLE jkr_koodistot.rakennusluokka_2018 (
	koodi char(4) NOT NULL,
	selite text NOT NULL,
	CONSTRAINT rakennusluokka_2018_pk PRIMARY KEY (koodi)
);
-- ddl-end --
ALTER TABLE jkr_koodistot.rakennusluokka_2018 OWNER TO jkr_admin;
-- ddl-end --

