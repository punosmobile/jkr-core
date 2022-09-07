GRANT SELECT ON ALL TABLES IN SCHEMA jkr TO jkr_viewer;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr TO jkr_editor;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr TO jkr_editor;

GRANT SELECT ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_viewer;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_editor;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr_koodistot TO jkr_editor;

GRANT SELECT ON ALL TABLES IN SCHEMA jkr_facta TO jkr_viewer;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_facta TO jkr_editor;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr_facta TO jkr_editor;

GRANT SELECT ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_viewer;

GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_editor;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr_osoite TO jkr_editor;

ALTER TABLE jkr.qgis_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY kaikki_luettavissa ON jkr.qgis_projects
    FOR SELECT
        USING (TRUE);

CREATE POLICY muut_paitsi_master_muokattavissa ON jkr.qgis_projects
    FOR ALL
        USING (name <> 'Jätteenkuljetusrekisteri [Master]');

