-- Update functions --

-- Update loppupvm for previous eldest in the appartment when a new eldest is inserterd.
--TODO! This should work if we only want a single active eldest per appartment.
create or replace function update_loppupvm() returns trigger as $$
begin
    update jkr.rakennuksen_vanhimmat
    set loppupvm = new.alkupvm - interval '1 day'
    where rakennus_id = new.rakennus_id
    and osapuoli_id != new.osapuoli_id
    and osapuoli_id != null
    and huoneistokirjain = new.huoneistokirjain
    and huoneistonumero = new.huoneistonumero
    and loppupvm is null;
    return new;
end;
$$ language plpgsql;

-- Update omistuksen_loppupvm for previous owner, when new owner is inserted.
-- TODO! Fix this.
--create or replace function update_omistuksen_loppupvm() returns trigger as $$
--begin
    --update jkr.rakennuksen_omistajat
    --set omistuksen_loppupvm = new.omistuksen_alkupvm - interval '1 day'
    --where rakennus_id = new.rakennus_id
    --and osapuoli_id != new.osapuoli_id
    --and osapuoli_id != null
    --and omistuksen_loppupvm is null;
    --return new;
--end;
--$$ language plpgsql;

-- update omistuksen_loppupvm via a function
-- what do we want to do with omistuksen_loppupvm when the building doesn't exist anymore or the building is not owned by anyone?
-- currently what happens is that the omistuksen_loppupvm becomes the alkupvm - 1 day.
-- should the setting of omistuksen_loppupvm be skipped in that case?
-- or maybe there is something wrong with the inserting of owners when updating with new dvv-data?
-- TODO! This function is quite slow, any faster way to iterate through these records? Testing is painfully slow...
create or replace function update_omistuksen_loppupvm() returns void as $$
declare
    owners_with_henkilotunnus record;
    owners_with_ytunnus record;
    owners_without_henkilotunnus_or_ytunnus record;
begin
    for owners_with_henkilotunnus in select r.rakennus_id, r.osapuoli_id, o.henkilotunnus, rk.prt, r.omistuksen_alkupvm, r.omistuksen_loppupvm
        from jkr.rakennuksen_omistajat r
        join jkr.osapuoli o on r.osapuoli_id = o.id
        join jkr.rakennus rk on r.rakennus_id = rk.id
        where not exists (
            select 1 from jkr_dvv.omistaja od
            where od."rakennustunnus" = rk.prt
            and o.henkilotunnus is not null
            and od."henkilötunnus" = o.henkilotunnus
            and to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') = r.omistuksen_alkupvm
        )
    loop
        select to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') - interval '1 day'
        into owners_with_henkilotunnus.omistuksen_loppupvm
        from jkr_dvv.omistaja od
        where od."rakennustunnus" = owners_with_henkilotunnus.prt;

        update jkr.rakennuksen_omistajat
        set omistuksen_loppupvm = owners_with_henkilotunnus.omistuksen_loppupvm
        where rakennus_id = owners_with_henkilotunnus.rakennus_id
        and osapuoli_id = owners_with_henkilotunnus.osapuoli_id
        and omistuksen_alkupvm = owners_with_henkilotunnus.omistuksen_alkupvm
        and omistuksen_loppupvm is null;
    end loop;

    for owners_with_ytunnus in select r.rakennus_id, r.osapuoli_id, o.ytunnus, rk.prt, r.omistuksen_alkupvm, r.omistuksen_loppupvm
        from jkr.rakennuksen_omistajat r
        join jkr.osapuoli o on r.osapuoli_id = o.id
        join jkr.rakennus rk on r.rakennus_id = rk.id
        where not exists (
            select 1 from jkr_dvv.omistaja od
            where od."rakennustunnus" = rk.prt
            and o.ytunnus is not null
            and o.tiedontuottaja_tunnus = 'dvv'
            and od."y_tunnus" = o.ytunnus
            and to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') = r.omistuksen_alkupvm
        )
    loop
        select to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') - interval '1 day'
        into owners_with_ytunnus.omistuksen_loppupvm
        from jkr_dvv.omistaja od
        where od."rakennustunnus" = owners_with_ytunnus.prt;

        update jkr.rakennuksen_omistajat
        set omistuksen_loppupvm = owners_with_ytunnus.omistuksen_loppupvm
        where rakennus_id = owners_with_ytunnus.rakennus_id
        and osapuoli_id = owners_with_ytunnus.osapuoli_id
        and omistuksen_alkupvm = owners_with_ytunnus.omistuksen_alkupvm
        and omistuksen_loppupvm is null;
    end loop;

    for owners_without_henkilotunnus_or_ytunnus in select r.rakennus_id, r.osapuoli_id, o.nimi, o.katuosoite, o.postitoimipaikka, o.postitoimipaikka, o.postinumero, rk.prt, r.omistuksen_alkupvm, r.omistuksen_loppupvm
        from jkr.rakennuksen_omistajat r
        join jkr.osapuoli o on r.osapuoli_id = o.id
        join jkr.rakennus rk on r.rakennus_id = rk.id
        where not exists (
            select 1 from jkr_dvv.omistaja od
            where od."rakennustunnus" = rk.prt
            and o.ytunnus is null
            and o.henkilotunnus is null
            and od."omistajan nimi" = o.nimi
            and od."omistajan postiosoite" = o.katuosoite
            and od."postiosoitteen postitoimipaikka" = o.postitoimipaikka
            and od."postios posti_numero" = o.postinumero
            and o.tiedontuottaja_tunnus = 'dvv'
            and to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') = r.omistuksen_alkupvm
        )
    loop
        select to_date(od."omistuksen alkupäivä"::text, 'YYYYMMDD') - interval '1 day'
        into owners_without_henkilotunnus_or_ytunnus.omistuksen_loppupvm
        from jkr_dvv.omistaja od
        where od."rakennustunnus" = owners_without_henkilotunnus_or_ytunnus.prt;

        update jkr.rakennuksen_omistajat
        set omistuksen_loppupvm = owners_without_henkilotunnus_or_ytunnus.omistuksen_loppupvm
        where rakennus_id = owners_without_henkilotunnus_or_ytunnus.rakennus_id
        and osapuoli_id = owners_without_henkilotunnus_or_ytunnus.osapuoli_id
        and omistuksen_alkupvm = owners_without_henkilotunnus_or_ytunnus.omistuksen_alkupvm
        and omistuksen_loppupvm is null;
    end loop;
