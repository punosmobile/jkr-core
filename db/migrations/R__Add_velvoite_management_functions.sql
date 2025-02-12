CREATE OR REPLACE FUNCTION jkr.update_velvoitteet()
    RETURNS integer
    LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
  velvoitemalli RECORD;
  insert_velvoite_sql text;
  yhteenvetomalli RECORD;
  insert_yhteenveto_sql text;
BEGIN
  -- Velvoitemallit
  FOR velvoitemalli in select vm.id, vm.saanto, vm.voimassaolo, jt.selite as jatetyyppi_selite
  from jkr.velvoitemalli vm 
  left join jkr_koodistot.jatetyyppi jt on vm.jatetyyppi_id = jt.id 
  where vm.saanto is not null
  loop                
    insert_velvoite_sql := '
      insert into jkr.velvoite(kohde_id, velvoitemalli_id)
      select distinct
        k.id,
        $1
      from jkr.kohde k
      where
        exists (select 1 from jkr.'||quote_ident(velvoitemalli.saanto)||' kohteet where k.id = kohteet.id)
        and k.voimassaolo && $2
        and k.kohdetyyppi_id != 8
        and (
          k.kohdetyyppi_id not in (5,6)
          OR 
          (k.kohdetyyppi_id = 5 and ''' || velvoitemalli.jatetyyppi_selite || ''' = ''Sekajäte'')  -- HAPA
          OR
          (k.kohdetyyppi_id = 6 and ''' || velvoitemalli.jatetyyppi_selite || ''' in (''Sekajäte'', ''Biojäte''))  -- BIOHAPA
        )
      ON CONFLICT DO NOTHING
    ';
    EXECUTE insert_velvoite_sql 
    USING velvoitemalli.id, velvoitemalli.voimassaolo;
  end loop;

  -- Velvoiteyhteenvetomallit
  FOR yhteenvetomalli in select id, saanto, voimassaolo 
  from jkr.velvoiteyhteenvetomalli where saanto is not null
  loop
    insert_yhteenveto_sql := '
      insert into jkr.velvoiteyhteenveto(kohde_id, velvoiteyhteenvetomalli_id)
      select distinct
        k.id,
        $1
      from jkr.kohde k
      where
        exists (select 1 from jkr.'||quote_ident(yhteenvetomalli.saanto)||' kohteet where k.id = kohteet.id)
        and k.voimassaolo && $2
        and k.kohdetyyppi_id != 8
      ON CONFLICT DO NOTHING
    ';
    EXECUTE insert_yhteenveto_sql 
    USING yhteenvetomalli.id, yhteenvetomalli.voimassaolo;
  end loop;
  
  RETURN 1;
END;
$BODY$;

CREATE OR REPLACE FUNCTION jkr.velvoite_status(loppupvm date) 
RETURNS TABLE(velvoite_id int, jakso daterange, ok bool) AS
$$
DECLARE
  velvoitemalli RECORD;
  select_sql text;
  jakso_alku date := DATE_TRUNC('quarter', loppupvm) - INTERVAL '6 months';
  jakso_loppu date := DATE_TRUNC('quarter', loppupvm) + INTERVAL '3 months' - INTERVAL '1 day';
BEGIN
  for velvoitemalli in select vm.id, vm.tayttymissaanto, vm.jatetyyppi_id, jt.selite as jatetyyppi_selite
  from jkr.velvoitemalli vm
  left join jkr_koodistot.jatetyyppi jt on vm.jatetyyppi_id = jt.id
  where vm.tayttymissaanto is not null
  loop
    select_sql := '
      select
        v.id velvoite_id,
        daterange($1, $2) AS jakso,
        case when ok.kohde_id is not null then true else false end ok
      from
        jkr.kohde k
        join jkr.velvoite v on k.id = v.kohde_id
        join jkr.velvoitemalli vm on v.velvoitemalli_id = vm.id
        left join jkr.'||quote_ident(velvoitemalli.tayttymissaanto)||'(daterange($1, $2)) ok
          on v.kohde_id = ok.kohde_id
      where
        vm.id = $3
        and k.voimassaolo && daterange($1, $2)
        and vm.voimassaolo && daterange($1, $2)
        and k.kohdetyyppi_id != 8
        and (
          k.kohdetyyppi_id not in (5,6)  -- normaalit kohteet
          OR 
          (k.kohdetyyppi_id = 5 and ''' || velvoitemalli.jatetyyppi_selite || ''' = ''Sekajäte'')  -- HAPA
          OR
          (k.kohdetyyppi_id = 6 and ''' || velvoitemalli.jatetyyppi_selite || ''' in (''Sekajäte'', ''Biojäte''))  -- BIOHAPA
        )
    ';

    RETURN QUERY EXECUTE select_sql 
    USING jakso_alku, jakso_loppu, velvoitemalli.id;
  end loop;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION jkr.velvoiteyhteenveto_status(loppupvm date) 
