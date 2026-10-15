create or replace view jkr.v_kohteen_yhteystiedot as (
select
  k.id kohde_id,
  (
    select
      string_agg(jkr.pitka_kitu_2_lyhyt(kiinteistotunnus), ', ')
    from
      jkr.kohteen_rakennukset kr
      join jkr.rakennus r
        on kr.rakennus_id = r.id
    where kr.kohde_id = k.id
  ) kiinteistotunnus,
  (
    select
      string_agg(prt, ', ')
    from
      jkr.kohteen_rakennukset kr
      join jkr.rakennus r
        on kr.rakennus_id = r.id
    where kr.kohde_id = k.id
  ) prt,
  op.nimi yhteyshenkilo,
  op.katuosoite,
  op.postitoimipaikka,
  op.postinumero,
  op.erikoisosoite
FROM
  jkr.kohde k
  LEFT JOIN (
    SELECT *
    FROM jkr.kohteen_osapuolet
    WHERE osapuolenrooli_id = (
        SELECT osapuolenrooli.id
        FROM jkr_koodistot.osapuolenrooli
        WHERE osapuolenrooli.selite = 'Yhteystieto'::text
    )
  ) ko
    on k.id = ko.kohde_id
  LEFT JOIN jkr.osapuoli op
    ON op.id = ko.osapuoli_id
);

COMMENT ON VIEW jkr.v_kohteen_yhteystiedot IS E'Kohteen yhteystiedot koottuna: Yhteystieto-roolin osapuolen tiedot sekä kohteen rakennusten kiinteistötunnukset ja pysyvät rakennustunnukset (PRT) listana. Apunäkymä muille näkymille.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.kohde_id IS E'Viittaus kohteeseen.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.kiinteistotunnus IS E'Kohteen rakennusten kiinteistötunnukset lyhyessä muodossa, pilkulla eroteltuna.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.prt IS E'Kohteen rakennusten pysyvät rakennustunnukset (PRT), pilkulla eroteltuna.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.yhteyshenkilo IS E'Kohteen yhteystieto-roolisen osapuolen nimi.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.katuosoite IS E'Yhteyshenkilön katuosoite.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.postitoimipaikka IS E'Yhteyshenkilön postitoimipaikka.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.postinumero IS E'Yhteyshenkilön postinumero.';
COMMENT ON COLUMN jkr.v_kohteen_yhteystiedot.erikoisosoite IS E'Yhteyshenkilön ulkomaanosoite.';
