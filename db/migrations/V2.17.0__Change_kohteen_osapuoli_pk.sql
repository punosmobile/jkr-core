ALTER TABLE jkr.kohteen_osapuolet
  DROP CONSTRAINT kohteen_osapuolet_pk;

ALTER TABLE jkr.kohteen_osapuolet
  ADD CONSTRAINT kohteen_osapuolet_pk PRIMARY KEY (kohde_id, osapuoli_id, osapuolenrooli_id);
