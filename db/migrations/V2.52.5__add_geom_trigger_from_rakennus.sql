CREATE OR REPLACE FUNCTION jkr.update_kohde_geom_from_rakennus()

RETURNS trigger AS
$$
BEGIN
  -- Päivitä kaikki kohteet, joissa tämä rakennus on mukana
  UPDATE jkr.kohde
  SET geom = jkr.create_kohde_geom(kr.kohde_id)
  FROM jkr.kohteen_rakennukset kr
  WHERE kr.rakennus_id = NEW.id
    AND jkr.kohde.id = kr.kohde_id;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Päivitä rakennuksen kohteen geometria kun rakennuksen geometria muuttuu
CREATE TRIGGER trg_rakennus_geom_update
AFTER UPDATE OF geom
ON jkr.rakennus
FOR EACH ROW
EXECUTE FUNCTION jkr.update_kohde_geom_from_rakennus();