end;
$$ language plpgsql;

-- Matches and updates information (nimi, postioimipaikka, postinumero) for osapuoli with known ytunnus and missing information
create or replace function update_osapuoli_with_ytunnus() returns void as $$
declare
    rec jkr.osapuoli%rowtype;
begin
    for rec in select * from jkr.osapuoli where ytunnus is not null and henkilotunnus is null and tiedontuottaja_tunnus = 'dvv'
        and (nimi is null
        or katuosoite is null
        or postitoimipaikka is null
        or postinumero is null)
    loop
        update jkr.osapuoli
        set nimi = (
                select nimi from jkr.osapuoli
                where ytunnus = rec.ytunnus
                and nimi is not null
                and tiedontuottaja_tunnus = 'dvv'
                limit 1
            ),
            katuosoite = (
                select katuosoite from jkr.osapuoli
                where ytunnus = rec.ytunnus
                and katuosoite is not null
                and tiedontuottaja_tunnus = 'dvv'
                limit 1
            ),
            postitoimipaikka = (
                select postitoimipaikka from jkr.osapuoli
                where ytunnus = rec.ytunnus
                and postitoimipaikka is not null
                and tiedontuottaja_tunnus = 'dvv'
                limit 1
            ),
            postinumero = (
                select postinumero from jkr.osapuoli
                where ytunnus = rec.ytunnus
                and postinumero is not null
                and tiedontuottaja_tunnus = 'dvv'
                limit 1
            )
        where
            ytunnus = rec.ytunnus;   
    end loop;
   end;
$$ language plpgsql;


-- Matches and updates information (nimi, postitomipaikka, postinumero) for osapuoli with known henkilotunnus and missing information. 
create or replace function update_osapuoli_with_henkilotunnus() returns void as $$
declare
    rec jkr.osapuoli%rowtype;
begin
    for rec in select * from jkr.osapuoli where henkilotunnus is not null and ytunnus is null
        and (nimi is null
        or postitoimipaikka is null
        or postinumero is null)
    loop
        update jkr.osapuoli
        set nimi = (
                select nimi from jkr.osapuoli
                where henkilotunnus = rec.henkilotunnus
                and nimi is not null
                limit 1         
            ),
            postitoimipaikka = (
                select postitoimipaikka from jkr.osapuoli
                where henkilotunnus = rec.henkilotunnus
                and postitoimipaikka is not null
                limit 1
            ),
            postinumero = (
                select postinumero from jkr.osapuoli
                where henkilotunnus = rec.henkilotunnus
                and postinumero is not null
                limit 1
            )
        where
            henkilotunnus = rec.henkilotunnus;
    end loop;
   end;
$$ language plpgsql;

