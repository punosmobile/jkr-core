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
