SELECT to_date(:'formatted_date', 'YYYYMMDD') AS poimintapvm \gset


-- Add dvv tiedontuottaja
insert into jkr_koodistot.tiedontuottaja values
    ('dvv', 'Digi- ja väestötietovirasto')
on conflict do nothing;


-- Add temporary column to easily sort buildings that exists in the dvv.
alter table jkr.rakennus add column found_in_dvv boolean;


-- Insert buildings to jkr_rakennus
insert into jkr.rakennus (prt, kiinteistotunnus, onko_viemari, geom, kayttoonotto_pvm, kaytossaolotilanteenmuutos_pvm, rakennuksenkayttotarkoitus_koodi, rakennuksenolotila_koodi, rakennusluokka_2018, found_in_dvv)
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
    "käytös_säolo_tilanne" as rakennuksenolotila_koodi,
    "rakennus_
luokka" as rakennusluokka_2018,
    true as found_in_dvv
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
    rakennuksenolotila_koodi = excluded.rakennuksenolotila_koodi,
    rakennusluokka_2018 = excluded.rakennusluokka_2018,
    found_in_dvv = true;


SELECT update_kaytostapoisto_pvm(:'poimintapvm');
alter table jkr.rakennus drop column found_in_dvv;


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


alter table jkr.rakennuksen_omistajat add column found_in_dvv boolean;
alter table jkr.rakennuksen_vanhimmat add column found_in_dvv boolean;


-- Insert owners to jkr.rakennuksen_omistajat
-- Step 1: Find all buildings owned by each owner, matching by henkilötunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm, found_in_dvv)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."henkilötunnus" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm,
    true as found_in_dvv
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
-- DVV has registered some owners twice on different dates
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do update
    set found_in_dvv = true;


-- Step 2: Find all buildings owned by each owner, matching by y-tunnus
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm, found_in_dvv)
select
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where omistaja."y_tunnus" = osapuoli.ytunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm,
    true as found_in_dvv
from jkr_dvv.omistaja
where
    omistaja."y_tunnus" is not null and
    exists (select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do update -- DVV has registered some owners twice on different dates
    set found_in_dvv = true;


-- Step 3: Find all buildings owned by missing henkilötunnus/y-tunnus by name and address
insert into jkr.rakennuksen_omistajat (rakennus_id, osapuoli_id, omistuksen_alkupvm, found_in_dvv)
select distinct
    (select id from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where
        -- all fields must be equal or null to match.
        -- some rows are exact duplicates. they should not be present in jkr.osapuoli.
        omistaja."omistajan nimi" is not distinct from osapuoli.nimi and
        omistaja."omistajan postiosoite" is not distinct from osapuoli.katuosoite and
        omistaja."postiosoitteen postitoimipaikka" is not distinct from osapuoli.postitoimipaikka and
        omistaja."postios posti_numero" is not distinct from osapuoli.postinumero and
        osapuoli.tiedontuottaja_tunnus = 'dvv'
        LIMIT 1
    ) as osapuoli_id,
    to_date(omistaja."omistuksen alkupäivä"::text, 'YYYYMMDD') as omistuksen_alkupvm,
    true as found_in_dvv
from jkr_dvv.omistaja
where
    omistaja."henkilötunnus" is null and
    omistaja."y_tunnus" is null and
    exists (
        select 1 from jkr.rakennus where omistaja.rakennustunnus = rakennus.prt) -- not all buildings might be listed
on conflict (rakennus_id, osapuoli_id, omistuksen_alkupvm) do update
    set found_in_dvv = true;


select update_omistuksen_loppupvm(:'poimintapvm');
select update_osapuoli_with_ytunnus();
select update_osapuoli_with_henkilotunnus();


alter table jkr.osapuoli drop column rakennustunnus;
alter table jkr.rakennuksen_omistajat drop column found_in_dvv;


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
    jkr.osapuoli.henkilotunnus = excluded.henkilotunnus
    AND (
        jkr.osapuoli.katuosoite IS NULL OR jkr.osapuoli.katuosoite <> excluded.katuosoite
        AND jkr.osapuoli.postitoimipaikka IS NULL OR jkr.osapuoli.postitoimipaikka <> excluded.postitoimipaikka
        AND jkr.osapuoli.postinumero IS NULL OR jkr.osapuoli.postinumero <> excluded.postinumero
        AND jkr.osapuoli.kunta IS NULL OR jkr.osapuoli.kunta <> excluded.kunta
    );


-- Insert elders to jkr.rakennuksen_vanhimmat
-- Step 1. Some vanhimmat have no extra fields
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" = ' ' and
    vanhin."huo_neisto_numero" = '000' and
    vanhin."jako_kirjain" = ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, alkupvm)
