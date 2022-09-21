
-- object: jkr_koodistot.tapahtumalaji | type: TABLE --
-- DROP TABLE IF EXISTS jkr_koodistot.tapahtumalaji CASCADE;
CREATE TABLE jkr_koodistot.tapahtumalaji (
	koodi text NOT NULL,
	selite text,
	CONSTRAINT tapahtumalaji_pk PRIMARY KEY (koodi)
);
-- ddl-end --
ALTER TABLE jkr_koodistot.tapahtumalaji OWNER TO jkr_admin;
-- ddl-end --


-- object: jkr_koodistot.paatostulos | type: TABLE --
-- DROP TABLE IF EXISTS jkr_koodistot.paatostulos CASCADE;
CREATE TABLE jkr_koodistot.paatostulos (
	koodi text NOT NULL,
	selite text,
	CONSTRAINT paatostulos_pk PRIMARY KEY (koodi)
);
-- ddl-end --
ALTER TABLE jkr_koodistot.paatostulos OWNER TO jkr_admin;
-- ddl-end --

