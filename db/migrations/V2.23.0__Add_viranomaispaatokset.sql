CREATE SEQUENCE jkr.viranomaispaatokset_id_seq;

CREATE TABLE jkr.viranomaispaatokset (
    id integer NOT NULL DEFAULT nextval('jkr.viranomaispaatokset_id_seq'::regclass),
    paatosnumero text,
    alkupvm date NOT NULL,
    loppupvm date NOT NULL,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(COALESCE(alkupvm, '-infinity'::date), COALESCE(loppupvm, 'infinity'::date), '[]'::text)) STORED,
    vastaanottaja text,
    tyhjennysvali smallint,
    paatostulos_koodi text NOT NULL,
    tapahtumalaji_koodi text NOT NULL,
    akppoistosyy_id integer,
    jatetyyppi_id integer NOT NULL,
    rakennus_id integer NOT NULL,
    CONSTRAINT viranomaispaatokset_pk PRIMARY KEY (id),
    CONSTRAINT paatostulos_fk FOREIGN KEY (paatostulos_koodi)
        REFERENCES jkr_koodistot.paatostulos (koodi) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT tapahtumalaji_fk FOREIGN KEY (tapahtumalaji_koodi)
        REFERENCES jkr_koodistot.tapahtumalaji (koodi) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT akppoistosyy_fk FOREIGN KEY (akppoistosyy_id)
        REFERENCES jkr_koodistot.akppoistosyy (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT jatetyyppi_fk FOREIGN KEY (jatetyyppi_id)
        REFERENCES jkr_koodistot.jatetyyppi (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT rakennus_fk FOREIGN KEY (rakennus_id)
        REFERENCES jkr.rakennus (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
ALTER TABLE jkr.viranomaispaatokset OWNER TO jkr_admin;

CREATE INDEX idx_viranomaispaatokset_rakennus_id ON jkr.viranomaispaatokset
USING btree
(
	rakennus_id
);
