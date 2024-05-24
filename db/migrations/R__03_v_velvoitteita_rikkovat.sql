DROP MATERIALIZED VIEW IF EXISTS jkr.v_velvoitteiden_kohteet;
-- REPLACE doesn't work with materialized view.
CREATE MATERIALIZED VIEW jkr.v_velvoitteiden_kohteet AS
  SELECT
    k.id AS kohde_id,
    k.geom,
    vm.id AS velvoitemalli_id,
    vm.selite,
    vs.jakso,
    vs.ok,
    yht.kiinteistotunnus,
    yht.prt,
    yht.yhteyshenkilo,
    yht.katuosoite,
    yht.postitoimipaikka,
    yht.postinumero,
    yht.erikoisosoite
  FROM
    jkr.kohde k
    JOIN jkr.velvoite v
      ON k.id = v.kohde_id
    JOIN (
      SELECT
        velvoite_status.id,
        velvoite_status.jakso,
        velvoite_status.ok,
        velvoite_status.velvoite_id,
        velvoite_status.tallennuspvm,
        row_number() OVER (
          PARTITION BY velvoite_status.velvoite_id
          ORDER BY upper(velvoite_status.jakso) DESC
        ) AS row_number
      FROM jkr.velvoite_status
    ) vs
      ON v.id = vs.velvoite_id AND vs.row_number = 1
    JOIN jkr.velvoitemalli vm
      ON vm.id = v.velvoitemalli_id
    LEFT JOIN jkr.v_kohteen_yhteystiedot yht
      ON k.id = yht.kohde_id
  WHERE
    k.voimassaolo @> CURRENT_DATE
    AND vs.ok;


DROP MATERIALIZED VIEW IF EXISTS jkr.v_velvoiteyhteenvetojen_kohteet;
CREATE MATERIALIZED VIEW jkr.v_velvoiteyhteenvetojen_kohteet AS
  SELECT
    k.id AS kohde_id,
    k.geom,
    vm.id AS velvoitemalli_id,
    vm.selite,
    vs.jakso,
    vs.ok,
    yht.kiinteistotunnus,
    yht.prt,
    yht.yhteyshenkilo,
    yht.katuosoite,
    yht.postitoimipaikka,
    yht.postinumero,
    yht.erikoisosoite
  FROM
    jkr.kohde k
    JOIN jkr.velvoiteyhteenveto v
      ON k.id = v.kohde_id
    JOIN (
      SELECT
        velvoiteyhteenveto_status.id,
        velvoiteyhteenveto_status.jakso,
        velvoiteyhteenveto_status.ok,
        velvoiteyhteenveto_status.velvoiteyhteenveto_id,
        velvoiteyhteenveto_status.tallennuspvm,
        row_number() OVER (
          PARTITION BY velvoiteyhteenveto_status.velvoiteyhteenveto_id
          ORDER BY upper(velvoiteyhteenveto_status.jakso) DESC
        ) AS row_number
      FROM jkr.velvoiteyhteenveto_status
    ) vs
      ON v.id = vs.velvoiteyhteenveto_id AND vs.row_number = 1
    JOIN jkr.velvoiteyhteenvetomalli vm
      ON vm.id = v.velvoiteyhteenvetomalli_id
    LEFT JOIN jkr.v_kohteen_yhteystiedot yht
      ON k.id = yht.kohde_id
  WHERE
    k.voimassaolo @> CURRENT_DATE
    AND vs.ok;
