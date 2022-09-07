ALTER TABLE jkr.ulkoinen_kohdetunnus RENAME TO ulkoinen_asiakastieto;

ALTER TABLE jkr.ulkoinen_asiakastieto
    ADD COLUMN ulkoinen_asiakastieto jsonb;

