DROP MATERIALIZED VIEW IF EXISTS jkr.v_kuljetustietojen_kohteet_kolmeviimeista;
CREATE MATERIALIZED VIEW jkr.v_kuljetustietojen_kohteet_kolmeviimeista AS
  SELECT
    k.id AS kohde_id,
    k.kohdetyyppi_id,
    k.geom,
    ku.jatetyyppi_id,
    yht.kiinteistotunnus,
    yht.prt,
    yht.yhteyshenkilo,
    yht.katuosoite,
    yht.postitoimipaikka,
    yht.postinumero,
    yht.erikoisosoite
  FROM
    jkr.kohde k
    JOIN jkr.kuljetus ku
      ON k.id = ku.kohde_id
    LEFT JOIN jkr.v_kohteen_yhteystiedot yht
      ON k.id = yht.kohde_id
  WHERE
    k.voimassaolo @> CURRENT_DATE
    AND ku.aikavali && daterange(
      DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '9 months')::date,
      DATE_TRUNC('quarter', CURRENT_DATE)::date,
      '[)'
    );


DROP MATERIALIZED VIEW IF EXISTS jkr.v_kompostorien_kohteet_kolmeviimeista;
CREATE MATERIALIZED VIEW jkr.v_kompostorien_kohteet_kolmeviimeista AS
  SELECT
    k.id AS kohde_id,
    k.kohdetyyppi_id,
    k.geom,
    ko.id as kompostori_id,
    yht.kiinteistotunnus,
    yht.prt,
    yht.yhteyshenkilo,
    yht.katuosoite,
    yht.postitoimipaikka,
    yht.postinumero,
    yht.erikoisosoite
  FROM
    jkr.kohde k
    JOIN jkr.kompostorin_kohteet kk ON k.id = kk.kohde_id
    JOIN jkr.kompostori ko ON kk.kompostori_id = ko.id
    LEFT JOIN jkr.v_kohteen_yhteystiedot yht
      ON k.id = yht.kohde_id
  WHERE
    k.voimassaolo @> CURRENT_DATE
    AND ko.voimassaolo && daterange(
      DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '9 months')::date,
      DATE_TRUNC('quarter', CURRENT_DATE)::date,
      '[)'
    );

REFRESH MATERIALIZED VIEW jkr.v_kuljetustietojen_kohteet_kolmeviimeista;
REFRESH MATERIALIZED VIEW jkr.v_kompostorien_kohteet_kolmeviimeista;