CREATE OR REPLACE VIEW jkr.v_ulkoinen_asiakastieto_tiedontuottajalla AS
SELECT 
    u.id,
    u.tiedontuottaja_tunnus,
    t.nimi AS tiedontuottaja_nimi,
    u.ulkoinen_id,
    u.kohde_id,
    -- Urakoitsijan tiedot
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'UrakoitsijaId' AS urakoitsija_id,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'UrakoitsijankohdeId' AS urakoitsijan_kohde_id,
    -- Kiinteistön tiedot
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kiinteistotunnus' AS kiinteistotunnus,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kiinteistonkatuosoite' AS kiinteiston_katuosoite,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kiinteistonposti' AS kiinteiston_posti,
    -- Haltijan tiedot
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijannimi' AS haltijan_nimi,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijanyhteyshlo' AS haltijan_yhteyshlo,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijankatuosoite' AS haltijan_katuosoite,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijanposti' AS haltijan_posti,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijanmaakoodi' AS haltijan_maakoodi,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Haltijanulkomaanpaikkakunta' AS haltijan_ulkomaan_paikkakunta,
    -- Voimassaoloajat
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Pvmalk')::date AS pvm_alkaen,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Pvmasti')::date AS pvm_asti,
    -- Jätetyyppi ja astiatiedot
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'tyyppiIdEWC' AS jatetyyppi_ewc,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'astiamaara')::numeric AS astiamaara,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'koko')::numeric AS astian_koko,
    -- Kunta
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kuntatun')::integer AS kunta_tunnus,
    -- Kimppakohde
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'palveluKimppakohdeId' AS kimppakohde_id,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'kimpanNimi' AS kimpan_nimi,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kimpanyhteyshlo' AS kimpan_yhteyshlo,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kimpankatuosoite' AS kimpan_katuosoite,
    (u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Kimpanposti' AS kimpan_posti,
    -- Keskeytykset
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Keskeytysalkaen')::date AS keskeytys_alkaen,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->>'Keskeytysasti')::date AS keskeytys_asti,
    -- Array-kentät TEKSTINÄ
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->'kaynnit')::text AS kaynnit,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->'paino')::text AS paino,
    ((u.ulkoinen_asiakastieto#>>'{}')::jsonb->'tyhjennysvali')::text AS tyhjennysvali,
    -- Alkuperäinen JSON TEKSTINÄ
    (u.ulkoinen_asiakastieto#>>'{}')::text AS alkuperainen_json
FROM 
    jkr.ulkoinen_asiakastieto u
    INNER JOIN jkr_koodistot.tiedontuottaja t 
        ON u.tiedontuottaja_tunnus = t.tunnus;