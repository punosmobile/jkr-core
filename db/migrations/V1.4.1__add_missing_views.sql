
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