-- Update triggers --
-- Trigger for updating eldest, called when inserting new eldest with no conflicts.
drop trigger if exists update_loppupvm_trigger on jkr.rakennuksen_vanhimmat;
create trigger update_loppupvm_trigger
after insert on jkr.rakennuksen_vanhimmat
for each row
when (new.loppupvm is null)
execute function update_loppupvm();

-- Trigger for updating owner, called when inserting new owner with no conflicts.
--drop trigger if exists update_omistuksen_loppupvm_trigger on jkr.rakennuksen_omistajat;
--create trigger update_omistuksen_loppupvm_trigger
--after insert on jkr.rakennuksen_omistajat
--for each row
--when (new.omistuksen_loppupvm is null)
--execute function update_omistuksen_loppupvm();

-- Inserts
-- Add dvv tiedontuottaja
insert into jkr_koodistot.tiedontuottaja values
    ('dvv', 'Digi- ja väestötietovirasto')
on conflict do nothing;

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
-- update all existing buildings
on conflict (prt) do update
set
    kiinteistotunnus = excluded.kiinteistotunnus,
    onko_viemari = excluded.onko_viemari,
    geom = excluded.geom,
    kayttoonotto_pvm = excluded.kayttoonotto_pvm,
    kaytossaolotilanteenmuutos_pvm = excluded.kaytossaolotilanteenmuutos_pvm,
    rakennuksenkayttotarkoitus_koodi = excluded.rakennuksenkayttotarkoitus_koodi,
    rakennuksenolotila_koodi = excluded.rakennuksenolotila_koodi;

-- Insert streets to jkr_osoite.katu
-- jkr_osoite.kunta must be filled in the database by running import_posti.sql first!
-- Step 1: Import streets with names in two languages first. This way, we will not import
-- incomplete rows if complete rows exist.
insert into jkr_osoite.katu (katunimi_fi, katunimi_sv, kunta_koodi)
select distinct
    "kadunnimi suomeksi" as katunimi_fi,
    "kadunnimi ruotsiksi" as katunimi_sv,
    sijainti_kunta as kunta_koodi -- names may be null. sijaintikunta is never null.
from jkr_dvv.osoite
where
    "kadunnimi suomeksi" is not null and "kadunnimi ruotsiksi" is not null
on conflict do nothing;

-- Step 2: Import streets with max one language name. This way they will not override
-- any names with two languages.
insert into jkr_osoite.katu (katunimi_fi, katunimi_sv, kunta_koodi)
select distinct
    "kadunnimi suomeksi" as katunimi_fi,
    "kadunnimi ruotsiksi" as katunimi_sv,
    sijainti_kunta as kunta_koodi -- names may be null. sijaintikunta is never null.
from jkr_dvv.osoite
where
    "kadunnimi suomeksi" is null or "kadunnimi ruotsiksi" is null
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
-- on conflict (katu_id) do update -- add constraint for do update? No uniques here. Or do this with a function also?
-- set
    -- osoitenumero = excluded.osoitenumero,
    -- katu_id = excluded.katu_id,
    -- posti_numero = excluded.posti_numero;


-- Insert owners to jkr.osapuoli
-- Step 1: Find distinct people. This will pick the first line with matching henkilötunnus,
-- if a person is listed multiple times.
insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, erikoisosoite, kunta, henkilotunnus, tiedontuottaja_tunnus)
select distinct on ("henkilötunnus")
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan vakinainen kotimainen asuinosoite" as katuosoite,
    omistaja."vakinaisen kotim osoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."vak os posti_ numero" as postinumero,
    concat_ws(e'\n', omistaja."omistajan ulkomainen lähiosoite", omistaja."ulkomaisen osoitteen paikkakunta", omistaja."ulkomaisen osoitteen valtion postinimi") as erikoisosoite,
    omistaja."omist koti_kunta" as kunta,
    omistaja."henkilötunnus" as henkilotunnus,
    'dvv' as tiedontuottaja_tunnus
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is not null
-- Updates the person's information, if new insert conflicts with existing one.
on conflict (henkilotunnus) where tiedontuottaja_tunnus = 'dvv' do update
set
    nimi = excluded.nimi,
    katuosoite = excluded.katuosoite,
    postitoimipaikka = excluded.postitoimipaikka,
    postinumero = excluded.postinumero,
    erikoisosoite = excluded.erikoisosoite,
    kunta = excluded.kunta,
    henkilotunnus = excluded.henkilotunnus,
    tiedontuottaja_tunnus = excluded.tiedontuottaja_tunnus;

-- Step 2: Find distinct non-people. Luckily, DVV y-tunnus entries don't have foreign addresses.
-- y-tunnus does not have kotikunta either. y-tunnus always has postiosoite instead of asuinosoite.
insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, ytunnus, tiedontuottaja_tunnus)
select distinct on ("y_tunnus")
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan postiosoite" as katuosoite,
    omistaja."postiosoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."postios posti_numero" as postinumero,
    omistaja."y_tunnus" as ytunnus,
    'dvv' as tiedontuottaja_tunnus
