-- ddl-end --
--
-- ALTER TABLE jkr.keskeytys DROP COLUMN IF EXISTS voimassaolo CASCADE;
ALTER TABLE jkr.keskeytys ADD COLUMN voimassaolo daterange GENERATED ALWAYS AS (daterange(coalesce(alkupvm, '-infinity'), coalesce(loppupvm, 'infinity'), '[]')) STORED;
-- ddl-end --




-- object: idx_sopimus_voimassaolo | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_sopimus_voimassaolo CASCADE;
CREATE INDEX idx_sopimus_voimassaolo ON jkr.sopimus
USING gist
(
	voimassaolo
);
-- ddl-end --

-- object: idx_keskeytys_voimassaolo | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_keskeytys_voimassaolo CASCADE;
CREATE INDEX idx_keskeytys_voimassaolo ON jkr.keskeytys
USING gist
(
	voimassaolo
);
-- ddl-end --


-- object: idx_velvoite_velvoitemalli_id | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_velvoite_velvoitemalli_id CASCADE;
CREATE INDEX idx_velvoite_velvoitemalli_id ON jkr.velvoite
USING btree
(
	velvoitemalli_id
);
-- ddl-end --

-- object: idx_kuljetus_jatetyyppi_id | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_kuljetus_jatetyyppi_id CASCADE;
CREATE INDEX idx_kuljetus_jatetyyppi_id ON jkr.kuljetus
USING btree
(
	jatetyyppi_id
);
-- ddl-end --
