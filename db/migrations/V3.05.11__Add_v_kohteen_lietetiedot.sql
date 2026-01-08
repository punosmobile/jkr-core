-- Näkymä kohteen lietetiedoille QGIS-välilehteä varten
-- LAH-437: QGIS-projektiin lietetiedot näkymään kohteelle
-- LAH-308: Käyttöliittymämuutokset - Kaivotiedot näkymiin QGIS välilehdelle

-- Näkymä kokoaa kohteen kaikki lietetiedot yhdelle riville
-- Määrittelyjen mukaiset kentät (JKR Lietemäärittelyt 19122025.xlsx):
-- - Viemäriverkostoliittymä: varhaisin alkupvm
-- - Kaivotiedot: voimassa olevat per tyyppi
-- - Lietteen kompostointi-ilmoitus: myöhäisimpään voimassa oleva

CREATE OR REPLACE VIEW jkr.v_kohteen_lietetiedot AS
WITH 
-- Viemäriverkostoliittymä: varhaisin alkupvm kohteelta
viemari AS (
    SELECT 
        kohde_id,
        MIN(viemariverkosto_alkupvm) AS viemariverkosto_alkupvm
    FROM jkr.viemari_liitos
    WHERE viemariverkosto_loppupvm IS NULL 
       OR viemariverkosto_loppupvm >= CURRENT_DATE
    GROUP BY kohde_id
),
-- Kaivotiedot: voimassa olevat per tyyppi (tyyppi_id: 1=Kantovesi, 2=Saostussäiliö, 3=Pienpuhdistamo, 4=Umpisäiliö, 5=Vain harmaat vedet)
kaivot AS (
    SELECT 
        kt.kohde_id,
        MAX(CASE WHEN kt.kaivotietotyyppi_id = 1 THEN kt.alkupvm END) AS kantovesi_alkupvm,
        MAX(CASE WHEN kt.kaivotietotyyppi_id = 2 THEN kt.alkupvm END) AS saostussailio_alkupvm,
        MAX(CASE WHEN kt.kaivotietotyyppi_id = 3 THEN kt.alkupvm END) AS pienpuhdistamo_alkupvm,
        MAX(CASE WHEN kt.kaivotietotyyppi_id = 4 THEN kt.alkupvm END) AS umpisailio_alkupvm,
        MAX(CASE WHEN kt.kaivotietotyyppi_id = 5 THEN kt.alkupvm END) AS harmaat_vedet_alkupvm
    FROM jkr.kaivotieto kt
    WHERE kt.loppupvm IS NULL 
       OR kt.loppupvm >= CURRENT_DATE
    GROUP BY kt.kohde_id
),
-- Lietteen kompostointi-ilmoitus: myöhäisimpään voimassa oleva (tai uusin päättynyt)
kompostointi AS (
    SELECT DISTINCT ON (kk.kohde_id)
        kk.kohde_id,
        k.alkupvm AS kompostointi_alkupvm,
        k.loppupvm AS kompostointi_loppupvm
    FROM jkr.kompostorin_kohteet kk
    JOIN jkr.kompostori k ON kk.kompostori_id = k.id
    ORDER BY kk.kohde_id, 
             CASE WHEN k.loppupvm IS NULL OR k.loppupvm >= CURRENT_DATE THEN 0 ELSE 1 END,
             COALESCE(k.loppupvm, '9999-12-31') DESC,
             k.alkupvm DESC
)
SELECT 
    ROW_NUMBER() OVER () AS id,
    ko.id AS kohde_id,
    -- Viemäriverkostoliittymä
    v.viemariverkosto_alkupvm AS "Viemäriverkostoliittymä alkupvm",
    -- Saostussäiliö
    ka.saostussailio_alkupvm AS "Saostussäiliö alkupvm",
    -- Pienpuhdistamo
    ka.pienpuhdistamo_alkupvm AS "Pienpuhdistamo alkupvm",
    -- Umpisäiliö
    ka.umpisailio_alkupvm AS "Umpisäiliö alkupvm",
    -- Vain harmaat vedet
    ka.harmaat_vedet_alkupvm AS "Vain harmaat vedet alkupvm",
    -- Kantovesi-ilmoitus
    ka.kantovesi_alkupvm AS "Kantovesi-ilmoitus alkupvm",
    -- Lietteen kompostointi-ilmoitus
    komp.kompostointi_alkupvm AS "Lietteen kompostointi-ilmoitus alkupvm",
    komp.kompostointi_loppupvm AS "Lietteen kompostointi-ilmoitus loppupvm"
FROM jkr.kohde ko
LEFT JOIN viemari v ON ko.id = v.kohde_id
LEFT JOIN kaivot ka ON ko.id = ka.kohde_id
LEFT JOIN kompostointi komp ON ko.id = komp.kohde_id
WHERE v.kohde_id IS NOT NULL 
   OR ka.kohde_id IS NOT NULL 
   OR komp.kohde_id IS NOT NULL;

ALTER VIEW jkr.v_kohteen_lietetiedot OWNER TO jkr_admin;

GRANT SELECT ON jkr.v_kohteen_lietetiedot TO jkr_viewer;

COMMENT ON VIEW jkr.v_kohteen_lietetiedot IS 'Kohteen lietetiedot QGIS-välilehteä varten. Sisältää viemäriverkostoliittymän, kaivotiedot ja lietteen kompostointi-ilmoituksen.';
