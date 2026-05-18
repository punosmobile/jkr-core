ALTER TABLE IF EXISTS jkr.velvoite
    ADD COLUMN loppupvm date;

ALTER TABLE IF EXISTS jkr.velvoiteyhteenveto
    ADD COLUMN loppupvm date;

DROP INDEX IF EXISTS jkr.uidx_velvoite_kohde_id_velvoitemalli_id;
CREATE UNIQUE INDEX IF NOT EXISTS uidx_velvoite_kohde_id_velvoitemalli_id
    ON jkr.velvoite USING btree
    (kohde_id ASC NULLS LAST, velvoitemalli_id ASC NULLS LAST, loppupvm DESC NULLS FIRST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

DROP INDEX IF EXISTS jkr.uidx_velvoiteyhteenveto_kohde_id_velvoiteyhteenvetomalli_id;
CREATE UNIQUE INDEX IF NOT EXISTS uidx_velvoiteyhteenveto_kohde_id_velvoiteyhteenvetomalli_id
    ON jkr.velvoiteyhteenveto USING btree
    (kohde_id ASC NULLS LAST, velvoiteyhteenvetomalli_id ASC NULLS LAST, loppupvm DESC NULLS FIRST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;