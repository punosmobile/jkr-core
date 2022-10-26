-- object: jkr.rakennuksen_vanhimmat | type: TABLE --
-- DROP TABLE IF EXISTS jkr.rakennuksen_vanhimmat CASCADE;
CREATE TABLE jkr.rakennuksen_vanhimmat (
	rakennus_id integer NOT NULL,
	osapuoli_id integer NOT NULL,
    huoneistokirjain text,
    huoneistonumero integer,
    jakokirjain text,
	CONSTRAINT rakennuksen_vanhimmat_pk PRIMARY KEY (osapuoli_id)
);
-- ddl-end --
ALTER TABLE jkr.rakennuksen_vanhimmat OWNER TO jkr_admin;
-- ddl-end --

-- object: rakennus_fk | type: CONSTRAINT --
-- ALTER TABLE jkr.rakennuksen_vanhimmat DROP CONSTRAINT IF EXISTS rakennus_fk CASCADE;
ALTER TABLE jkr.rakennuksen_vanhimmat ADD CONSTRAINT rakennus_fk FOREIGN KEY (rakennus_id)
REFERENCES jkr.rakennus (id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: osapuoli_fk | type: CONSTRAINT --
-- ALTER TABLE jkr.rakennuksen_vanhimmat DROP CONSTRAINT IF EXISTS osapuoli_fk CASCADE;
ALTER TABLE jkr.rakennuksen_vanhimmat ADD CONSTRAINT osapuoli_fk FOREIGN KEY (osapuoli_id)
REFERENCES jkr.osapuoli (id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: idx_rakennuksen_vanhimmat_rakennus_id | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_rakennuksen_vanhimmat_rakennus_id CASCADE;
CREATE INDEX idx_rakennuksen_vanhimmat_rakennus_id ON jkr.rakennuksen_vanhimmat
USING btree
(
	rakennus_id
);

-- Some vanhimmat have no extra fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_rakennus_id
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id)
    WHERE huoneistokirjain is null and huoneistonumero is null and jakokirjain is null;

-- Some vanhimmat have one extra field
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, huoneistokirjain)
    WHERE huoneistokirjain is not null and huoneistonumero is null and jakokirjain is null;

CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistonumero
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, huoneistonumero)
    WHERE huoneistokirjain is null and huoneistonumero is not null and jakokirjain is null;

-- Some vanhimmat have two extra fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, huoneistokirjain, huoneistonumero)
    WHERE huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is null;

CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistonumero_jakokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, huoneistonumero, jakokirjain)
    WHERE huoneistokirjain is null and huoneistonumero is not null and jakokirjain is not null;

-- Some vanhimmat have all fields
CREATE UNIQUE INDEX uidx_rakennuksen_vanhimmat_huoneistokirjain_huoneistonumero_jakokirjain
    ON jkr.rakennuksen_vanhimmat
    (rakennus_id, huoneistokirjain, huoneistonumero, jakokirjain)
    WHERE huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is not null;
