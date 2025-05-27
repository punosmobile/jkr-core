CREATE VIEW jkr.v_rakennukset
AS

SELECT r.id,
    r.prt,
    r.huoneistomaara,
    r.kiinteistotunnus,
    r.onko_viemari,
    r.geom,
    r.rakennuksenkayttotarkoitus_koodi,
    r.rakennuksenolotila_koodi,
    r.kayttoonotto_pvm,
    r.kaytostapoisto_pvm,
    rl.selite as rakennusluokka_selite,
    r.rakennusluokka_2018,
    (EXISTS ( SELECT 1
           FROM jkr.kohteen_rakennusehdokkaat kr
          WHERE r.id = kr.rakennus_id)) AS on_kohde_ehdokkaita,
    r.kunta
FROM jkr.rakennus r
LEFT JOIN jkr_koodistot.rakennusluokka_2018 rl ON r.rakennusluokka_2018 = rl.koodi;

ALTER VIEW jkr.v_rakennukset OWNER TO jkr_admin;

COMMENT ON VIEW jkr.v_rakennukset IS E'Rakennusnäkymä, joka sisältää kaikki jkr.rakennus-taulun kentät sekä generoidun kentän onko rakennukselle tyrkyllä kohteita.';
