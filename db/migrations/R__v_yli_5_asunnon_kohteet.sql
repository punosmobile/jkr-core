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

COMMENT ON VIEW jkr.v_yli_5_asunnon_kohteet IS E'Kohteet, joiden rakennusten yhteenlaskettu huoneistomäärä on vähintään 5. Sisältää lasketun huoneistomäärän ja käytetään suurten kohteiden tunnistamiseen.';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.id IS E'Kohteen yksilöivä tunniste (jkr.kohde.id).';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.nimi IS E'Kohteen nimi.';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.geom IS E'Kohteen pseudogeometria (konveksi peite kohteeseen kuuluvista rakennuksista).';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.alkupvm IS E'Kohteen jätehuoltovelvollisuuden alkupäivämäärä.';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.loppupvm IS E'Kohteen jätehuoltovelvollisuuden loppupäivämäärä.';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.voimassaolo IS E'Kohteen jätehuoltovelvollisuuden voimassaoloaikaväli.';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.kohdetyyppi_id IS E'Viittaus kohteen tyyppiin (jkr_koodistot.kohdetyyppi).';
COMMENT ON COLUMN jkr.v_yli_5_asunnon_kohteet.huoneistomaara IS E'Kohteen rakennusten yhteenlaskettu huoneistomäärä (vähintään 5).';