where huoneistokirjain is null and huoneistonumero is null and jakokirjain is null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


-- Step 2. Some vanhimmat have one extra field
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" != ' ' and
    vanhin."huo_neisto_numero" = '000' and
    vanhin."jako_kirjain" = ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, huoneistokirjain, alkupvm)
where huoneistokirjain is not null and huoneistonumero is null and jakokirjain is null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


-- Some vanhimmat have one extra field
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" = ' ' and
    vanhin."huo_neisto_numero" != '000' and
    vanhin."jako_kirjain" = ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, huoneistonumero, alkupvm)
where huoneistokirjain is null and huoneistonumero is not null and jakokirjain is null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


-- Step 3. Some vanhimmat have two extra fields
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" != ' ' and
    vanhin."huo_neisto_numero" != '000' and
    vanhin."jako_kirjain" = ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, alkupvm)
where huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


-- Some vanhimmat have two extra fields
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" = ' ' and
    vanhin."huo_neisto_numero" != '000' and
    vanhin."jako_kirjain" != ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, huoneistonumero, jakokirjain, alkupvm)
where huoneistokirjain is null and huoneistonumero is not null and jakokirjain is not null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


-- Step 4. Some vanhimmat have all fields
insert into jkr.rakennuksen_vanhimmat (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm, loppupvm, found_in_dvv)
select
    (select id from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) as rakennus_id,
    (select id from jkr.osapuoli where vanhin."huoneiston vanhin asukas (henkilötunnus)" = osapuoli.henkilotunnus and osapuoli.tiedontuottaja_tunnus = 'dvv') as osapuoli_id,
    nullif(vanhin."huo_neisto_kirjain", ' ') as huoneistokirjain,
    nullif(vanhin."huo_neisto_numero", '000')::integer as huoneistonumero,
    nullif(vanhin."jako_kirjain", ' ') as jakokirjain,
    to_date(vanhin."vakin kotim osoitteen alkupäivä"::text, 'YYYYMMDD') as alkupvm,
    null as loppupvm,
    true as found_in_dvv
from jkr_dvv.vanhin
where
    vanhin."huoneiston vanhin asukas (henkilötunnus)" is not null and
    vanhin."huo_neisto_kirjain" != ' ' and
    vanhin."huo_neisto_numero" != '000' and
    vanhin."jako_kirjain" != ' ' and
    exists (select 1 from jkr.rakennus where vanhin.rakennustunnus = rakennus.prt) -- not all buildings are listed
on conflict (rakennus_id, osapuoli_id, huoneistokirjain, huoneistonumero, jakokirjain, alkupvm)
where huoneistokirjain is not null and huoneistonumero is not null and jakokirjain is not null
do update set found_in_dvv = true
where jkr.rakennuksen_vanhimmat.osapuoli_id = excluded.osapuoli_id 
  and (
    (jkr.rakennuksen_vanhimmat.huoneistokirjain IS NULL and excluded.huoneistokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistokirjain = excluded.huoneistokirjain)
  )
  and (
    (jkr.rakennuksen_vanhimmat.huoneistonumero IS NULL and excluded.huoneistonumero IS NULL)
    or (jkr.rakennuksen_vanhimmat.huoneistonumero = excluded.huoneistonumero)
  )
  and (
    (jkr.rakennuksen_vanhimmat.jakokirjain IS NULL and excluded.jakokirjain IS NULL)
    or (jkr.rakennuksen_vanhimmat.jakokirjain = excluded.jakokirjain)
  )
  and jkr.rakennuksen_vanhimmat.rakennus_id = excluded.rakennus_id;


select update_vanhin_loppupvm(:'poimintapvm');
alter table jkr.rakennuksen_vanhimmat drop column found_in_dvv;
