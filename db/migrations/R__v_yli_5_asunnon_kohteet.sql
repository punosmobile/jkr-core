CREATE VIEW jkr.v_yli_5_asunnon_kohteet
AS
SELECT k.id,
    k.nimi,
    k.geom,
    k.alkupvm,
    k.loppupvm,
    k.voimassaolo,
    k.kohdetyyppi_id,
    yli5.huoneistomaara
   FROM (jkr.kohde k
     JOIN ( SELECT k_1.id,
            sum(COALESCE((r.huoneistomaara)::integer, 1)) AS huoneistomaara
           FROM ((jkr.kohde k_1
             JOIN jkr.kohteen_rakennukset kr ON ((k_1.id = kr.kohde_id)))
             JOIN jkr.rakennus r ON ((kr.rakennus_id = r.id)))
          GROUP BY k_1.id
         HAVING (sum(COALESCE((r.huoneistomaara)::integer, 1)) >= 5)) yli5 ON ((k.id = yli5.id)));

ALTER VIEW jkr.v_yli_5_asunnon_kohteet OWNER TO jkr_admin;
