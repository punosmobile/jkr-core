-- V2.48.0__Add_hapa_trigger.sql

-- Luodaan funktio joka päivittää kohteen tyypin HAPA-aineiston perusteella 
CREATE OR REPLACE FUNCTION jkr.update_kohde_type_from_hapa()
RETURNS TRIGGER AS $$
BEGIN
    -- Päivitä kohteiden tyypit, joiden rakennukset ovat HAPA-aineistossa
    UPDATE jkr.kohde k
    SET kohdetyyppi_id = CASE 
        -- Jos biohapa ja EI ole biojätteen erilliskeräysalueella
        -- (tässä vaiheessa emme tiedä erilliskeräysalueita, joten oletamme ettei ole)
        WHEN EXISTS (
            SELECT 1 
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON kr.rakennus_id = r.id
            JOIN jkr.hapa_aineisto ha ON r.prt = ha.rakennus_id_tunnus
            WHERE kr.kohde_id = k.id 
            AND ha.kohdetyyppi ILIKE 'biohapa'
            AND ha.voimassa && k.voimassaolo
        ) THEN 6  -- biohapa id
        
        -- Jos tavallinen hapa ja kohde EI ole asuinkiinteistö
        WHEN EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON kr.rakennus_id = r.id
            JOIN jkr.hapa_aineisto ha ON r.prt = ha.rakennus_id_tunnus
            WHERE kr.kohde_id = k.id 
            AND ha.kohdetyyppi ILIKE 'hapa'
            AND ha.voimassa && k.voimassaolo
        ) 
        AND k.kohdetyyppi_id != 7  -- asuinkiinteistö id
        THEN 5  -- hapa id
        
        ELSE k.kohdetyyppi_id  -- säilytä nykyinen tyyppi
    END
    WHERE EXISTS (
        SELECT 1
        FROM jkr.kohteen_rakennukset kr
        JOIN jkr.rakennus r ON kr.rakennus_id = r.id
        JOIN jkr.hapa_aineisto ha ON r.prt = ha.rakennus_id_tunnus
        WHERE kr.kohde_id = k.id
        AND ha.voimassa && k.voimassaolo
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Luodaan trigger joka suoritetaan HAPA-aineiston muuttuessa
DROP TRIGGER IF EXISTS trg_update_kohde_type_from_hapa ON jkr.hapa_aineisto;

CREATE TRIGGER trg_update_kohde_type_from_hapa
    AFTER INSERT OR UPDATE OR DELETE ON jkr.hapa_aineisto
    FOR EACH STATEMENT
    EXECUTE FUNCTION jkr.update_kohde_type_from_hapa();

-- Kommentit
COMMENT ON FUNCTION jkr.update_kohde_type_from_hapa() IS 
    'Funktio joka päivittää kohteiden tyypit HAPA-aineiston perusteella. Noudattaa määrittelyn ensisijaisuussääntöjä.';

COMMENT ON TRIGGER trg_update_kohde_type_from_hapa ON jkr.hapa_aineisto IS
    'Triggeri joka suoritetaan kun HAPA-aineistoa muutetaan. Päivittää kohdetyypit automaattisesti.';