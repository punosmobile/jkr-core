CREATE VIEW jkr.v_kohdehaku
AS
SELECT DISTINCT k.id AS kohde_id,
    k.nimi AS kohteen_nimi,
    k.alkupvm AS kohteen_alkupvm,
    k.loppupvm AS kohteen_loppupvm,
    k.geom AS kohde_geom,
    ua.tiedontuottaja_tunnus AS ulkoinen_jarjestelma,
    ua.ulkoinen_id AS ulkoinen_asiakasnumero,
    ko.osapuolenrooli_id,
    op.nimi AS osapuoli_nimi,
    op.katuosoite AS osapuoli_osoite,
    op.postinumero AS osapuoli_postinumero,
    op.kunta AS osapuoli_kunta,
    r.prt AS rakennuksen_prt,
    r.kiinteistotunnus AS rakennuksen_kiinteistotunnus,
    ka.katunimi_fi AS rakennuksen_katunimi,
    o.osoitenumero AS rakennuksen_osoitenumero,
    ku.nimi_fi AS rakennuksen_kunta,
    po.numero AS rakennuksen_postinumero,
    po.nimi_fi AS rakennuksen_postitoimipaikka
    FROM jkr.kohde k
    LEFT JOIN jkr.ulkoinen_asiakastieto ua ON k.id = ua.kohde_id
    LEFT JOIN jkr.kohteen_osapuolet ko ON k.id = ko.kohde_id
    LEFT JOIN jkr.osapuoli op ON ko.osapuoli_id = op.id
    LEFT JOIN jkr.kohteen_rakennukset kr ON k.id = kr.kohde_id
    LEFT JOIN jkr.rakennus r ON kr.rakennus_id = r.id
    LEFT JOIN jkr.osoite o ON r.id = o.rakennus_id
    LEFT JOIN jkr_osoite.katu ka ON o.katu_id = ka.id
    LEFT JOIN jkr_osoite.kunta ku ON ka.kunta_koodi = ku.koodi
    LEFT JOIN jkr_osoite.posti po ON o.posti_numero = po.numero;

ALTER VIEW jkr.v_kohdehaku OWNER TO jkr_admin;