from jkr_dvv.omistaja
where omistaja."y_tunnus" is not null
on conflict (ytunnus) where tiedontuottaja_tunnus = 'dvv' do update
set
    nimi = excluded.nimi,
    katuosoite = excluded.katuosoite,
    postitoimipaikka = excluded.postitoimipaikka,
    postinumero = excluded.postinumero,
    tiedontuottaja_tunnus = excluded.tiedontuottaja_tunnus;

-- Step 3: Create all owners with missing henkilötunnus/y-tunnus as separate rows.
-- Any owners without henkilötunnus/y-tunnus do not have vakinainen asuinosoite or kotikunta or
-- foreign address.
alter table jkr.osapuoli add column rakennustunnus text;

insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, rakennustunnus, tiedontuottaja_tunnus)
select distinct -- There are some duplicate rows with identical address data
    omistaja."omistajan nimi" as nimi,
    omistaja."omistajan postiosoite" as katuosoite,
    omistaja."postiosoitteen postitoimipaikka" as postitoimipaikka,
    omistaja."postios posti_numero" as postinumero,
    omistaja."rakennustunnus" as rakennustunnus, -- We need rakennustunnus to match each row
    'dvv' as tiedontuottaja_tunnus
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

-- 
select update_omistuksen_loppupvm();

-- Insert owners to jkr.rakennuksen_omistajat
-- TODO! Fix rakennuksen_omistajat insert, currently duplicates every entry.
-- Step 1: Find all buildings owned by each owner, matching by henkilötunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."henkilötunnus" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
--on conflict on constraint unique_rakennuksen_omistajat do nothing; -- DVV has registered some owners twice on different dates
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do nothing;

-- Step 2: Find all buildings owned by each owner, matching by y-tunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."y_tunnus" = osapuoli.ytunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm
from jkr_dvv.omistaja
where
    omistaja."y_tunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do nothing; -- DVV has registered some owners twice on different dates

-- Step 3: Find all buildings owned by missing henkilötunnus/y-tunnus by name and address
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where
        -- all fields must be equal or null to match.
        -- some rows are exact duplicates. they should not be present in jkr.osapuoli.
        omistaja."omistajan nimi" is not distinct from osapuoli.nimi and
        omistaja."omistajan postiosoite" is not distinct from osapuoli.katuosoite and
        omistaja."postiosoitteen postitoimipaikka" is not distinct from osapuoli.postitoimipaikka and
        omistaja."postios posti_numero" is not distinct from osapuoli.postinumero and
        omistaja."rakennustunnus" = osapuoli.rakennustunnus and
        osapuoli.tiedontuottaja_tunnus = 'dvv'
    ) as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm
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
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do nothing; -- There are some duplicate rows with identical address data

select update_osapuoli_with_ytunnus();
select update_osapuoli_with_henkilotunnus();
-- select count(*) from jkr.osapuoli where henkilotunnus is null;

alter table jkr.osapuoli drop column rakennustunnus;

-- Insert elders to jkr.osapuoli
insert into jkr.osapuoli (nimi, katuosoite, postitoimipaikka, postinumero, kunta, henkilotunnus, tiedontuottaja_tunnus)
select distinct on ("huoneiston vanhin asukas (henkilötunnus)")
    concat_ws(' ', vanhin."sukunimi", vanhin."etunimet") as nimi,
    vanhin."vakinainen kotimainen asuinosoite" as katuosoite,
    vanhin."vakinaisen kotim osoitteen postitoimipaikka" as postitoimipaikka,
    vanhin."vak os posti_ numero" as postinumero,
    vanhin.sijainti_kunta as kunta,
    vanhin."huoneiston vanhin asukas (henkilötunnus)" as henkilotunnus,
    'dvv' as tiedontuottaja_tunnus
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null
on conflict (henkilotunnus) do update -- some elders (e.g. owners) already exist
-- updates existing osapuoli
set
    nimi = excluded.nimi,
    katuosoite = excluded.katuosoite,
    postitoimipaikka = excluded.postitoimipaikka,
    postinumero = excluded.postinumero,
    kunta = excluded.kunta,
    tiedontuottaja_tunnus = excluded.tiedontuottaja_tunnus
where
    jkr.osapuoli.henkilotunnus = excluded.henkilotunnus;
    
-- Insert elders to jkr.rakennuksen_vanhimmat
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
    -- this isnt preventing duplicate inserts... why?
-- on conflict (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm) do nothing;
on conflict do nothing;
