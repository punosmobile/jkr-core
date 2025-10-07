DO $$
DECLARE
    view_name TEXT;
BEGIN
    FOR view_name IN 
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'jkr'
    LOOP
        EXECUTE format('GRANT ALL ON TABLE jkr.%I TO jkr_admin', view_name);
        EXECUTE format('GRANT INSERT, UPDATE, DELETE ON TABLE jkr.%I TO jkr_editor', view_name);
        EXECUTE format('GRANT SELECT ON TABLE jkr.%I TO jkr_viewer', view_name);
    END LOOP;
END $$;

ALTER DEFAULT PRIVILEGES IN SCHEMA jkr
GRANT ALL ON TABLES TO jkr_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA jkr
GRANT INSERT, UPDATE, DELETE ON TABLES TO jkr_editor;

ALTER DEFAULT PRIVILEGES IN SCHEMA jkr
GRANT SELECT ON TABLES TO jkr_viewer;
