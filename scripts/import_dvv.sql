insert into jkr.rakennus (prt, kiinteistotunnus, onko_viemari, geom, kayttoonotto_pvm)
select 
    rakennustunnus as prt,
    "sijaintikiinteistön tunnus" as kiinteistotunnus,
    viemäri::boolean as onko_viemari,
    ST_GeomFromText('POINT('||itä_koordinaatti||' '||pohjois_koordinaatti||')', 3067) as geom,
    to_date("käytössä_olotilanteen muutospäivä"::text, 'YYYYMMDD') as kayttoonotto_pvm
from jkr_dvv.rakennus
on conflict do nothing
;
