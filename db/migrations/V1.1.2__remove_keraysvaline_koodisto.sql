-- [ Dropped objects ] --
ALTER TABLE jkr.keraysvaline
  DROP CONSTRAINT IF EXISTS keraysvalinetyyppi_fk CASCADE;

-- ddl-end --
DROP INDEX IF EXISTS jkr.uidx_osoite_rakennus_katu_numero CASCADE;

-- ddl-end --
DROP TABLE IF EXISTS jkr_koodistot.keraysvalinetyyppi CASCADE;

-- ddl-end --
ALTER TABLE jkr.keraysvaline
  DROP COLUMN IF EXISTS keraysvalinetyyppi_koodi CASCADE;

-- ddl-end --
ALTER TABLE jkr.sopimus
  ADD COLUMN aluejatepiste_asiakas boolean NOT NULL DEFAULT FALSE;

-- ddl-end --
ALTER TABLE jkr.keraysvaline
  ADD COLUMN keraysvalinetyyppi text;

-- ddl-end --
COMMENT ON COLUMN jkr.keraysvaline.koko IS E'keräysvälineen koko litroina';

