CREATE OR REPLACE VIEW jkr.v_kohdevelvoitteet_distinct
 AS
   SELECT DISTINCT ON (kohde_id, velvoitemalli_kuvaus) velvoitemalli_kuvaus,
   velvoite_id,
   kohde_id,
   velvoitemalli_id,
   velvoitemalli_selite,
   voimassaolo,
   status_id,
   status_ok,
   status_tallennuspvm,
   status_jakso,
   (lower(status_jakso) || ' - '::text) || upper(status_jakso) AS jakso
   FROM jkr.v_kohdevelvoitteet_status
   ORDER BY kohde_id, velvoitemalli_kuvaus, status_tallennuspvm DESC NULLS LAST