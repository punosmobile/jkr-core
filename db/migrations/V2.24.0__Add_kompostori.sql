CREATE SEQUENCE jkr.kompostori_id_seq;

CREATE TABLE jkr.kompostori (
    id integer NOT NULL DEFAULT nextval('jkr.kompostori_id_seq'::regclass),
    alkupvm date NOT NULL,
    loppupvm date,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(COALESCE(alkupvm, '-infinity'::date), COALESCE(loppupvm, 'infinity'::date), '[]'::text)) STORED,
    onko_kimppa bool,
    osoite_id integer NOT NULL,
    osapuoli_id integer NOT NULL,
    CONSTRAINT kompostori_pk PRIMARY KEY (id),
    CONSTRAINT osoite_fk FOREIGN KEY (osoite_id)
        REFERENCES jkr.osoite (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT osapuoli_fk FOREIGN KEY (osapuoli_id)
        REFERENCES jkr.osapuoli (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
ALTER TABLE jkr.kompostori OWNER TO jkr_admin;
