-- Insert buildings to jkr_rakennus
insert into jkr.rakennus (prt, kiinteistotunnus, onko_viemari, geom, kayttoonotto_pvm, kaytossaolotilanteenmuutos_pvm, rakennuksenkayttotarkoitus_koodi, rakennuksenolotila_koodi)
select 
    rakennustunnus as prt,
    "sijaintikiinteistön tunnus" as kiinteistotunnus,
    viemäri::boolean as onko_viemari,
    ST_GeomFromText('POINT('||itä_koordinaatti||' '||pohjois_koordinaatti||')', 3067) as geom,
    case when length("valmis_tumis_
päivä"::text) = 8 then to_date("valmis_tumis_
päivä"::text, 'YYYYMMDD') else null end as kayttoonotto_pvm,
    to_date("käytössä_olotilanteen muutospäivä"::text, 'YYYYMMDD') as kaytossaolotilanteenmuutos_pvm,
    "käyttö_tarkoitus" as rakennuksenkayttotarkoitus_koodi,
    "käytös_säolo_tilanne" as rakennuksenolotila_koodi
from jkr_dvv.rakennus
on conflict do nothing
;

-- Insert streets to jkr_osoite.katu
-- jkr_osoite.kunta must be filled in the database by running import_posti.sql first!
insert into jkr_osoite.katu (katunimi_fi, katunimi_sv, kunta_koodi)
select distinct
    "kadunnimi suomeksi" as katunimi_fi,
    "kadunnimi ruotsiksi" as katunimi_sv,
    sijainti_kunta as kunta_koodi
from jkr_dvv.osoite
where "kadunnimi suomeksi" is not null or "kadunnimi ruotsiksi" is not null  -- not all places have street address
on conflict do nothing;

-- Insert addresses to jkr.osoite
-- Assume Finnish kadunnimi is given. Some (two) entries might have errors because of this.
insert into jkr.osoite (osoitenumero, katu_id, rakennus_id, posti_numero)
select
    katu_numero as osoitenumero,
    (select id from jkr_osoite.katu where osoite."kadunnimi suomeksi" = katu.katunimi_fi and osoite.sijainti_kunta = katu.kunta_koodi) as katu_id,
    (select id from jkr.rakennus where osoite.rakennustunnus = rakennus.prt) as rakennus_id,
    posti_numero as posti_numero
from jkr_dvv.osoite
where
    exists (select 1 from jkr.rakennus where osoite.rakennustunnus = rakennus.prt) -- not all addresses have buildings
    and posti_numero != '00000'
on conflict do nothing;
