ALTER TABLE jkr.keraysvaline ALTER koko TYPE integer;
ALTER TABLE jkr.keraysvaline ALTER koko DROP NOT NULL;
ALTER TABLE jkr.keraysvaline RENAME COLUMN koko TO tilavuus;

COMMENT ON COLUMN jkr.keraysvaline.tilavuus IS E'Keräysväline(id)en tilavuus litroina';
