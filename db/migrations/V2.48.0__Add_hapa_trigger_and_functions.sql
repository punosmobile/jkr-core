-- V2.48.0__Add_hapa_trigger_and_functions.sql

-- Funktio joka tarkistaa onko kohde biojätteen erilliskeräysalueella
CREATE OR REPLACE FUNCTION jkr.is_kohde_biojate_erilliskeraysalueella(kohde_id integer) 
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM jkr.kohde k
        JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id
        JOIN jkr.rakennus r ON r.id = kr.rakennus_id
        JOIN jkr.taajama t ON ST_Contains(t.geom, r.geom)
        WHERE k.id = kohde_id 
        AND t.vaesto_lkm >= 10000
    );
END;
$$ LANGUAGE plpgsql;

-- Funktio joka tarkistaa onko kohteella vähintään 5 huoneistoa
CREATE OR REPLACE FUNCTION jkr.has_kohde_vahintaan_5_huoneistoa(kohde_id integer)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM jkr.kohde k
        WHERE k.id = kohde_id
        AND (
            SELECT SUM(COALESCE((rak.huoneistomaara)::integer, 1))
            FROM jkr.kohteen_rakennukset kkr
            JOIN jkr.rakennus rak ON rak.id = kkr.rakennus_id
            WHERE kkr.kohde_id = k.id
        ) >= 5
    );
END;
$$ LANGUAGE plpgsql;

-- Funktio joka päivittää kohteen tyypin HAPA-aineiston ja ensisijaisuussääntöjen perusteella
CREATE OR REPLACE FUNCTION jkr.update_kohde_type_from_hapa()
RETURNS TRIGGER AS $$
BEGIN
    -- Päivitä kohteiden tyypit, joiden rakennukset ovat HAPA-aineistossa
    UPDATE jkr.kohde k
    SET kohdetyyppi_id = CASE 
        -- Säilytä asuinkiinteistö jos:
        -- - on biojätteen erilliskeräysalueella TAI
        -- - on hyötyjätealueella ja vähintään 5 huoneistoa
        WHEN k.kohdetyyppi_id = 7  -- asuinkiinteistö
        AND (
            jkr.is_kohde_biojate_erilliskeraysalueella(k.id)
            OR (
                jkr.is_kohde_biojate_erilliskeraysalueella(k.id)  -- hyötyjätealue sama kuin biojätealue
                AND jkr.has_kohde_vahintaan_5_huoneistoa(k.id)
            )
        ) THEN 7  -- säilytä asuinkiinteistönä
        
        -- BIOHAPA vahvempi kuin asuinkiinteistö biojätealueen ulkopuolella
        WHEN EXISTS (
            SELECT 1 
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON kr.rakennus_id = r.id
            JOIN jkr.hapa_aineisto ha ON r.prt = ha.rakennus_id_tunnus
            WHERE kr.kohde_id = k.id 
            AND ha.kohdetyyppi ILIKE 'biohapa'
            AND ha.voimassa && k.voimassaolo
        )
        AND NOT jkr.is_kohde_biojate_erilliskeraysalueella(k.id)
        THEN 6  -- biohapa
        
        -- HAPA vain jos ei ole asuinkiinteistö
        WHEN EXISTS (
            SELECT 1
            FROM jkr.kohteen_rakennukset kr
            JOIN jkr.rakennus r ON kr.rakennus_id = r.id
            JOIN jkr.hapa_aineisto ha ON r.prt = ha.rakennus_id_tunnus
            WHERE kr.kohde_id = k.id 
            AND ha.kohdetyyppi ILIKE 'hapa'
            AND ha.voimassa && k.voimassaolo
        ) 
        AND k.kohdetyyppi_id != 7  -- ei asuinkiinteistö
        THEN 5  -- hapa
        
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
COMMENT ON FUNCTION jkr.is_kohde_biojate_erilliskeraysalueella(integer) IS 
    'Tarkistaa sijaitseeko kohde biojätteen erilliskeräysalueella (taajama >= 10000 asukasta)';

COMMENT ON FUNCTION jkr.has_kohde_vahintaan_5_huoneistoa(integer) IS
    'Tarkistaa onko kohteella vähintään 5 huoneistoa';

COMMENT ON FUNCTION jkr.update_kohde_type_from_hapa() IS 
    'Funktio joka päivittää kohteiden tyypit HAPA-aineiston perusteella noudattaen määrittelyn ensisijaisuussääntöjä';

COMMENT ON TRIGGER trg_update_kohde_type_from_hapa ON jkr.hapa_aineisto IS
    'Triggeri joka suoritetaan kun HAPA-aineistoa muutetaan. Päivittää kohdetyypit automaattisesti.';