
ALTER TABLE jkr.kiinteisto DROP CONSTRAINT IF EXISTS omistaja_osapuoli_fk CASCADE;
ALTER TABLE jkr.kiinteisto DROP COLUMN IF EXISTS omistaja_osapuoli_id CASCADE;

ALTER TABLE jkr.rakennus ADD COLUMN kayttoonotto_pvm date;
ALTER TABLE jkr.rakennus ADD COLUMN kaytostapoisto_pvm date;

CREATE TABLE jkr.kiinteiston_omistajat (
	kiinteisto_id integer NOT NULL,
	osapuoli_id integer NOT NULL,
	CONSTRAINT kiinteiston_omistajat_pk PRIMARY KEY (kiinteisto_id,osapuoli_id)
);

CREATE INDEX idx_rakennuksen_omistajat_rakennus_id ON jkr.rakennuksen_omistajat
USING btree
(
	rakennus_id
);

ALTER TABLE jkr.kiinteiston_omistajat OWNER TO jkr_admin;

CREATE TABLE jkr_koodistot.keraysvalinetyyppi (
	koodi text NOT NULL,
	selite text NOT NULL,
	CONSTRAINT keraysvalinetyyppi_pk PRIMARY KEY (koodi)
);
ALTER TABLE jkr_koodistot.keraysvalinetyyppi OWNER TO jkr_admin;

ALTER TABLE jkr.keraysvaline ADD COLUMN keraysvalinetyyppi_koodi text;


ALTER TABLE jkr_koodistot.tiedontuottaja ALTER COLUMN tunnus TYPE text;
-- ddl-end --
ALTER TABLE jkr_koodistot.rakennuksenkayttotarkoitus ALTER COLUMN koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr_koodistot.rakennuksenolotila ALTER COLUMN koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr_koodistot.osapuolenlaji ALTER COLUMN koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr.rakennus ALTER COLUMN rakennuksenkayttotarkoitus_koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr.rakennus ALTER COLUMN rakennuksenolotila_koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr.osapuoli ALTER COLUMN osapuolenlaji_koodi TYPE text;
-- ddl-end --
ALTER TABLE jkr.ulkoinen_kohdetunnus ALTER COLUMN tiedontuottaja_tunnus TYPE text;
-- ddl-end --


ALTER TABLE jkr.kiinteiston_omistajat ADD CONSTRAINT kiinteisto_fk FOREIGN KEY (kiinteisto_id)
REFERENCES jkr.kiinteisto (id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

ALTER TABLE jkr.kiinteiston_omistajat ADD CONSTRAINT osapuoli_fk FOREIGN KEY (osapuoli_id)
REFERENCES jkr.osapuoli (id) MATCH SIMPLE
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

ALTER TABLE jkr.keraysvaline ADD CONSTRAINT keraysvalinetyyppi_fk FOREIGN KEY (keraysvalinetyyppi_koodi)
REFERENCES jkr_koodistot.keraysvalinetyyppi (koodi) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;

