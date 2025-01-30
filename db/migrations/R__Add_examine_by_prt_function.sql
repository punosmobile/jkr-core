-- Function to examine all data related to a building by its PRT (pysyvä rakennustunnus)
CREATE OR REPLACE FUNCTION jkr.examine_by_prt(prt_param text)
RETURNS TABLE (
    table_name text,
    data jsonb
) AS $$
BEGIN
    -- Return building basic information
    RETURN QUERY
    SELECT 
        'rakennus'::text as table_name,
        to_jsonb(r.*) as data
    FROM jkr.rakennus r
    WHERE r.prt = prt_param;

    -- Return building usage type information
    RETURN QUERY
    SELECT 
        'rakennuksenkayttotarkoitus'::text,
        to_jsonb(rk.*)
    FROM jkr.rakennus r
    JOIN jkr_koodistot.rakennuksenkayttotarkoitus rk ON r.rakennuksenkayttotarkoitus_koodi = rk.koodi
    WHERE r.prt = prt_param;

    -- Return building state information
    RETURN QUERY
    SELECT 
        'rakennuksenolotila'::text,
        to_jsonb(ro.*)
    FROM jkr.rakennus r
    JOIN jkr_koodistot.rakennuksenolotila ro ON r.rakennuksenolotila_koodi = ro.koodi
    WHERE r.prt = prt_param;

    -- Return kohde (target) information where this building belongs to
    RETURN QUERY
    SELECT 
        'kohde'::text,
        to_jsonb(k.*)
    FROM jkr.rakennus r
    JOIN jkr.kohteen_rakennukset kr ON r.id = kr.rakennus_id
    JOIN jkr.kohde k ON kr.kohde_id = k.id
    WHERE r.prt = prt_param;

    -- Return velvoite (obligation) information for the kohde
    RETURN QUERY
    SELECT 
        'velvoite'::text,
        to_jsonb(v.*) as data
    FROM jkr.rakennus r
    JOIN jkr.kohteen_rakennukset kr ON r.id = kr.rakennus_id
    JOIN jkr.kohde k ON kr.kohde_id = k.id
    JOIN jkr.velvoite v ON k.id = v.kohde_id
    WHERE r.prt = prt_param;

    -- Return velvoiteyhteenveto information with model and status
    RETURN QUERY
    SELECT 
        'velvoiteyhteenveto'::text,
        jsonb_build_object(
            'yhteenveto', to_jsonb(vy.*),
            'yhteenvetomalli', to_jsonb(vym.*),
            'yhteenveto_status', to_jsonb(vys.*)
        ) as data
    FROM jkr.rakennus r
    JOIN jkr.kohteen_rakennukset kr ON r.id = kr.rakennus_id
    JOIN jkr.kohde k ON kr.kohde_id = k.id
    LEFT JOIN jkr.velvoiteyhteenveto vy ON k.id = vy.kohde_id
    LEFT JOIN jkr.velvoiteyhteenvetomalli vym ON vy.velvoiteyhteenvetomalli_id = vym.id
    LEFT JOIN jkr.velvoiteyhteenveto_status vys ON vy.id = vys.velvoiteyhteenveto_id
    WHERE r.prt = prt_param;

    -- Return building owner information with owner details
    RETURN QUERY
    SELECT 
        'rakennuksen_omistajat'::text,
        jsonb_build_object(
            'omistussuhde', to_jsonb(ro.*),
            'osapuoli', to_jsonb(op.*)
        ) as data
    FROM jkr.rakennus r
    JOIN jkr.rakennuksen_omistajat ro ON r.id = ro.rakennus_id
    JOIN jkr.osapuoli op ON ro.osapuoli_id = op.id
    WHERE r.prt = prt_param;

    -- Return address information with street details
    RETURN QUERY
    SELECT 
        'osoite'::text,
        jsonb_build_object(
            'osoite', to_jsonb(o.*),
            'katu', to_jsonb(k.*),
            'postinumero', to_jsonb(p.*)
        ) as data
    FROM jkr.rakennus r
    JOIN jkr.osoite o ON r.id = o.rakennus_id
    LEFT JOIN jkr_osoite.katu k ON o.katu_id = k.id
    LEFT JOIN jkr_osoite.posti p ON o.posti_numero = p.numero
    WHERE r.prt = prt_param;

    -- Return building candidate information if any
    RETURN QUERY
    SELECT 
        'kohteen_rakennusehdokkaat'::text,
        to_jsonb(kre.*)
    FROM jkr.rakennus r
    JOIN jkr.kohteen_rakennusehdokkaat kre ON r.id = kre.rakennus_id
    WHERE r.prt = prt_param;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission to jkr_admin
GRANT EXECUTE ON FUNCTION jkr.examine_by_prt(text) TO jkr_admin;

COMMENT ON FUNCTION jkr.examine_by_prt(text) IS 'Function that retrieves all related information for a building based on its PRT (pysyvä rakennustunnus). Returns data from multiple related tables including basic building info, usage type, state, kohde membership, obligations, obligation summaries with models and status, owners with their details, addresses with street info, and building candidates.';
