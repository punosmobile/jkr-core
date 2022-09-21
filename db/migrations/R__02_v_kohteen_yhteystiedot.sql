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
