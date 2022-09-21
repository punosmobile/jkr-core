-- object: jkr.kohteen_rakennusehdokkaat | type: TABLE --
-- DROP TABLE IF EXISTS jkr.kohteen_rakennusehdokkaat CASCADE;
CREATE TABLE jkr.kohteen_rakennusehdokkaat (
	kohde_id integer NOT NULL,
	rakennus_id integer NOT NULL,
	CONSTRAINT kohteen_rakennusehdokkaat_pk PRIMARY KEY (kohde_id,rakennus_id)
);
-- ddl-end --
ALTER TABLE jkr.kohteen_rakennusehdokkaat OWNER TO jkr_admin;
-- ddl-end --

-- object: idx_kohteen_rakennusehdokkaat_rakennus_id | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_kohteen_rakennusehdokkaat_rakennus_id CASCADE;
CREATE INDEX idx_kohteen_rakennusehdokkaat_rakennus_id ON jkr.kohteen_rakennusehdokkaat
USING btree
(
	rakennus_id
);
-- ddl-end --

-- object: kohde_fk | type: CONSTRAINT --
-- ALTER TABLE jkr.kohteen_rakennusehdokkaat DROP CONSTRAINT IF EXISTS kohde_fk CASCADE;
ALTER TABLE jkr.kohteen_rakennusehdokkaat ADD CONSTRAINT ehdokaskohde_fk FOREIGN KEY (kohde_id)
REFERENCES jkr.kohde (id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

-- object: rakennus_fk | type: CONSTRAINT --
-- ALTER TABLE jkr.kohteen_rakennusehdokkaat DROP CONSTRAINT IF EXISTS rakennus_fk CASCADE;
ALTER TABLE jkr.kohteen_rakennusehdokkaat ADD CONSTRAINT ehdokasrakennus_fk FOREIGN KEY (rakennus_id)
REFERENCES jkr.rakennus (id) MATCH FULL
ON DELETE CASCADE ON UPDATE CASCADE;
-- ddl-end --

CREATE FUNCTION jkr.trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat ()
	RETURNS trigger
	LANGUAGE plpgsql
	VOLATILE
	CALLED ON NULL INPUT
	SECURITY INVOKER
	PARALLEL UNSAFE
	COST 1
	AS $$
begin
  DELETE FROM jkr.kohteen_rakennusehdokkaat
  WHERE kohde_id = new.kohde_id;
  RETURN NULL;
end;
$$;
-- ddl-end --
ALTER FUNCTION jkr.trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat() OWNER TO jkr_admin;
-- ddl-end --

-- object: trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat | type: TRIGGER --
-- DROP TRIGGER IF EXISTS trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat ON jkr.kohteen_rakennukset CASCADE;
CREATE TRIGGER trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat
	AFTER INSERT
	ON jkr.kohteen_rakennukset
	FOR EACH ROW
	EXECUTE PROCEDURE jkr.trg_kohteen_rakennukset_ai_remove_from_rakennusehdokkaat();
