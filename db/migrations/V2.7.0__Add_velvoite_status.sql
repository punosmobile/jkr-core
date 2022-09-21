
ALTER TABLE jkr.velvoite DROP COLUMN alkupvm;
ALTER TABLE jkr.velvoite DROP COLUMN loppupvm;

ALTER TABLE jkr.velvoitemalli ADD COLUMN alkupvm date;
ALTER TABLE jkr.velvoitemalli ADD COLUMN loppupvm date;
ALTER TABLE jkr.velvoitemalli ADD COLUMN voimassaolo daterange GENERATED ALWAYS AS (daterange(alkupvm, loppupvm, '[]')) STORED;


-- object: jkr.velvoite_status | type: TABLE --
-- DROP TABLE IF EXISTS jkr.velvoite_status CASCADE;
CREATE TABLE jkr.velvoite_status (
	id serial NOT NULL,
	pvm date NOT NULL,
	ok bool NOT NULL,
	velvoite_id integer NOT NULL,
	tallennuspvm date NOT NULL,
	CONSTRAINT velvoite_status_pk PRIMARY KEY (id)
);
-- ddl-end --
ALTER TABLE jkr.velvoite_status OWNER TO jkr_admin;
-- ddl-end --

-- [ Created foreign keys ] --
-- object: velvoite_fk | type: CONSTRAINT --
-- ALTER TABLE jkr.velvoite_status DROP CONSTRAINT IF EXISTS velvoite_fk CASCADE;
ALTER TABLE jkr.velvoite_status ADD CONSTRAINT velvoite_fk FOREIGN KEY (velvoite_id)
REFERENCES jkr.velvoite (id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --


CREATE INDEX idx_velvoite_status_velvoite_id ON jkr.velvoite_status USING btree (velvoite_id);

-- object: voimassaolo | type: COLUM
CREATE UNIQUE INDEX uidx_velvoite_status_velvoite_id_pvm ON jkr.velvoite_status
USING btree
(
	velvoite_id,
	pvm
);

CREATE UNIQUE INDEX uidx_velvoite_kohde_id_velvoitemalli_id ON jkr.velvoite
USING btree
(
	kohde_id,
	velvoitemalli_id
);

CREATE UNIQUE INDEX uidx_velvoitemalli_selite ON jkr.velvoitemalli
USING btree
(
	selite
);

