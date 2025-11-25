CREATE OR REPLACE VIEW jkr.v_velvoiteyhteenveto_status
 AS
 SELECT id,
    (lower(jakso) || ' - '::text) || upper(jakso) AS jakso,
    ok,
    velvoiteyhteenveto_id,
    tallennuspvm
   FROM jkr.velvoiteyhteenveto_status
   ORDER BY jakso DESC NULLS LAST;
