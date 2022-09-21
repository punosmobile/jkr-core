CREATE SCHEMA jkr_qgis_projektit;

-- object: jkr_qgis_projektit.qgis_projects | type: TABLE --
-- DROP TABLE IF EXISTS jkr_qgis_projektit.qgis_projects CASCADE;
CREATE TABLE jkr_qgis_projektit.qgis_projects (
	name text NOT NULL,
	metadata jsonb,
	content bytea,
	CONSTRAINT qgis_projects_pkey PRIMARY KEY (name)
);
-- ddl-end --
COMMENT ON TABLE jkr_qgis_projektit.qgis_projects IS E'QGIS-projektit sisältävä taulu';
-- ddl-end --
COMMENT ON COLUMN jkr_qgis_projektit.qgis_projects.name IS E'QGIS-projektin nimi';
-- ddl-end --
COMMENT ON COLUMN jkr_qgis_projektit.qgis_projects.metadata IS E'QGIS-projektin metadatatiedot jsonb-muodossa';
-- ddl-end --
COMMENT ON COLUMN jkr_qgis_projektit.qgis_projects.content IS E'QGIS-projektitiedosto. Tämän kentän sisältö on tarkoitettu ainoastaan QGISin käyttöön.';
-- ddl-end --
ALTER TABLE jkr_qgis_projektit.qgis_projects OWNER TO jkr_admin;
-- ddl-end --


ALTER TABLE jkr_qgis_projektit.qgis_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY kaikki_luettavissa ON jkr_qgis_projektit.qgis_projects
    FOR SELECT
        USING (TRUE);

CREATE POLICY muut_paitsi_master_muokattavissa ON jkr_qgis_projektit.qgis_projects
    FOR ALL
        USING (name <> 'Jätteenkuljetusrekisteri [Master]');

