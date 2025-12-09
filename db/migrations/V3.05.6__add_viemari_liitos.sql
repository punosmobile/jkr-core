CREATE TABLE jkr.viemari_liitos (
    id SERIAL PRIMARY KEY,
    kohde_id INTEGER NOT NULL,
    viemariverkosto_alkupvm DATE NOT NULL,
    viemariverkosto_loppupvm DATE,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(viemariverkosto_alkupvm, viemariverkosto_loppupvm, '[]')) STORED,
    rakennus_prt Text
);

ALTER TABLE jkr.viemari_liitos OWNER TO jkr_admin;