DO
$do$
BEGIN
   IF EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'jkr_viewer') THEN
      RAISE NOTICE 'Role "jkr_viewer" already exists. Skipping.';
   ELSE
      CREATE ROLE jkr_viewer;
   END IF;
END
$do$;

DO
$do$
BEGIN
   IF EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'jkr_editor') THEN
      RAISE NOTICE 'Role "jkr_editor" already exists. Skipping.';
   ELSE
      CREATE ROLE jkr_editor;
   END IF;
END
$do$;


GRANT jkr_viewer TO jkr_editor;
