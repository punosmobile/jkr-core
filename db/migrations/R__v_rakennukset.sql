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
COMMENT ON COLUMN jkr.v_rakennukset.id IS E'Rakennuksen yksilöivä tunniste (jkr.rakennus.id).';
COMMENT ON COLUMN jkr.v_rakennukset.prt IS E'Yksilöivä 10-merkkinen rakennustunnus.';
COMMENT ON COLUMN jkr.v_rakennukset.huoneistomaara IS E'Rakennukseen kuuluvien huoneistojen lukumäärä.';
COMMENT ON COLUMN jkr.v_rakennukset.kiinteistotunnus IS E'Tekstimuotoinen kiinteistötunnus.';
COMMENT ON COLUMN jkr.v_rakennukset.onko_viemari IS E'Totuusarvo, joka kertoo sen kuuluuko rakennus viemäriverkostoon vai ei.';
COMMENT ON COLUMN jkr.v_rakennukset.geom IS E'Rakennuksen geometria.';
COMMENT ON COLUMN jkr.v_rakennukset.rakennuksenkayttotarkoitus_koodi IS E'Viittaus rakennuksen käyttötarkoitukseen (jkr_koodistot.rakennuksenkayttotarkoitus).';
COMMENT ON COLUMN jkr.v_rakennukset.rakennuksenolotila_koodi IS E'Viittaus rakennuksen olotilaan (jkr_koodistot.rakennuksenolotila).';
COMMENT ON COLUMN jkr.v_rakennukset.kayttoonotto_pvm IS E'Rakennuksen käyttöönottopäivämäärä.';
COMMENT ON COLUMN jkr.v_rakennukset.kaytostapoisto_pvm IS E'Rakennuksen käytöstäpoistopäivämäärä.';
COMMENT ON COLUMN jkr.v_rakennukset.rakennusluokka_selite IS E'Rakennusluokan selite (jkr_koodistot.rakennusluokka_2018.selite).';
COMMENT ON COLUMN jkr.v_rakennukset.rakennusluokka_2018 IS E'Rakennusluokka 2018 -luokituksen mukainen rakennuksen käyttötarkoitus.';
COMMENT ON COLUMN jkr.v_rakennukset.on_kohde_ehdokkaita IS E'Totuusarvo siitä, onko rakennus ehdolla jonkin kohteen rakennukseksi (jkr.kohteen_rakennusehdokkaat).';
COMMENT ON COLUMN jkr.v_rakennukset.kunta IS E'Tieto rakennuksen sijaintikunnasta.';
