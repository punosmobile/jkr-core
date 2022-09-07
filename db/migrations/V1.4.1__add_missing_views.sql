
CREATE VIEW jkr.v_rakennusten_osoitteet
AS
SELECT
  o.id,
  o.rakennus_id,
  ka.katunimi_fi katunimi,
  o.osoitenumero,
  ku.nimi_fi kunta,
  po.numero postinumero,
  po.nimi_fi postitoimipaikka
FROM
  jkr.osoite o
  JOIN jkr_osoite.katu ka ON o.katu_id = ka.id
  JOIN jkr_osoite.kunta ku ON ka.kunta_koodi = ku.koodi
  JOIN jkr_osoite.posti po ON o.posti_numero = po.numero;
-- ddl-end --
ALTER VIEW jkr.v_rakennusten_osoitteet OWNER TO jkr_admin;
-- ddl-end --

-- object: jkr.v_rakennukset_ilman_kohdetta | type: VIEW --
-- DROP VIEW IF EXISTS jkr.v_rakennukset_ilman_kohdetta CASCADE;
CREATE VIEW jkr.v_rakennukset_ilman_kohdetta
AS

SELECT
  *
FROM
  jkr.rakennus r
WHERE
  NOT EXISTS (
    SELECT
      1
    FROM
      jkr.kohteen_rakennukset kr
    WHERE
      r.id = kr.rakennus_id);
-- ddl-end --
ALTER VIEW jkr.v_rakennukset_ilman_kohdetta OWNER TO jkr_admin;
-- ddl-end --

-- object: jkr.v_kohteet_ilman_rakennuksia | type: VIEW --
-- DROP VIEW IF EXISTS jkr.v_kohteet_ilman_rakennuksia CASCADE;
CREATE VIEW jkr.v_kohteet_ilman_rakennuksia
AS

SELECT
  *
FROM
  jkr.kohde k
WHERE
  NOT EXISTS (
    SELECT
      1
    FROM
      jkr.kohteen_rakennukset kr
    WHERE
      k.id = kr.kohde_id);
-- ddl-end --
ALTER VIEW jkr.v_kohteet_ilman_rakennuksia OWNER TO jkr_admin;
-- ddl-end --



-- object: jkr.v_kohde_yhteystiedot | type: VIEW --
-- DROP VIEW IF EXISTS jkr.v_kohde_yhteystiedot CASCADE;
CREATE VIEW jkr.v_kohde_yhteystiedot
AS

select
  k.id kohde_id,
  k.alkupvm,
  k.loppupvm,
  op.id osapuoli_id,
  (select selite from jkr_koodistot.osapuolenrooli opr where kop.osapuolenrooli_id = opr.id) osapuolenrooli,
  op.nimi,
  op.ytunnus,
  op.katuosoite,
  op.postinumero,
  op.postitoimipaikka,
  op.erikoisosoite
from
  jkr.kohde k
  left join jkr.kohteen_osapuolet kop
    on k.id = kop.kohde_id
  left join jkr.osapuoli op
    on kop.osapuoli_id = op.id;
-- ddl-end --
COMMENT ON VIEW jkr.v_kohde_yhteystiedot IS E'Näkymä kuhunkin kohteeseen liittyvistä yhteystiedoista';
-- ddl-end --
ALTER VIEW jkr.v_kohde_yhteystiedot OWNER TO jkr_admin;
-- ddl-end --

