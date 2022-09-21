CREATE OR REPLACE FUNCTION jkr.update_velvoitteet(
	)
    RETURNS integer
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
  velvoitemalli RECORD;
  insert_sql text;
BEGIN
  FOR velvoitemalli in select id, saanto, voimassaolo from jkr.velvoitemalli where saanto is not null
  loop
    insert_sql := '
      insert into jkr.velvoite(kohde_id, velvoitemalli_id)
      select
        k.id,
        $1
      from jkr.kohde k
      where
        exists (select 1 from jkr.'||quote_ident(velvoitemalli.saanto)||' kohteet where k.id = kohteet.id)
        and k.voimassaolo && $2
      ON CONFLICT DO NOTHING
    ';
    EXECUTE insert_sql USING velvoitemalli.id, velvoitemalli.voimassaolo;
  end loop;
  RETURN 1;
END;
$BODY$;


create or replace function jkr.velvoite_status(date) RETURNS TABLE(velvoite_id int, pvm date, ok bool) AS
$$
DECLARE
  velvoitemalli RECORD;
  select_sql text;
BEGIN
  for velvoitemalli in select id, tayttymissaanto from jkr.velvoitemalli where tayttymissaanto is not null
  loop
    select_sql := '
      select
        v.id velvoite_id,
        $1,
        case when ok.kohde_id is not null then true else false end ok
      from
        jkr.kohde k
        join jkr.velvoite v
          on k.id = v.kohde_id
        join jkr.velvoitemalli vm
          on v.velvoitemalli_id = vm.id
        left join jkr.'||quote_ident(velvoitemalli.tayttymissaanto)||'($1) ok
          on v.kohde_id = ok.kohde_id
        where
          vm.id = $2
          and k.voimassaolo @> $1
          and vm.voimassaolo @> $1
    ';
    RETURN QUERY EXECUTE select_sql USING $1, velvoitemalli.id;
  end loop;
END;
$$ LANGUAGE plpgsql;


create or replace function jkr.tallenna_velvoite_status(date) RETURNS int AS
$$
  INSERT INTO jkr.velvoite_status (velvoite_id, pvm, ok, tallennuspvm)
  select velvoite_id, pvm, ok, CURRENT_DATE from jkr.velvoite_status($1)
  ON CONFLICT (velvoite_id, pvm) DO UPDATE
    SET
      ok = EXCLUDED.ok,
      tallennuspvm = CURRENT_DATE
  ;
  SELECT 1;
$$ LANGUAGE SQL;

