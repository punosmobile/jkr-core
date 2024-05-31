CREATE OR REPLACE FUNCTION jkr.kohteiden_paatokset(kohde_ids integer[], tarkistusjakso daterange)
RETURNS TABLE(
    Kohde_id integer,
    Kompostoi date,
    "Perusmaksupäätös voimassa" date,
    "Perusmaksupäätös" text,
    "Tyhjennysvälipäätös voimassa" date,
    "Tyhjennysvälipäätös" text,
    "Akp-kohtuullistaminen voimassa" date,
    "Akp-kohtuullistaminen" text,
    "Keskeytys voimassa" date,
    "Keskeytys" text,
    "Erilliskeräysvelvoitteesta poikkeaminen voimassa" date,
    "Erilliskeräysvelvoitteesta poikkeaminen" text
) AS $$
BEGIN
    RETURN QUERY
    WITH rakennukset AS (
        SELECT
            kr.kohde_id,
            kr.rakennus_id
        FROM
            unnest(kohde_ids) AS k_id(kohde_id)
        JOIN
            jkr.kohteen_rakennukset AS kr ON kr.kohde_id = k_id.kohde_id
    ),
    paatokset AS (
        SELECT
            r.kohde_id,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS perusmaksupaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS perusmaksupaatos,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS tyhjennysvalipaatos_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS tyhjennysvalipaatos,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END)
                ELSE NULL
            END AS akp_kohtuullistaminen_voimassa,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END)
                ELSE NULL
            END AS akp_kohtuullistaminen,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END)
                ELSE NULL
            END AS keskeytys_voimassa,
            CASE WHEN 
                COUNT(*) = SUM(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN 1 ELSE 0 END) THEN
                    MAX(CASE WHEN vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END)
                ELSE NULL
            END AS keskeytys,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.loppupvm END) AS erilliskerayksesta_poikkeaminen_voimassa,
            MAX(CASE WHEN vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1' THEN vp.paatosnumero END) AS erilliskerayksesta_poikkeaminen
        FROM
            rakennukset r
        LEFT JOIN
            jkr.viranomaispaatokset AS vp ON vp.rakennus_id = r.rakennus_id
        WHERE
            (vp.tapahtumalaji_koodi = 'PERUSMAKSU' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'TYHJENNYSVALI' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'AKP' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'KESKEYTTAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
            OR (vp.tapahtumalaji_koodi = 'ERILLISKERAYKSESTA_POIKKEAMINEN' AND vp.voimassaolo && tarkistusjakso AND vp.paatostulos_koodi = '1')
        GROUP BY
            r.kohde_id
    ),
    composting_status AS (
        SELECT DISTINCT ON (k_id.kohde_id)
            k_id.kohde_id,
            kom.loppupvm AS kompostoi
        FROM
            unnest(kohde_ids) AS k_id(kohde_id)
        LEFT JOIN
            jkr.kompostorin_kohteet AS k ON k.kohde_id = k_id.kohde_id
        LEFT JOIN
            jkr.kompostori AS kom ON kom.id = k.kompostori_id
        WHERE
            kom.voimassaolo && tarkistusjakso
        ORDER BY
            k_id.kohde_id, kom.loppupvm DESC
    )
    SELECT
        k_id.kohde_id,
        cs.kompostoi,
        p.perusmaksupaatos_voimassa AS "Perusmaksupäätös voimassa",
        p.perusmaksupaatos AS "Perusmaksupäätös",
        p.tyhjennysvalipaatos_voimassa AS "Tyhjennysvälipäätös voimassa",
        p.tyhjennysvalipaatos AS "Tyhjennysvälipäätös",
        p.akp_kohtuullistaminen_voimassa AS "Akp-kohtuullistaminen voimassa",
        p.akp_kohtuullistaminen AS "Akp-kohtuullistaminen",
        p.keskeytys_voimassa AS "Keskeytys voimassa",
        p.keskeytys AS "Keskeytys",
        p.erilliskerayksesta_poikkeaminen_voimassa AS "Erilliskeräysvelvoitteesta poikkeaminen voimassa",
        p.erilliskerayksesta_poikkeaminen AS "Erilliskeräysvelvoitteesta poikkeaminen"
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        composting_status cs ON cs.kohde_id = k_id.kohde_id
    LEFT JOIN
        paatokset p ON p.kohde_id = k_id.kohde_id
    ORDER BY
        k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_kuljetukset(kohde_ids integer[], tarkistusjakso daterange)
RETURNS TABLE(
    Kohde_id integer,
    Muovi date,
    Kartonki date,
    Metalli date,
    Lasi date,
    Biojäte date,
    Monilokero date,
    Sekajate date,
    Akp date
) AS $$
BEGIN
    RETURN QUERY
    WITH valid_kuljetukset AS (
        SELECT
            k.kohde_id,
            CASE WHEN jt.selite = 'Muovi' THEN k.loppupvm END AS muovi,
            CASE WHEN jt.selite = 'Kartonki' THEN k.loppupvm END AS kartonki,
            CASE WHEN jt.selite = 'Metalli' THEN k.loppupvm END AS metalli,
            CASE WHEN jt.selite = 'Lasi' THEN k.loppupvm END AS lasi,
            CASE WHEN jt.selite = 'Biojäte' THEN k.loppupvm END AS biojate,
            CASE WHEN jt.selite = 'Monilokero' THEN k.loppupvm END AS monilokero,
            CASE WHEN jt.selite = 'Sekajäte' THEN k.loppupvm END AS sekajate,
            CASE WHEN jt.selite = 'Muu' THEN k.loppupvm END AS akp
        FROM
            jkr.kuljetus k
        JOIN
            jkr_koodistot.jatetyyppi jt ON k.jatetyyppi_id = jt.id
        WHERE
            k.kohde_id = ANY(kohde_ids)
            AND k.aikavali && tarkistusjakso
    ),
    aggregated_kuljetukset AS (
        SELECT
            vk.kohde_id,
            MAX(vk.muovi) AS muovi,
            MAX(vk.kartonki) AS kartonki,
            MAX(vk.metalli) AS metalli,
            MAX(vk.lasi) AS lasi,
            MAX(vk.biojate) AS biojate,
            MAX(vk.monilokero) AS monilokero,
            MAX(vk.sekajate) AS sekajate,
            MAX(vk.akp) AS akp
        FROM
            valid_kuljetukset vk
        GROUP BY
            vk.kohde_id
    )
    SELECT
        k_id.kohde_id,
        ak.muovi,
        ak.kartonki,
        ak.metalli,
        ak.lasi,
        ak.biojate,
        ak.monilokero,
        ak.sekajate,
        ak.akp
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        aggregated_kuljetukset ak ON ak.kohde_id = k_id.kohde_id
    ORDER BY
        k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_velvoitteet(kohde_ids integer[], tarkistusjakso daterange)
RETURNS TABLE(
    Kohde_id integer,
    "Velvoitteen tallennuspvm" date,
    Velvoiteyhteenveto text,
    Sekajätevelvoite text,
    Biojätevelvoite text,
    Muovipakkausvelvoite text,
    Kartonkipakkausvelvoite text,
    Lasipakkausvelvoite text,
    Metallipakkausvelvoite text
) AS $$
DECLARE
    selected_tallennuspvm date;
BEGIN
    SELECT 
        vs.tallennuspvm
    INTO 
        selected_tallennuspvm
    FROM 
        jkr.velvoite_status vs
    WHERE 
        vs.jakso && tarkistusjakso
    ORDER BY 
        vs.tallennuspvm DESC
    LIMIT 1;

    RETURN QUERY
    WITH velvoiteyhteenveto_data AS (
        SELECT
            v.kohde_id,
            vs.jakso,
            vvm.kuvaus
        FROM
            jkr.velvoiteyhteenveto v
        JOIN
            jkr.velvoiteyhteenveto_status vs ON v.id = vs.velvoiteyhteenveto_id
        JOIN
            jkr.velvoiteyhteenvetomalli vvm ON v.velvoiteyhteenvetomalli_id = vvm.id
        WHERE
            v.kohde_id = ANY(kohde_ids)
            AND vs.ok = TRUE
            AND vs.tallennuspvm = selected_tallennuspvm
        ORDER BY
            vs.jakso DESC
    ),
    velvoite_data AS (
        SELECT
            v.kohde_id,
            vs.jakso,
            vm.kuvaus,
            vm.selite
        FROM
            jkr.velvoite v
        JOIN
            jkr.velvoite_status vs ON v.id = vs.velvoite_id
        JOIN
            jkr.velvoitemalli vm ON v.velvoitemalli_id = vm.id
        WHERE
            v.kohde_id = ANY(kohde_ids)
            AND vs.ok = TRUE
            AND vs.tallennuspvm = selected_tallennuspvm
        ORDER BY
            vs.jakso DESC
    ),
    aggregated_velvoite AS (
        SELECT
            vd.kohde_id,
            MAX(CASE WHEN vd.selite = 'Sekajäte' THEN vd.kuvaus END) AS sekajatevelvoite,
            MAX(CASE WHEN vd.selite = 'Biojäte' THEN vd.kuvaus END) AS biojatevelvoite,
            MAX(CASE WHEN vd.selite = 'Muovi' THEN vd.kuvaus END) AS muovipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Kartonki' THEN vd.kuvaus END) AS kartonkipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Lasipakkaus' THEN vd.kuvaus END) AS lasipakkausvelvoite,
            MAX(CASE WHEN vd.selite = 'Metalli' THEN vd.kuvaus END) AS metallipakkausvelvoite
        FROM
            velvoite_data vd
        GROUP BY
            vd.kohde_id
    )
    SELECT
        k_id.kohde_id,
        selected_tallennuspvm AS "Velvoitteen tallennuspvm",
        vy.kuvaus AS velvoiteyhteenveto,
        av.sekajatevelvoite,
        av.biojatevelvoite,
        av.muovipakkausvelvoite,
        av.kartonkipakkausvelvoite,
        av.lasipakkausvelvoite,
        av.metallipakkausvelvoite
    FROM
        unnest(kohde_ids) AS k_id(kohde_id)
    LEFT JOIN
        (SELECT DISTINCT ON (kohde_id) * FROM velvoiteyhteenveto_data) vy ON vy.kohde_id = k_id.kohde_id
    LEFT JOIN
        aggregated_velvoite av ON av.kohde_id = k_id.kohde_id;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.kohteiden_rakennustiedot(kohde_ids integer[])
