CREATE OR REPLACE VIEW jkr.v_kohdevelvoitteet_distinct
 AS
 SELECT velvoite_id,
    kohde_id,
    velvoitemalli_id,
    velvoitemalli_selite,
    velvoitemalli_kuvaus,
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