CREATE OR REPLACE VIEW jkr.v_velvoitteiden_kohteet AS
  SELECT
    k.id AS kohde_id,
    k.geom,
    vm.selite,
    vs.pvm,
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
        velvoite_status.pvm,
        velvoite_status.ok,
        velvoite_status.velvoite_id,
        velvoite_status.tallennuspvm,
        row_number() OVER (
          PARTITION BY velvoite_status.velvoite_id
          ORDER BY velvoite_status.pvm DESC
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