RETURNS TABLE(
    Kohde_id integer,
    "PRT 1" text,
    "Käyttötila 1" text,
    "Käyttötarkoitus 1" text,
    Katuosoite text,
    Postinumero text,
    Postitoimipaikka text,
    Sijaintikiinteistö text,
    "X-koordinaatti" float,
    "Y-koordinaatti" float,
    "PRT 2" text,
    "Käyttötila 2" text,
    "Käyttötarkoitus 2" text,
    "PRT 3" text,
    "Käyttötila 3" text,
    "Käyttötarkoitus 3" text,
    "PRT 4" text,
    "Käyttötila 4" text,
    "Käyttötarkoitus 4" text,
    "PRT 5" text,
    "Käyttötila 5" text,
    "Käyttötarkoitus 5" text,
    "PRT 6" text,
    "Käyttötila 6" text,
    "Käyttötarkoitus 6" text,
    "PRT 7" text,
    "Käyttötila 7" text,
    "Käyttötarkoitus 7" text,
    "PRT 8" text,
    "Käyttötila 8" text,
    "Käyttötarkoitus 8" text,
    "PRT 9" text,
    "Käyttötila 9" text,
    "Käyttötarkoitus 9" text,
    "PRT 10" text,
    "Käyttötila 10" text,
    "Käyttötarkoitus 10" text,
    "PRT 11" text,
    "Käyttötila 11" text,
    "Käyttötarkoitus 11" text,
    "PRT 12" text,
    "Käyttötila 12" text,
    "Käyttötarkoitus 12" text,
    "PRT 13" text,
    "Käyttötila 13" text,
    "Käyttötarkoitus 13" text,
    "PRT 14" text,
    "Käyttötila 14" text,
    "Käyttötarkoitus 14" text,
    "PRT 15" text,
    "Käyttötila 15" text,
    "Käyttötarkoitus 15" text,
    "PRT 16" text,
    "Käyttötila 16" text,
    "Käyttötarkoitus 16" text,
    "PRT 17" text,
    "Käyttötila 17" text,
    "Käyttötarkoitus 17" text
) AS $$
BEGIN
    RETURN QUERY
    WITH significant_rakennukset AS (
        SELECT
            kr.kohde_id,
            r.id AS rakennus_id,
            r.prt::text AS prt,
            ro.selite::text AS kayttotila,
            rt.selite::text AS kayttotarkoitus,
            r.kiinteistotunnus::text AS sijaintikiinteisto,
            ST_X(ST_Transform(r.geom, 3067)) AS x_koordinaatti,
            ST_Y(ST_Transform(r.geom, 3067)) AS y_koordinaatti
        FROM
            jkr.kohteen_rakennukset kr
        JOIN
            jkr.rakennus r ON kr.rakennus_id = r.id
        LEFT JOIN
            jkr_koodistot.rakennuksenkayttotarkoitus rt ON r.rakennuksenkayttotarkoitus_koodi = rt.koodi
        LEFT JOIN
            jkr_koodistot.rakennuksenolotila ro ON r.rakennuksenolotila_koodi = ro.koodi
        WHERE
            kr.kohde_id = ANY(kohde_ids)
            AND (
                rt.selite = ANY(ARRAY[
                    'Yhden asunnon talot', 'Kahden asunnon talot', 'Muut erilliset pientalot', 'Rivitalot',
                    'Luhtitalot', 'Ketjutalot', 'Muut asuinkerrostalot', 'Vapaa-ajan asuinrakennukset',
                    'Muut asuntolarakennukset', 'Vanhainkodit', 'Lasten- ja koulukodit',
                    'Kehitysvammaisten hoitolaitokset', 'Muut huoltolaitosrakennukset', 'Lasten päiväkodit',
                    'Muualla luokittelemattomat sosiaalitoimen rakennukset', 'Yleissivistävien oppilaitosten rakennukset',
                    'Ammatillisten oppilaitosten rakennukset', 'Korkeakoulurakennukset', 'Tutkimuslaitosrakennukset',
                    'Järjestöjen, liittojen, työnantajien yms. opetusrakennukset', 'Muualla luokittelemattomat opetusrakennukset'
                ])
            )
    ),
    first_significant_address AS (
        SELECT DISTINCT ON (sr.kohde_id)
            sr.kohde_id,
            (k.katunimi_fi || ' ' || ao.osoitenumero)::text AS katuosoite,
            ao.posti_numero::text AS postinumero,
            kun.nimi_fi::text AS postitoimipaikka
        FROM
            significant_rakennukset sr
        JOIN
            jkr.osoite ao ON sr.rakennus_id = ao.rakennus_id
        LEFT JOIN
            jkr_osoite.katu k ON ao.katu_id = k.id
        LEFT JOIN
            jkr_osoite.kunta kun ON k.kunta_koodi = kun.koodi
    ),
    ranked_rakennukset AS (
        SELECT DISTINCT ON (sr.kohde_id, sr.rakennus_id)
            sr.*,
            ROW_NUMBER() OVER (PARTITION BY sr.kohde_id ORDER BY sr.rakennus_id) AS rn
        FROM significant_rakennukset sr
    )
    SELECT
        sr.kohde_id,
        MAX(CASE WHEN rn = 1 THEN sr.prt END) AS "PRT 1",
        MAX(CASE WHEN rn = 1 THEN sr.kayttotila END) AS "Käyttötila 1",
        MAX(CASE WHEN rn = 1 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 1",
        fa.katuosoite,
        fa.postinumero,
        fa.postitoimipaikka,
        MAX(CASE WHEN rn = 1 THEN sr.sijaintikiinteisto END) AS sijaintikiinteisto,
        MAX(CASE WHEN rn = 1 THEN sr.x_koordinaatti END) AS "X-koordinaatti",
        MAX(CASE WHEN rn = 1 THEN sr.y_koordinaatti END) AS "Y-koordinaatti",
        MAX(CASE WHEN rn = 2 THEN sr.prt END) AS "PRT 2",
        MAX(CASE WHEN rn = 2 THEN sr.kayttotila END) AS "Käyttötila 2",
        MAX(CASE WHEN rn = 2 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 2",
        MAX(CASE WHEN rn = 3 THEN sr.prt END) AS "PRT 3",
        MAX(CASE WHEN rn = 3 THEN sr.kayttotila END) AS "Käyttötila 3",
        MAX(CASE WHEN rn = 3 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 3",
        MAX(CASE WHEN rn = 4 THEN sr.prt END) AS "PRT 4",
        MAX(CASE WHEN rn = 4 THEN sr.kayttotila END) AS "Käyttötila 4",
        MAX(CASE WHEN rn = 4 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 4",
        MAX(CASE WHEN rn = 5 THEN sr.prt END) AS "PRT 5",
        MAX(CASE WHEN rn = 5 THEN sr.kayttotila END) AS "Käyttötila 5",
        MAX(CASE WHEN rn = 5 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 5",
        MAX(CASE WHEN rn = 6 THEN sr.prt END) AS "PRT 6",
        MAX(CASE WHEN rn = 6 THEN sr.kayttotila END) AS "Käyttötila 6",
        MAX(CASE WHEN rn = 6 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 6",
        MAX(CASE WHEN rn = 7 THEN sr.prt END) AS "PRT 7",
        MAX(CASE WHEN rn = 7 THEN sr.kayttotila END) AS "Käyttötila 7",
        MAX(CASE WHEN rn = 7 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 7",
        MAX(CASE WHEN rn = 8 THEN sr.prt END) AS "PRT 8",
        MAX(CASE WHEN rn = 8 THEN sr.kayttotila END) AS "Käyttötila 8",
        MAX(CASE WHEN rn = 8 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 8",
        MAX(CASE WHEN rn = 9 THEN sr.prt END) AS "PRT 9",
        MAX(CASE WHEN rn = 9 THEN sr.kayttotila END) AS "Käyttötila 9",
        MAX(CASE WHEN rn = 9 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 9",
        MAX(CASE WHEN rn = 10 THEN sr.prt END) AS "PRT 10",
        MAX(CASE WHEN rn = 10 THEN sr.kayttotila END) AS "Käyttötila 10",
        MAX(CASE WHEN rn = 10 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 10",
        MAX(CASE WHEN rn = 11 THEN sr.prt END) AS "PRT 11",
        MAX(CASE WHEN rn = 11 THEN sr.kayttotila END) AS "Käyttötila 11",
        MAX(CASE WHEN rn = 11 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 11",
        MAX(CASE WHEN rn = 12 THEN sr.prt END) AS "PRT 12",
        MAX(CASE WHEN rn = 12 THEN sr.kayttotila END) AS "Käyttötila 12",
        MAX(CASE WHEN rn = 12 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 12",
        MAX(CASE WHEN rn = 13 THEN sr.prt END) AS "PRT 13",
        MAX(CASE WHEN rn = 13 THEN sr.kayttotila END) AS "Käyttötila 13",
        MAX(CASE WHEN rn = 13 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 13",
        MAX(CASE WHEN rn = 14 THEN sr.prt END) AS "PRT 14",
        MAX(CASE WHEN rn = 14 THEN sr.kayttotila END) AS "Käyttötila 14",
        MAX(CASE WHEN rn = 14 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 14",
        MAX(CASE WHEN rn = 15 THEN sr.prt END) AS "PRT 15",
        MAX(CASE WHEN rn = 15 THEN sr.kayttotila END) AS "Käyttötila 15",
        MAX(CASE WHEN rn = 15 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 15",
        MAX(CASE WHEN rn = 16 THEN sr.prt END) AS "PRT 16",
        MAX(CASE WHEN rn = 16 THEN sr.kayttotila END) AS "Käyttötila 16",
        MAX(CASE WHEN rn = 16 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 16",
        MAX(CASE WHEN rn = 17 THEN sr.prt END) AS "PRT 17",
        MAX(CASE WHEN rn = 17 THEN sr.kayttotila END) AS "Käyttötila 17",
        MAX(CASE WHEN rn = 17 THEN sr.kayttotarkoitus END) AS "Käyttötarkoitus 17"
    FROM ranked_rakennukset sr
    LEFT JOIN first_significant_address fa ON sr.kohde_id = fa.kohde_id
    GROUP BY sr.kohde_id, fa.katuosoite, fa.postinumero, fa.postitoimipaikka
    ORDER BY sr.kohde_id;
END;
$$ LANGUAGE plpgsql;
