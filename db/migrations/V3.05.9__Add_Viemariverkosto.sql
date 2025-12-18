-- SEQUENCE: jkr.viemariverkosto_id_seq

-- DROP SEQUENCE IF EXISTS jkr.viemariverkosto_id_seq;

CREATE SEQUENCE IF NOT EXISTS jkr.viemariverkosto_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE jkr.viemariverkosto_id_seq
    OWNER TO jkr_admin;

GRANT ALL ON SEQUENCE jkr.viemariverkosto_id_seq TO jkr_admin;

GRANT USAGE ON SEQUENCE jkr.viemariverkosto_id_seq TO jkr_editor;


CREATE TABLE IF NOT EXISTS jkr.viemariverkosto
(
    id integer NOT NULL DEFAULT nextval('jkr.viemariverkosto_id_seq'::regclass),
    geom geometry(MultiPolygon,3067) NOT NULL,
    nimi text COLLATE pg_catalog."default",
    viemariverkosto_id integer,
    alkupvm date NOT NULL,
    loppupvm date,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(COALESCE(alkupvm, '-infinity'::date), COALESCE(loppupvm, 'infinity'::date), '[]'::text)) STORED,
    CONSTRAINT viemariverkosto_pk PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER SEQUENCE jkr.viemariverkosto_id_seq
    OWNED BY jkr.viemariverkosto.id;

ALTER TABLE IF EXISTS jkr.viemariverkosto
    OWNER to jkr_admin;

REVOKE ALL ON TABLE jkr.viemariverkosto FROM jkr_editor;
REVOKE ALL ON TABLE jkr.viemariverkosto FROM jkr_viewer;

GRANT ALL ON TABLE jkr.viemariverkosto TO jkr_admin;

GRANT INSERT, DELETE, UPDATE ON TABLE jkr.viemariverkosto TO jkr_editor;

GRANT SELECT ON TABLE jkr.viemariverkosto TO jkr_viewer;

COMMENT ON TABLE jkr.viemariverkosto
    IS 'Näyttää kunnallisen viemäriverkostoalueen rajat';

COMMENT ON COLUMN jkr.viemariverkosto.geom
    IS 'Viemäriverkoston aluerajaus';
-- Index: idx_viemariverkosto_geom

-- DROP INDEX IF EXISTS jkr.idx_viemariverkosto_geom;

CREATE INDEX IF NOT EXISTS idx_viemariverkosto_geom
    ON jkr.viemariverkosto USING gist
    (geom)
    WITH (fillfactor=90, buffering=auto)
    TABLESPACE pg_default;