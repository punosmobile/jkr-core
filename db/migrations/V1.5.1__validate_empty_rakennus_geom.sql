UPDATE jkr.rakennus
SET geom = NULL
WHERE st_x(geom) = 'infinity' OR st_y(geom) = 'infinity';

CREATE FUNCTION jkr.fix_empty_point ()
	RETURNS trigger
	LANGUAGE plpgsql
	VOLATILE
	CALLED ON NULL INPUT
	SECURITY INVOKER
	PARALLEL SAFE
	COST 100
	AS $$
    BEGIN
        IF st_x(NEW.geom) = 'infinity' OR st_y(NEW.geom) = 'infinity' THEN
          RAISE NOTICE 'Converted POINT(infinity infinity) to NULL';
          NEW.geom = NULL;
        END IF;
        RETURN NEW;
    END;
$$;
ALTER FUNCTION jkr.fix_empty_point() OWNER TO jkr_admin;


CREATE TRIGGER trg_fix_empty_rakennus_point
	BEFORE INSERT OR UPDATE
	ON jkr.rakennus
	FOR EACH ROW
	EXECUTE PROCEDURE jkr.fix_empty_point();
