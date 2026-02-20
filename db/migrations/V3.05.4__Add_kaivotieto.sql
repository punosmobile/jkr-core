-- Kaivotiedot-taulu lietevelvoitteiden hallintaan
-- LAH-415: "Kaivotiedot" ja "Kaivotiedon lopetus" tietojen vienti kantaan

-- Koodistotaulu kaivotietotyypeille
CREATE TABLE IF NOT EXISTS jkr_koodistot.kaivotietotyyppi (
    id serial PRIMARY KEY,
    selite text NOT NULL UNIQUE
);

ALTER TABLE jkr_koodistot.kaivotietotyyppi OWNER TO jkr_admin;
GRANT SELECT ON jkr_koodistot.kaivotietotyyppi TO jkr_viewer;

COMMENT ON TABLE jkr_koodistot.kaivotietotyyppi IS 'Kaivotietotyypit: Kantovesi, Saostussäiliö, Pienpuhdistamo, Umpisäiliö, Vain harmaat vedet';

-- Kaivotieto-taulu
CREATE TABLE IF NOT EXISTS jkr.kaivotieto (
    id serial PRIMARY KEY,
    kohde_id integer NOT NULL REFERENCES jkr.kohde(id) ON DELETE CASCADE,
    kaivotietotyyppi_id integer NOT NULL REFERENCES jkr_koodistot.kaivotietotyyppi(id),
    alkupvm date NOT NULL,
    loppupvm date,
    voimassaolo daterange GENERATED ALWAYS AS (daterange(coalesce(alkupvm, '-infinity'), coalesce(loppupvm, 'infinity'), '[]')) STORED,
    tietolahde text,
    tiedontuottaja_tunnus char(3) REFERENCES jkr_koodistot.tiedontuottaja(tunnus),
    luotu timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    muokattu timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE jkr.kaivotieto OWNER TO jkr_admin;
GRANT SELECT ON jkr.kaivotieto TO jkr_viewer;
GRANT SELECT, INSERT, UPDATE, DELETE ON jkr.kaivotieto TO jkr_editor;
GRANT USAGE, SELECT ON SEQUENCE jkr.kaivotieto_id_seq TO jkr_editor;

-- Indeksit
CREATE INDEX IF NOT EXISTS idx_kaivotieto_kohde_id ON jkr.kaivotieto(kohde_id);
CREATE INDEX IF NOT EXISTS idx_kaivotieto_kaivotietotyyppi_id ON jkr.kaivotieto(kaivotietotyyppi_id);
CREATE INDEX IF NOT EXISTS idx_kaivotieto_voimassaolo ON jkr.kaivotieto USING gist(voimassaolo);

-- Uniikki rajoite: sama kohde + tyyppi + alkupvm ei saa olla kahdesti
CREATE UNIQUE INDEX IF NOT EXISTS idx_kaivotieto_unique 
ON jkr.kaivotieto(kohde_id, kaivotietotyyppi_id, alkupvm);

-- Kommentit
COMMENT ON TABLE jkr.kaivotieto IS 'Kohteen kaivotiedot (lietevelvoitteiden hallinta). Sisältää tiedot kohteen jätevesijärjestelmistä.';
COMMENT ON COLUMN jkr.kaivotieto.kohde_id IS 'Viittaus kohteeseen';
COMMENT ON COLUMN jkr.kaivotieto.kaivotietotyyppi_id IS 'Kaivotietotyyppi: Kantovesi, Saostussäiliö, Pienpuhdistamo, Umpisäiliö, Vain harmaat vedet';
COMMENT ON COLUMN jkr.kaivotieto.alkupvm IS 'Kaivotiedon alkamispäivämäärä (Vastausaika Excel-tiedostosta)';
COMMENT ON COLUMN jkr.kaivotieto.loppupvm IS 'Kaivotiedon päättymispäivämäärä (asetetaan lopetustiedostosta)';
COMMENT ON COLUMN jkr.kaivotieto.tietolahde IS 'Tiedon lähde (Excel-tiedoston Tietolähde-sarake)';
COMMENT ON COLUMN jkr.kaivotieto.tiedontuottaja_tunnus IS 'Tiedontuottajan tunnus';

-- Triggeri muokattu-kentän päivittämiseen
CREATE OR REPLACE FUNCTION jkr.update_kaivotieto_muokattu()
RETURNS TRIGGER AS $$
BEGIN
    NEW.muokattu = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_kaivotieto_muokattu
    BEFORE UPDATE ON jkr.kaivotieto
    FOR EACH ROW
    EXECUTE FUNCTION jkr.update_kaivotieto_muokattu();

-- Näkymä kaivotiedoille kohteen tiedoilla
CREATE OR REPLACE VIEW jkr.v_kaivotiedot AS
SELECT 
    kt.id,
    kt.kohde_id,
    k.nimi AS kohde_nimi,
    ktt.id AS kaivotietotyyppi_id,
    ktt.selite AS kaivotietotyyppi,
    kt.alkupvm,
    kt.loppupvm,
    kt.voimassaolo,
    kt.tietolahde,
    kt.tiedontuottaja_tunnus,
    t.nimi AS tiedontuottaja_nimi,
    kt.luotu,
    kt.muokattu
FROM jkr.kaivotieto kt
JOIN jkr.kohde k ON kt.kohde_id = k.id
JOIN jkr_koodistot.kaivotietotyyppi ktt ON kt.kaivotietotyyppi_id = ktt.id
LEFT JOIN jkr_koodistot.tiedontuottaja t ON kt.tiedontuottaja_tunnus = t.tunnus;

GRANT SELECT ON jkr.v_kaivotiedot TO jkr_viewer;

COMMENT ON VIEW jkr.v_kaivotiedot IS 'Näkymä kaivotiedoista kohteen ja tyypin tiedoilla';
