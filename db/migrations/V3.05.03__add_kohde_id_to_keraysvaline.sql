ALTER TABLE jkr.keraysvaline
ADD COLUMN kohde_id integer REFERENCES jkr.kohde(id);

ALTER TABLE jkr.kompostori
ADD COLUMN onko_liete Boolean default false;

-- Require either sopimus or kohde id
ALTER TABLE jkr.keraysvaline alter sopimus_id drop not null;
ALTER TABLE jkr.keraysvaline add CONSTRAINT sopimus_or_kohde_id CHECK
(sopimus_id IS NOT NULL or kohde_id IS NOT NULL);