CREATE OR REPLACE VIEW jkr.v_kohteen_osapuolet_roolilla AS
SELECT 
    ROW_NUMBER() OVER () AS gid,  -- Yksilöivä avain QGISiä varten
    ko.kohde_id,
    ko.osapuoli_id,
    ko.osapuolenrooli_id,
    ro.selite AS osapuoli
FROM 
    jkr.kohteen_osapuolet ko
    INNER JOIN jkr_koodistot.osapuolenrooli ro ON ko.osapuolenrooli_id = ro.id;