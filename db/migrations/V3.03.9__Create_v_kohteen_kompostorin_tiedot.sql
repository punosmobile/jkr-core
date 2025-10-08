CREATE OR REPLACE VIEW jkr.v_kohteen_kompostorin_tiedot AS
SELECT 
    ROW_NUMBER() OVER () AS gid,
    kk.kohde_id,
    kk.kompostori_id,
    k.alkupvm,
    k.loppupvm,
    k.voimassaolo,
    k.onko_kimppa,
    k.osoite_id,
    k.osapuoli_id
FROM 
    jkr.kompostorin_kohteet kk
    INNER JOIN jkr.kompostori k ON kk.kompostori_id = k.id;