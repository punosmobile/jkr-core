
ALTER TABLE jkr.taajama ADD COLUMN tilastokeskus_id text;
ALTER TABLE jkr.taajama ADD COLUMN nimi text;
ALTER TABLE jkr.taajama ADD COLUMN nimi_sv text;
ALTER TABLE jkr.taajama ADD COLUMN vaesto_lkm bigint;
ALTER TABLE jkr.taajama ADD COLUMN paivitetty date;
ALTER TABLE jkr.taajama ALTER COLUMN geom SET NOT NULL;
CREATE INDEX idx_taajama_geom ON jkr.taajama
USING gist
(
	geom
);

ALTER TABLE jkr.jatteenkuljetusalue ADD COLUMN nimi text;

CREATE TABLE jkr.viemarointialue (
	id serial NOT NULL,
	nimi text,
	geom geometry(MULTIPOLYGON, 3067) NOT NULL,
	CONSTRAINT viemarointialue_pk PRIMARY KEY (id)
);
ALTER TABLE jkr.viemarointialue OWNER TO jkr_admin;
CREATE INDEX idx_viemarointialue_geom ON jkr.viemarointialue
USING gist
(
	geom
);


CREATE INDEX idx_jatteenkuljetusalue_geom ON jkr.jatteenkuljetusalue
USING gist
(
	geom
);

CREATE INDEX idx_toimialue_geom ON jkr.toimialue
USING gist
(
	geom
);

CREATE INDEX idx_pohjavesialue_geom ON jkr.pohjavesialue
USING gist
(
	geom
);
