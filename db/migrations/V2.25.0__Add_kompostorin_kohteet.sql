CREATE TABLE jkr.kompostorin_kohteet (
    kompostori_id integer NOT NULL,
    kohde_id integer NOT NULL,
    CONSTRAINT kompostorin_kohteet_pk PRIMARY KEY (kompostori_id, kohde_id),
    CONSTRAINT kompostori_fk FOREIGN KEY (kompostori_id)
        REFERENCES jkr.kompostori (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT kohde_fk FOREIGN KEY (kohde_id)
        REFERENCES jkr.kohde (id) MATCH FULL
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
ALTER TABLE jkr.kompostorin_kohteet OWNER TO jkr_admin;

CREATE UNIQUE INDEX uidx_kompostorin_kohteet_kohde_id ON jkr.kompostorin_kohteet
USING btree
(
	kohde_id
);
