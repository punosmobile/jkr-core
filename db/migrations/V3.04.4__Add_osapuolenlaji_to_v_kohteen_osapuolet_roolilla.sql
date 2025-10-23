-- Add osapuolenlaji to v_kohteen_osapuolet_roolilla view

CREATE OR REPLACE VIEW jkr.v_kohteen_osapuolet_roolilla AS
SELECT 
    ROW_NUMBER() OVER () AS gid,
    ko.kohde_id,
    ko.osapuoli_id,
    ko.osapuolenrooli_id,
    ro.selite AS osapuoli,
    ol.selite AS osapuolenlaji
FROM 
    jkr.kohteen_osapuolet ko
    INNER JOIN jkr_koodistot.osapuolenrooli ro ON ko.osapuolenrooli_id = ro.id
    INNER JOIN jkr.osapuoli op ON ko.osapuoli_id = op.id
    LEFT JOIN jkr_koodistot.osapuolenlaji ol ON op.osapuolenlaji_koodi = ol.koodi;
