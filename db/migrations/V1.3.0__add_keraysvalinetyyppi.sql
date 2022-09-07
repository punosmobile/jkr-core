CREATE TABLE jkr_koodistot.keraysvalinetyyppi (
	id smallint NOT NULL GENERATED ALWAYS AS IDENTITY ,
	selite text,
	CONSTRAINT keraysvalinetyyppi_pk PRIMARY KEY (id)
);
COMMENT ON TABLE jkr_koodistot.keraysvalinetyyppi IS E'Taulu, joka sisältää mahdolliset keräysvälinetyypit';
COMMENT ON COLUMN jkr_koodistot.keraysvalinetyyppi.id IS E'Taulun avaimena toimiva uniikki kokonaislukutunniste. Tunniste generoidaan automaattisesti';
COMMENT ON COLUMN jkr_koodistot.keraysvalinetyyppi.selite IS E'Kuvaus tietyn tunnisteen omaavasta keräysvälinetyypistä';
ALTER TABLE jkr_koodistot.keraysvalinetyyppi OWNER TO jkr_admin;

CREATE UNIQUE INDEX uidx_keraysvalinetyyppi_selite ON jkr_koodistot.keraysvalinetyyppi
USING btree
(
	selite
);

INSERT INTO jkr_koodistot.keraysvalinetyyppi (selite) SELECT DISTINCT keraysvalinetyyppi from jkr.keraysvaline;

ALTER TABLE jkr.keraysvaline ADD COLUMN keraysvalinetyyppi_id smallint;

ALTER TABLE jkr.keraysvaline ADD CONSTRAINT keraysvalinetyyppi_fk FOREIGN KEY (keraysvalinetyyppi_id)
REFERENCES jkr_koodistot.keraysvalinetyyppi (id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;

UPDATE jkr.keraysvaline AS kv SET keraysvalinetyyppi_id = (
SELECT id FROM jkr_koodistot.keraysvalinetyyppi AS kvt WHERE kv.keraysvalinetyyppi = kvt.selite
);

ALTER TABLE jkr.keraysvaline DROP COLUMN IF EXISTS keraysvalinetyyppi CASCADE;
