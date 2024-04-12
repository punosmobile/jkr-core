CREATE OR REPLACE VIEW jkr.v_velvoite_status AS
SELECT id,
       lower(jakso) || ' - ' || upper(jakso) AS jakso,
       ok,
       velvoite_id,
       tallennuspvm
FROM jkr.velvoite_status;