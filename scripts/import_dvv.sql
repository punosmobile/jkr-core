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
    sijainti_kunta as kunta_koodi -- names may be null. sijaintikunta is never null.
from jkr_dvv.osoite
on conflict do nothing; -- create one empty street for each kunta

-- Insert addresses to jkr.osoite
insert into jkr.osoite (osoitenumero, katu_id, rakennus_id, posti_numero)
select
    katu_numero as osoitenumero,
    case when (osoite."kadunnimi suomeksi" is not null)
        then (select id from jkr_osoite.katu where osoite."kadunnimi suomeksi" = katu.katunimi_fi and osoite.sijainti_kunta = katu.kunta_koodi)
        when (osoite."kadunnimi ruotsiksi" is not null)
        then (select id from jkr_osoite.katu where osoite."kadunnimi ruotsiksi" = katu.katunimi_sv and osoite.sijainti_kunta = katu.kunta_koodi)
        else (select id from jkr_osoite.katu where katu.katunimi_fi is null and katu.katunimi_sv is null and osoite.sijainti_kunta = katu.kunta_koodi) end as katu_id, -- each kunta has one empty street
    (select id from jkr.rakennus where osoite.rakennustunnus = rakennus.prt) as rakennus_id,
    nullif(posti_numero, '00000') as posti_numero -- 00000 addresses will be mapped to the empty street
from jkr_dvv.osoite
where
    exists (select 1 from jkr.rakennus where osoite.rakennustunnus = rakennus.prt) -- not all addresses have buildings
on conflict do nothing; -- osoitenumero and posti_numero may be null. katu_id always points to known street or empty street.

-- Insert owners to jkr.osapuoli
-- Step 1: Find distinct people. This will pick the first line with matching henkilötunnus,
-- if a person is listed multiple times.
insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, erikoisosoite, kunta, henkilotunnus)
select distinct on ("henkilötunnus")
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan vakinainen kotimainen asuinosoite" as katuosoite,
    omistaja."vakinaisen kotim osoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."vak os posti_ numero" as postinumero,
    concat_ws(e'\n', omistaja."omistajan ulkomainen lähiosoite", omistaja."ulkomaisen osoitteen paikkakunta", omistaja."ulkomaisen osoitteen valtion postinimi") as erikoisosoite,
    omistaja."omist koti_kunta" as kunta,
    omistaja."henkilötunnus" as henkilotunnus
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is not null
on conflict do nothing;

-- Step 2: Find distinct non-people. Luckily, DVV y-tunnus entries don't have foreign addresses.
-- y-tunnus does not have kotikunta either. y-tunnus always has postiosoite instead of asuinosoite.
insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, ytunnus)
select distinct on ("y_tunnus")
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan postiosoite" as katuosoite,
    omistaja."postiosoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."postios posti_numero" as postinumero,
    omistaja."y_tunnus" as ytunnus
from jkr_dvv.omistaja
where omistaja."y_tunnus" is not null
on conflict do nothing;

-- Step 3: Create all owners with missing henkilötunnus/y-tunnus as separate rows.
-- Any owners without henkilötunnus/y-tunnus do not have vakinainen asuinosoite or kotikunta or
-- foreign address.
alter table jkr.osapuoli add column rakennustunnus text;

insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, rakennustunnus)
select distinct -- There are some duplicate rows with identical address data
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan postiosoite" as katuosoite,
    omistaja."postiosoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."postios posti_numero" as postinumero,
    omistaja."rakennustunnus" as rakennustunnus -- We need rakennustunnus to match each row
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is null and
    omistaja."y_tunnus" is null and
    not exists (
        select 1 from jkr.rakennus r
        join jkr.rakennuksen_omistajat ro on r.id = ro.rakennus_id
        join jkr.osapuoli op on ro.osapuoli_id = op.id
        where r.prt = omistaja.rakennustunnus and op.nimi = omistaja."omistajan nimi"
        ) -- Only add those names each building does not have listed as owners yet.
          -- Note that this may introduce multiple owners with the same name for each building
          -- if there are multiple such rows in the same file. They will still have different
          -- addresses, though.
;

-- Insert owners to jkr.rakennuksen_omistajat
-- Step 1: Find all buildings owned by each owner, matching by henkilötunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."henkilötunnus" = osapuoli.henkilotunnus) as osapuoli_id
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict do nothing; -- DVV has registered some owners twice on different dates

-- Step 2: Find all buildings owned by each owner, matching by y-tunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."y_tunnus" = osapuoli.ytunnus) as osapuoli_id
from jkr_dvv.omistaja
where
    omistaja."y_tunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict do nothing; -- DVV has registered some owners twice on different dates

-- Step 3: Find all buildings owned by missing henkilötunnus/y-tunnus by name and address
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where
        -- all fields must be equal or null to match.
        -- some rows are exact duplicates. they should not be present in jkr.osapuoli.
        omistaja."omistajan nimi" is not distinct from osapuoli.nimi and
        omistaja."omistajan postiosoite" is not distinct from osapuoli.katuosoite and
        omistaja."postiosoitteen postitoimipaikka" is not distinct from osapuoli.postitoimipaikka and
        omistaja."postios posti_numero" is not distinct from osapuoli.postinumero and
        omistaja."rakennustunnus" = osapuoli.rakennustunnus
    ) as osapuoli_id
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is null and
    omistaja."y_tunnus" is null and
    exists (
        select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) and -- not all buildings might be listed
    not exists (
        select 1 from jkr.rakennus r
        join jkr.rakennuksen_omistajat ro on r.id = ro.rakennus_id
        join jkr.osapuoli op on ro.osapuoli_id = op.id
        where r.prt = omistaja.rakennustunnus and op.nimi = omistaja."omistajan nimi"
        ) -- Only add those names each building does not have listed as owners yet.
          -- Note that this may introduce multiple owners with the same name for each building
          -- if there are multiple such rows in the same file. They will still have different
          -- addresses, though.
on conflict do nothing; -- There are some duplicate rows with identical address data

alter table jkr.osapuoli drop column rakennustunnus;
