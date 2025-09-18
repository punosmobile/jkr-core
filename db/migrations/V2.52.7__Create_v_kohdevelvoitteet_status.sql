CREATE OR REPLACE VIEW jkr.v_kohdevelvoitteet_status
 AS
 SELECT v.id AS velvoite_id,
    v.kohde_id,
    v.velvoitemalli_id,
    m.selite AS velvoitemalli_selite,
    m.kuvaus AS velvoitemalli_kuvaus,
    m.voimassaolo,
    CURRENT_DATE <@ m.voimassaolo AS model_valid_now,
    s.id AS status_id,
    s.ok AS status_ok,
    s.tallennuspvm AS status_tallennuspvm,
    s.jakso AS status_jakso,
    s.jakso IS NOT NULL AND CURRENT_DATE <@ s.jakso AS status_current_now
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