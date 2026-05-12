-- Flyway afterMigration hook (After successful Migrate runs)
-- Make sure we have all permissions setup right after each migration.

SET LOCAL client_min_messages TO ERROR;

GRANT CONNECT ON DATABASE ${flyway:database} TO jkr_viewer;

-- jkr schema
GRANT USAGE ON SCHEMA jkr TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr TO jkr_editor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr TO jkr_editor;

-- jkr_koodistot schema
GRANT USAGE ON SCHEMA jkr_koodistot TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_editor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr_koodistot TO jkr_editor;

-- jkr_osoite schema
GRANT USAGE ON SCHEMA jkr_osoite TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_editor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr_osoite TO jkr_editor;

-- jkr_qgis_projektit schema
GRANT USAGE ON SCHEMA jkr_qgis_projektit TO jkr_editor;

-- Siivoa voimassa olevat kohteet, joilla ei ole yhtään rakennusta.
-- Turvaverkko LAH-593: bugit kohteiden yhdistämisessä/uudelleenmuodostuksessa ovat
-- voineet jättää kantaan voimassa olevia kohteita ilman rakennuksia, jolloin
-- raporteille jää rivejä ilman PRT:tä. Päättyneitä (loppupvm IS NOT NULL) tyhjiä
-- kohteita ei kosketa, koska ne eivät päädy raporteille. Aja joka migraatioajon
-- yhteydessä.
DO $$
DECLARE
    poistettavat_ids INTEGER[];
    poistettavat_count INTEGER;
    poistettu_count INTEGER;
    velvoite_count INTEGER;
    yhteenveto_count INTEGER;
BEGIN
    SELECT ARRAY_AGG(k.id) INTO poistettavat_ids
    FROM jkr.kohde k
    WHERE k.loppupvm IS NULL
      AND NOT EXISTS (
        SELECT 1 FROM jkr.kohteen_rakennukset kr WHERE kr.kohde_id = k.id
      );

    poistettavat_count := COALESCE(ARRAY_LENGTH(poistettavat_ids, 1), 0);

    IF poistettavat_count > 0 THEN
        RAISE NOTICE 'Löydettiin % voimassa olevaa kohdetta ilman rakennuksia, poistetaan...', poistettavat_count;

        -- velvoite ja velvoiteyhteenveto on määritelty ON DELETE RESTRICT, joten
        -- poistetaan ne ensin manuaalisesti (niiden statukset poistuvat CASCADE:lla).
        WITH d AS (
            DELETE FROM jkr.velvoite WHERE kohde_id = ANY(poistettavat_ids) RETURNING 1
        )
        SELECT COUNT(*) INTO velvoite_count FROM d;

        WITH d AS (
            DELETE FROM jkr.velvoiteyhteenveto WHERE kohde_id = ANY(poistettavat_ids) RETURNING 1
        )
        SELECT COUNT(*) INTO yhteenveto_count FROM d;

        RAISE NOTICE 'Poistettu % velvoitetta ja % velvoiteyhteenvetoa orpoista kohteista', velvoite_count, yhteenveto_count;

        WITH deleted AS (
            DELETE FROM jkr.kohde k WHERE k.id = ANY(poistettavat_ids) RETURNING k.id
        )
        SELECT COUNT(*) INTO poistettu_count FROM deleted;

        RAISE NOTICE 'Poistettu % voimassa olevaa kohdetta ilman rakennuksia', poistettu_count;
    END IF;
END $$;