RETURNS TABLE(velvoiteyhteenveto_id int, jakso daterange, ok bool) AS
$$
DECLARE
  velvoiteyhteenvetomalli RECORD;
  select_sql text;
  jakso_alku date := DATE_TRUNC('quarter', loppupvm) - INTERVAL '6 months';
  jakso_loppu date := DATE_TRUNC('quarter', loppupvm) + INTERVAL '3 months' - INTERVAL '1 day';
BEGIN
  CREATE TEMP TABLE temp_status (
    velvoiteyhteenveto_id int,
    jakso daterange,
    ok bool,
    kohde_id int,
    luokitus int
  ) ON COMMIT DROP;

  FOR velvoiteyhteenvetomalli IN SELECT id, tayttymissaanto, luokitus 
  FROM jkr.velvoiteyhteenvetomalli 
  WHERE tayttymissaanto IS NOT null
  LOOP
    select_sql := '
      select
        v.id velvoiteyhteenveto_id,
        daterange($1, $2) AS jakso,
        case when ok.kohde_id is not null then true else false end ok,
        k.id,
        vm.luokitus
      from
        jkr.kohde k
        join jkr.velvoiteyhteenveto v on k.id = v.kohde_id
        join jkr.velvoiteyhteenvetomalli vm on v.velvoiteyhteenvetomalli_id = vm.id
        left join jkr.'||quote_ident(velvoiteyhteenvetomalli.tayttymissaanto)||'(daterange($1, $2)) ok
          on v.kohde_id = ok.kohde_id
      where
        vm.id = $3
        and k.voimassaolo && daterange($1, $2)
        and vm.voimassaolo && daterange($1, $2)
        and k.kohdetyyppi_id != 8
    ';
    
    EXECUTE 'INSERT INTO temp_status ' || select_sql 
    USING jakso_alku, jakso_loppu, velvoiteyhteenvetomalli.id;
  END LOOP;

  -- Käsitellään tilanteet joissa samalla kohteella on parempi luokitus
  WITH yhteenvedot_joilla_parempi_luokitus AS (
    SELECT t1.*
    FROM temp_status t1
    WHERE EXISTS (
      SELECT 1
      FROM temp_status t2
      WHERE t2.kohde_id = t1.kohde_id
        AND t2.ok = true
        AND t2.luokitus < t1.luokitus
    )
  )
  UPDATE temp_status
  SET ok = false
  WHERE (kohde_id, luokitus) IN (
    SELECT kohde_id, luokitus
    FROM yhteenvedot_joilla_parempi_luokitus
  );  

  -- Palautetaan lopulliset tulokset
  RETURN QUERY 
  SELECT temp_status.velvoiteyhteenveto_id, temp_status.jakso, temp_status.ok 
  FROM temp_status;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS jkr.tallenna_velvoite_status;
create or replace function jkr.tallenna_velvoite_status(date) RETURNS int AS
$$
  -- Tallennetaan velvoitteiden status
  INSERT INTO jkr.velvoite_status (velvoite_id, jakso, ok, tallennuspvm)
  select velvoite_id, jakso, ok, CURRENT_DATE from jkr.velvoite_status($1)
  ON CONFLICT (velvoite_id, jakso) DO UPDATE
    SET
      ok = EXCLUDED.ok,
      tallennuspvm = CURRENT_DATE
  ;
  -- Päivitetään velvoitteiden materialisoitu näkymä
  REFRESH MATERIALIZED VIEW jkr.v_velvoitteiden_kohteet;

  -- Tallennetaan velvoiteyhteenvetojen status  
  INSERT INTO jkr.velvoiteyhteenveto_status (velvoiteyhteenveto_id, jakso, ok, tallennuspvm)
  select velvoiteyhteenveto_id, jakso, ok, CURRENT_DATE from jkr.velvoiteyhteenveto_status($1)
  ON CONFLICT (velvoiteyhteenveto_id, jakso) DO UPDATE
    SET
      ok = EXCLUDED.ok,
      tallennuspvm = CURRENT_DATE
  ;
  -- Päivitetään yhteenvetojen materialisoitu näkymä
  REFRESH MATERIALIZED VIEW jkr.v_velvoiteyhteenvetojen_kohteet;
  
  SELECT 1;
$$ LANGUAGE SQL;