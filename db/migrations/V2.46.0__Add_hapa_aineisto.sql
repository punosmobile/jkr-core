-- V2.46.0__Add_hapa_aineisto.sql

-- Luodaan hapa_aineisto-taulu vastaamaan aineiston rakennetta
CREATE TABLE jkr.hapa_aineisto (
    id SERIAL PRIMARY KEY,
    rakennus_id_tunnus VARCHAR(50),     -- Esim. "100192554V"
    kohde_tunnus VARCHAR(50),           -- Esim. "098"
    sijaintikunta VARCHAR(100),         -- Esim. "001"
    asiakasnro VARCHAR(50),             -- Esim. "03-0009352-00"
    rakennus_id_tunnus2 VARCHAR(50),    -- Toistuva Rakennus-ID
    katunimi_fi VARCHAR(100),           -- Esim. "Aikkalantie"
    talon_numero VARCHAR(20),           -- Esim. "205"
    postinumero VARCHAR(5),             -- Esim. "15880"
    postitoimipaikka_fi VARCHAR(100),   -- Esim. "Hollola"
    kohdetyyppi VARCHAR(10),            -- "hapa" tai "biohapa"
    tuonti_pvm TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    voimassa DATERANGE NOT NULL DEFAULT daterange(CURRENT_DATE, NULL)
);

-- Indeksit hakujen optimointiin
CREATE INDEX idx_hapa_aineisto_rakennus_id_tunnus 
ON jkr.hapa_aineisto(rakennus_id_tunnus);

CREATE INDEX idx_hapa_aineisto_kohde_tunnus 
ON jkr.hapa_aineisto(kohde_tunnus);

CREATE INDEX idx_hapa_aineisto_asiakasnro 
ON jkr.hapa_aineisto(asiakasnro);

CREATE INDEX idx_hapa_aineisto_postinumero 
ON jkr.hapa_aineisto(postinumero);

CREATE INDEX idx_hapa_aineisto_kohdetyyppi 
ON jkr.hapa_aineisto(kohdetyyppi);

-- GiST-indeksi daterange-hauille
CREATE INDEX idx_hapa_aineisto_voimassa 
ON jkr.hapa_aineisto USING GIST (voimassa);

-- Kommentit
COMMENT ON TABLE jkr.hapa_aineisto IS 'HAPA- ja BIOHAPA-kohteiden erikseen toimitettava aineisto';
COMMENT ON COLUMN jkr.hapa_aineisto.rakennus_id_tunnus IS 'Rakennuksen tunniste';
COMMENT ON COLUMN jkr.hapa_aineisto.kohde_tunnus IS 'Kohteen tunniste';
COMMENT ON COLUMN jkr.hapa_aineisto.sijaintikunta IS 'Rakennuksen sijaintikunta';
COMMENT ON COLUMN jkr.hapa_aineisto.asiakasnro IS 'Asiakasnumero';
COMMENT ON COLUMN jkr.hapa_aineisto.rakennus_id_tunnus2 IS 'Rakennuksen tunniste (toistuva)';
COMMENT ON COLUMN jkr.hapa_aineisto.katunimi_fi IS 'Kadun nimi suomeksi';
COMMENT ON COLUMN jkr.hapa_aineisto.talon_numero IS 'Rakennuksen numero';
COMMENT ON COLUMN jkr.hapa_aineisto.postinumero IS 'Postinumero';
COMMENT ON COLUMN jkr.hapa_aineisto.postitoimipaikka_fi IS 'Postitoimipaikka suomeksi';
COMMENT ON COLUMN jkr.hapa_aineisto.kohdetyyppi IS 'Kohteen tyyppi (hapa/biohapa)';
COMMENT ON COLUMN jkr.hapa_aineisto.tuonti_pvm IS 'Aineiston tuontipäivämäärä';
COMMENT ON COLUMN jkr.hapa_aineisto.voimassa IS 'Tiedon voimassaoloaika';

-- Tarkistus kohdetyypille (case-insensitive)
ALTER TABLE jkr.hapa_aineisto 
ADD CONSTRAINT check_kohdetyyppi 
CHECK (LOWER(kohdetyyppi) IN ('hapa', 'biohapa'));