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


CREATE OR REPLACE VIEW jkr.v_kohdevelvoitteet_status
 AS
 SELECT v.id AS velvoite_id,
    v.kohde_id,
    v.velvoitemalli_id,
    m.selite AS velvoitemalli_selite,
    m.kuvaus AS velvoitemalli_kuvaus,
    m.voimassaolo,
    CURRENT_DATE <@ m.voimassaolo AS voimassa,
    s.id AS status_id,
    s.ok AS status_ok,
    s.tallennuspvm AS status_tallennuspvm,
    s.jakso AS status_jakso,
    s.jakso IS NOT NULL AND CURRENT_DATE <@ s.jakso AS nykystatus,
    v.loppupvm AS velvoite_loppupvm
   FROM jkr.velvoite v
     JOIN jkr.velvoitemalli m ON m.id = v.velvoitemalli_id
     LEFT JOIN LATERAL ( SELECT s_1.id,
            s_1.ok,
            s_1.velvoite_id,
            s_1.tallennuspvm,
            s_1.jakso
           FROM jkr.velvoite_status s_1
          WHERE s_1.velvoite_id = v.id
          ORDER BY (upper(s_1.jakso)) DESC NULLS LAST, s_1.tallennuspvm DESC, s_1.id DESC
         LIMIT 1) s ON true
  WHERE s.ok = true;


CREATE OR REPLACE VIEW jkr.v_kohdevelvoitteet_distinct
 AS
 SELECT velvoite_id,
    kohde_id,
    velvoitemalli_id,
    velvoitemalli_selite,
    velvoitemalli_kuvaus || CASE WHEN velvoite_loppupvm IS NOT NULL THEN ('(' || velvoite_loppupvm || ')') ELSE '' END,
    voimassaolo,
    voimassa,
    status_id,
    status_ok,
    status_tallennuspvm,
    status_jakso,
    (lower(status_jakso) || ' - '::text) || upper(status_jakso) AS jakso,
    nykystatus
   FROM jkr.v_kohdevelvoitteet_status
  ORDER BY kohde_id, velvoitemalli_kuvaus, status_tallennuspvm DESC NULLS LAST;