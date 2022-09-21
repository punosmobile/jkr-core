


-- [ Dropped objects ] --
ALTER TABLE jkr.facta_asia DROP CONSTRAINT IF EXISTS kohde_fk CASCADE;
-- ddl-end --
DROP INDEX IF EXISTS jkr.idx_facta_asia_kohde_id CASCADE;
-- ddl-end --
DROP TABLE IF EXISTS jkr.facta_asia CASCADE;
-- ddl-end --
DROP SEQUENCE IF EXISTS jkr.facta_asia_id_seq CASCADE;

DROP SCHEMA IF EXISTS jkr_facta CASCADE;
