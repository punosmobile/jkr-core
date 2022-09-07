ALTER TABLE jkr.osapuoli RENAME facta_id TO ulkoinen_id;
ALTER INDEX uidx_osapuoli_facta_id RENAME TO uidx_osapuoli_ulkoinen_id;
