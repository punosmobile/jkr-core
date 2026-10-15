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
COMMENT ON COLUMN jkr.v_sopimukset.sopimus_id IS E'Sopimuksen yksilöivä tunniste (jkr.sopimus.id).';
COMMENT ON COLUMN jkr.v_sopimukset.kohde_id IS E'Viittaus kohteeseen, jota sopimus koskee.';
COMMENT ON COLUMN jkr.v_sopimukset.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_sopimukset.sopimus_voimassaolo IS E'Sopimuksen voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_sopimukset.kimppaisanta_kohde_id IS E'Kimppasopimuksessa viittaus kimppaisäntänä toimivaan kohteeseen.';

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
COMMENT ON COLUMN jkr.v_tyhjennysvalit.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.sopimus_id IS E'Viittaus sopimukseen, jota tyhjennysväli koskee.';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.sopimus_voimassaolo IS E'Sopimuksen voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.alkuvko IS E'Viikkonumero, josta alkaen astiat tyhjennetään X viikon välein.';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.loppuvko IS E'Viikkonumero, johon päättyy astioiden tyhjentäminen X viikon välein.';
COMMENT ON COLUMN jkr.v_tyhjennysvalit.tyhjennysvali IS E'Tyhjennysväli viikoissa.';


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
COMMENT ON COLUMN jkr.v_keskeytys.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_keskeytys.sopimus_id IS E'Viittaus sopimukseen, jota keskeytys koskee.';
COMMENT ON COLUMN jkr.v_keskeytys.sopimus_voimassaolo IS E'Sopimuksen voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_keskeytys.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_keskeytys.keskeytys_voimassa IS E'Keskeytyksen voimassaoloaikaväli (jkr.keskeytys.voimassaolo).';

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
COMMENT ON COLUMN jkr.v_keraysvalineet.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_keraysvalineet.sopimus_id IS E'Viittaus sopimukseen, johon keräysväline liittyy.';
COMMENT ON COLUMN jkr.v_keraysvalineet.sopimus_voimassaolo IS E'Sopimuksen voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_keraysvalineet.pvm IS E'Päivämäärä, jolloin kuljettajat ovat keränneet raportoitavat tiedot.';
COMMENT ON COLUMN jkr.v_keraysvalineet.jatetyyppi_selite IS E'Jätetyypin selite (jkr_koodistot.jatetyyppi.selite).';
COMMENT ON COLUMN jkr.v_keraysvalineet.keraysvalinetyyppi_selite IS E'Keräysvälinetyypin selite (jkr_koodistot.keraysvalinetyyppi.selite).';
