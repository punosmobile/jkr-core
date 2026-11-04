-- Owners and privileges, run as the last repeatable migration. Flyway runs this file
-- only when it changes, so edit this comment in the same release as a repeatable
-- migration that recreates one of the materialized views below. 0.8.1:
-- R__03_v_velvoitteita_rikkovat and R__v_kuljetus_ja_kompostorit_kohteet.

-- pgaudit role
DO
$do$
BEGIN
   IF EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'auditor') THEN

      RAISE NOTICE 'Role "auditor" already exists. Skipping.';
   ELSE
      CREATE ROLE auditor WITH
        NOLOGIN
        NOSUPERUSER
        NOINHERIT
        NOCREATEDB
        NOCREATEROLE
        NOREPLICATION
        NOBYPASSRLS;

        COMMENT ON ROLE auditor IS 'Role for monitoring GDPR compliance. Allows limiting of monitored tables for audit logs to reduce volume of unnecessary lines';
   END IF;
END
$do$;

GRANT SELECT, UPDATE ON TABLE jkr_qgis_projektit.qgis_projects TO jkr_admin;
GRANT SELECT ON TABLE jkr_qgis_projektit.qgis_projects TO jkr_editor;
GRANT REFERENCES, TRUNCATE, DELETE, UPDATE, INSERT, SELECT, TRIGGER ON TABLE jkr_qgis_projektit.qgis_projects TO jkr_admin;
GRANT INSERT, SELECT, UPDATE ON TABLE jkr_qgis_projektit.qgis_projects TO jkr_editor;
GRANT CREATE, USAGE ON SCHEMA jkr_dvv TO jkr_admin;
GRANT USAGE ON SCHEMA jkr_dvv TO jkr_viewer;
GRANT SELECT, UPDATE ON TABLE jkr_qgis_projektit.qgis_api_credentials TO jkr_admin;
GRANT SELECT ON TABLE jkr_qgis_projektit.qgis_api_credentials TO jkr_editor;
GRANT REFERENCES, TRUNCATE, DELETE, UPDATE, INSERT, SELECT, TRIGGER ON TABLE jkr_qgis_projektit.qgis_api_credentials TO jkr_admin;
GRANT INSERT, SELECT, UPDATE ON TABLE jkr_qgis_projektit.qgis_api_credentials TO jkr_editor;
GRANT CREATE, USAGE ON SCHEMA jkr_dvv TO jkr_admin;
GRANT USAGE ON SCHEMA jkr_dvv TO jkr_viewer;

ALTER TABLE IF EXISTS jkr.v_kompostorien_kohteet_kolmeviimeista
    OWNER TO jkr_admin;

GRANT ALL ON TABLE jkr.v_kompostorien_kohteet_kolmeviimeista TO jkr_admin;
GRANT INSERT, DELETE, UPDATE ON TABLE jkr.v_kompostorien_kohteet_kolmeviimeista TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_kompostorien_kohteet_kolmeviimeista TO jkr_viewer;

ALTER TABLE IF EXISTS jkr.v_kuljetustietojen_kohteet_kolmeviimeista
    OWNER TO jkr_admin;

ALTER TABLE IF EXISTS jkr.v_velvoiteyhteenvetojen_kohteet
    OWNER TO jkr_admin;

ALTER TABLE IF EXISTS jkr.v_velvoitteiden_kohteet
    OWNER TO jkr_admin;

ALTER TABLE IF EXISTS jkr.nearby_buildings
    OWNER TO jkr_admin;

GRANT ALL ON TABLE jkr.v_kuljetustietojen_kohteet_kolmeviimeista TO jkr_admin;
GRANT INSERT, DELETE, UPDATE ON TABLE jkr.v_kuljetustietojen_kohteet_kolmeviimeista TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_kuljetustietojen_kohteet_kolmeviimeista TO jkr_viewer;


GRANT ALL ON TABLE jkr.v_velvoitteiden_kohteet TO jkr_admin;
GRANT INSERT, DELETE, UPDATE ON TABLE jkr.v_velvoitteiden_kohteet TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_velvoitteiden_kohteet TO jkr_viewer;

GRANT ALL ON TABLE jkr.v_velvoiteyhteenvetojen_kohteet TO jkr_admin;
GRANT INSERT, DELETE, UPDATE ON TABLE jkr.v_velvoiteyhteenvetojen_kohteet TO jkr_editor;
GRANT SELECT ON TABLE jkr.v_velvoiteyhteenvetojen_kohteet TO jkr_viewer;

ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_qgis_projektit
GRANT SELECT ON TABLES TO jkr_viewer;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_qgis_projektit
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jkr_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_qgis_projektit
GRANT ALL ON TABLES TO jkr_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT USAGE ON SEQUENCES TO jkr_editor, jkr_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_qgis_projektit
GRANT USAGE ON SEQUENCES TO jkr_editor, jkr_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT SELECT ON TABLES TO jkr_viewer;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jkr_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT ALL ON TABLES TO jkr_admin;

-- tables to audit with pgaudit role
GRANT SELECT ON TABLE jkr.osapuoli TO auditor;
GRANT SELECT ON TABLE jkr.ulkoinen_asiakastieto TO auditor;
GRANT SELECT ON TABLE jkr.v_ulkoinen_asiakastieto_tiedontuottajalla TO auditor;
GRANT SELECT ON TABLE jkr.v_kohteen_yhteystiedot TO auditor;
GRANT SELECT ON TABLE jkr.v_kohteen_viranomaispaatokset TO auditor;
GRANT SELECT ON TABLE jkr.v_kohteen_osapuolet_roolilla TO auditor;
GRANT SELECT ON TABLE jkr.v_kohteen_osapuolet TO auditor;
GRANT SELECT ON TABLE jkr.v_kohdehaku TO auditor;

-- Audit every jkr_dvv table.
GRANT SELECT ON ALL TABLES IN SCHEMA jkr_dvv TO auditor;

-- Default privileges for jkr_dvv. The DVV import (ogr2ogr -overwrite) drops and
-- recreates the tables, so per-table grants are lost on each import and only default
-- privileges survive it. Default privileges only apply to objects created by the named
-- role, and the import user (JKR_USER) differs between environments (jkr_admin,
-- punos_admin), so set them for every known admin role that exists plus the role
-- running this migration (Flyway and the imports both connect as JKR_USER).
DO
$do$
DECLARE
   creator text;
BEGIN
   FOR creator IN
      SELECT DISTINCT rolname FROM pg_catalog.pg_roles
      WHERE rolname IN ('jkr_admin', 'punos_admin', current_user)
   LOOP
      BEGIN
         EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA jkr_dvv
            GRANT SELECT ON TABLES TO jkr_viewer, auditor', creator);
         EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA jkr_dvv
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jkr_editor', creator);
         EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA jkr_dvv
            GRANT ALL ON TABLES TO jkr_admin', creator);
         EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA jkr_dvv
            GRANT USAGE ON SEQUENCES TO jkr_editor, jkr_admin', creator);
      EXCEPTION WHEN insufficient_privilege THEN
         RAISE NOTICE 'Cannot set default privileges for role "%": not a member. Skipping.', creator;
      END;
   END LOOP;
END
$do$;
