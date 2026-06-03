-- V3.05.27__Add_sote_aineisto.sql

-- Luodaan sote_aineisto-taulu vastaamaan aineiston rakennetta
CREATE TABLE jkr.sote_aineisto (
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
    kohdetyyppi VARCHAR(10),            -- "sote"
    tuonti_pvm TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    voimassa DATERANGE NOT NULL DEFAULT daterange(CURRENT_DATE, NULL)
);

-- Indeksit hakujen optimointiin
CREATE INDEX idx_sote_aineisto_rakennus_id_tunnus 
ON jkr.sote_aineisto(rakennus_id_tunnus);

CREATE INDEX idx_sote_aineisto_kohde_tunnus 
ON jkr.sote_aineisto(kohde_tunnus);

CREATE INDEX idx_sote_aineisto_asiakasnro 
ON jkr.sote_aineisto(asiakasnro);

CREATE INDEX idx_sote_aineisto_postinumero 
ON jkr.sote_aineisto(postinumero);

CREATE INDEX idx_sote_aineisto_kohdetyyppi 
ON jkr.sote_aineisto(kohdetyyppi);

-- GiST-indeksi daterange-hauille
CREATE INDEX idx_sote_aineisto_voimassa 
ON jkr.sote_aineisto USING GIST (voimassa);

-- Kommentit
COMMENT ON TABLE jkr.sote_aineisto IS 'sote- ja BIOsote-kohteiden erikseen toimitettava aineisto';
COMMENT ON COLUMN jkr.sote_aineisto.rakennus_id_tunnus IS 'Rakennuksen tunniste';
COMMENT ON COLUMN jkr.sote_aineisto.kohde_tunnus IS 'Kohteen tunniste';
COMMENT ON COLUMN jkr.sote_aineisto.sijaintikunta IS 'Rakennuksen sijaintikunta';
COMMENT ON COLUMN jkr.sote_aineisto.asiakasnro IS 'Asiakasnumero';
COMMENT ON COLUMN jkr.sote_aineisto.rakennus_id_tunnus2 IS 'Rakennuksen tunniste (toistuva)';
COMMENT ON COLUMN jkr.sote_aineisto.katunimi_fi IS 'Kadun nimi suomeksi';
COMMENT ON COLUMN jkr.sote_aineisto.talon_numero IS 'Rakennuksen numero';
COMMENT ON COLUMN jkr.sote_aineisto.postinumero IS 'Postinumero';
COMMENT ON COLUMN jkr.sote_aineisto.postitoimipaikka_fi IS 'Postitoimipaikka suomeksi';
COMMENT ON COLUMN jkr.sote_aineisto.kohdetyyppi IS 'Kohteen tyyppi (sote/biosote)';
COMMENT ON COLUMN jkr.sote_aineisto.tuonti_pvm IS 'Aineiston tuontipäivämäärä';
COMMENT ON COLUMN jkr.sote_aineisto.voimassa IS 'Tiedon voimassaoloaika';

-- Tarkistus kohdetyypille (case-insensitive)
ALTER TABLE jkr.sote_aineisto 
ADD CONSTRAINT check_kohdetyyppi 
CHECK (LOWER(kohdetyyppi) IN ('sote'));


-- FUNCTION: jkr.update_kohde_type_from_sote()

-- DROP FUNCTION IF EXISTS jkr.update_kohde_type_from_sote();

CREATE OR REPLACE FUNCTION jkr.update_kohde_type_from_sote()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    -- Päivitä kohteiden tyypit, joiden rakennukset ovat sote-aineistossa
    UPDATE jkr.kohde k
    SET kohdetyyppi_id = CASE 
        -- sote
        WHEN EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON kr.rakennus_id = r.id
            JOIN jkr.sote_aineisto ha ON r.prt = ha.rakennus_id_tunnus
            WHERE kr.kohde_id = k.id 
            AND ha.kohdetyyppi ILIKE 'sote'
            AND ha.voimassa && k.voimassaolo
        ) 
        THEN 9  -- sote
        
        ELSE k.kohdetyyppi_id  -- säilytä nykyinen tyyppi
    END
    WHERE EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        JOIN jkr.rakennus r ON kr.rakennus_id = r.id
        JOIN jkr.sote_aineisto ha ON r.prt = ha.rakennus_id_tunnus
        WHERE kr.kohde_id = k.id
        AND ha.voimassa && k.voimassaolo
    );

    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION jkr.update_kohde_type_from_sote()
    OWNER TO jkr_admin;

COMMENT ON FUNCTION jkr.update_kohde_type_from_sote()
    IS 'Funktio joka päivittää kohteiden tyypit sote-aineiston perusteella noudattaen määrittelyn ensisijaisuussääntöjä';


-- Trigger: trg_update_kohde_type_from_sote

-- DROP TRIGGER IF EXISTS trg_update_kohde_type_from_sote ON jkr.sote_aineisto;

CREATE OR REPLACE TRIGGER trg_update_kohde_type_from_sote
    AFTER INSERT OR UPDATE 
    ON jkr.sote_aineisto
    FOR EACH STATEMENT
    EXECUTE FUNCTION jkr.update_kohde_type_from_sote();

COMMENT ON TRIGGER trg_update_kohde_type_from_sote ON jkr.sote_aineisto
    IS 'Triggeri joka suoritetaan kun sote-aineistoa muutetaan. Päivittää kohdetyypit automaattisesti.';