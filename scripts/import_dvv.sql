insert into jkr.rakennus
select 
    rakennustunnus as prt,
    sijaintikiinteistön_tunnus as kiinteistotunnus,
    viemäri::boolean as onko_viemari,
    ST_GeomFromText('POINT('||itä_koordinaatti||' '||pohjois_koordinaatti||')', 3067) as geom,
    käytössä_olotilanteen_muutospäivä as kayttoonotto_pvm
from jkr_dvv.rakennus
on conflict do nothing
;
