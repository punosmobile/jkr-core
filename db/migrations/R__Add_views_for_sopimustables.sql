CREATE OR REPLACE VIEW jkr.v_sopimukset
 AS
 SELECT
    s.id sopimus_id,
    s.kohde_id,
    jt.selite jatetyyppi_selite,
    s.voimassaolo sopimus_voimassaolo,
    s.kimppaisanta_kohde_id
   FROM jkr.sopimus s
     JOIN jkr_koodistot.jatetyyppi jt ON jt.id = s.jatetyyppi_id;

COMMENT ON VIEW jkr.v_sopimukset IS E'Apunäkymä velvoitekyselyille. Sisältää mm. jätetyypin selitteen.';

create or replace view jkr.v_tyhjennysvalit as
select
  s.kohde_id,
  s.id sopimus_id,
  s.voimassaolo sopimus_voimassaolo,
  jt.selite jatetyyppi_selite,
  tv.alkuvko,
  tv.loppuvko,
  tv.tyhjennysvali
FROM jkr.sopimus s
  join jkr.tyhjennysvali tv on s.id = tv.sopimus_id
  JOIN jkr_koodistot.jatetyyppi jt ON jt.id = s.jatetyyppi_id;

COMMENT ON VIEW jkr.v_tyhjennysvalit IS E'Apunäkymä velvoitekyselyille. Sisältää mm. jätetyypin selitteen ja sopimuksen voimassaoloajan.';


create or replace view jkr.v_keskeytys as
select
  s.kohde_id,
  s.id sopimus_id,
  s.voimassaolo sopimus_voimassaolo,
  jt.selite jatetyyppi_selite,
  ke.voimassaolo keskeytys_voimassa
FROM jkr.sopimus s
  join jkr.keskeytys ke on s.id = ke.sopimus_id
  JOIN jkr_koodistot.jatetyyppi jt ON jt.id = s.jatetyyppi_id;

COMMENT ON VIEW jkr.v_keskeytys IS E'Apunäkymä velvoitekyselyille. Sisältää mm. jätetyypin selitteen ja sopimuksen voimassaoloajan.';

create or replace view jkr.v_keraysvalineet as
select
  s.kohde_id,
  s.id sopimus_id,
  s.voimassaolo sopimus_voimassaolo,
  kv.pvm,
  jt.selite jatetyyppi_selite,
  kvt.selite keraysvalinetyyppi_selite
FROM jkr.sopimus s
  join jkr.keraysvaline kv on s.id = kv.sopimus_id
  JOIN jkr_koodistot.jatetyyppi jt ON jt.id = s.jatetyyppi_id
  join jkr_koodistot.keraysvalinetyyppi kvt on kv.keraysvalinetyyppi_id = kvt.id
;

COMMENT ON VIEW jkr.v_keraysvalineet IS E'Apunäkymä velvoitekyselyille. Sisältää mm. jätetyypin selitteen ja sopimuksen voimassaoloajan.';
