create or replace function jkr.pitka_kitu_2_lyhyt(text) RETURNS text AS $$
  SELECT substring($1,1,3)::int||'-'||substring($1,4,3)::int||'-'||substring($1,7,4)::int||'-'||substring($1,11,4)::int
$$ LANGUAGE SQL STABLE PARALLEL SAFE;
