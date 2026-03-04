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
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_dvv
GRANT USAGE ON SEQUENCES TO jkr_editor, jkr_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_qgis_projektit
GRANT USAGE ON SEQUENCES TO jkr_editor, jkr_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_dvv
GRANT SELECT ON TABLES TO jkr_viewer;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_dvv
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jkr_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr_dvv
GRANT ALL ON TABLES TO jkr_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT SELECT ON TABLES TO jkr_viewer;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jkr_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE jkr_admin IN SCHEMA jkr
GRANT ALL ON TABLES TO jkr_admin;