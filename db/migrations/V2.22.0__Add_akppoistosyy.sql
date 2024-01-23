CREATE TABLE jkr_koodistot.akppoistosyy (
	id serial NOT NULL,
	selite text NOT NULL,
	CONSTRAINT akppoistosyy_pk PRIMARY KEY (id)
);
ALTER TABLE jkr_koodistot.akppoistosyy OWNER TO jkr_admin;

CREATE UNIQUE INDEX akppoistosyy_selite_uidx ON jkr_koodistot.akppoistosyy
USING btree
(
	selite
);
