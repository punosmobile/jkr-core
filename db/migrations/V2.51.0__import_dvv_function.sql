

create or replace function update_omistuksen_loppupvm(poimintapvm DATE) returns void as $$
begin
  update jkr.rakennuksen_omistajat as ro
  set omistuksen_loppupvm = 
    case
      -- Looks for existing entry and
      -- sets loppupvm to new entry's omistuksen_alkupvm - 1 day,
      -- if it is greater than the omistuksen_alkupvm
      -- of the entry being updated.
      -- If multiple existing entries are found
      -- picks the one with latest omistuksen_alkupvm
      when exists(
        select 1 
        from jkr.rakennuksen_omistajat as existing_entry
        where existing_entry.rakennus_id = ro.rakennus_id
        and existing_entry.omistuksen_alkupvm::date > ro.omistuksen_alkupvm::date
        and existing_entry.found_in_dvv = true
        order by omistuksen_alkupvm desc
        limit 1
      ) then 
        (select to_date((existing_entry.omistuksen_alkupvm::date - interval '1 DAY')::text, 'YYYY-MM-DD') 
         from jkr.rakennuksen_omistajat as existing_entry
         where existing_entry.rakennus_id = ro.rakennus_id
         and existing_entry.omistuksen_alkupvm::date > ro.omistuksen_alkupvm::date
         and existing_entry.found_in_dvv = TRUE
         order by omistuksen_alkupvm desc
         limit 1)
      else 
        poimintapvm -- if no applicable existing entry is found, use poimintapvm.
    end
  where found_in_dvv is not True
  and omistuksen_loppupvm is null;
end;
$$ language plpgsql;

create or replace function update_vanhin_loppupvm(poimintapvm DATE) returns void as $$
begin
  update jkr.rakennuksen_vanhimmat as rv
  set loppupvm = 
    case
      -- Looks for a new entry in the same appartment
      -- sets loppupvm to new entry's alkupvm - 1 day, if it is greater than the alkupvm
      -- of the entry being updated. 
      when exists(
        select 1
        from jkr.rakennuksen_vanhimmat as new_entry
        where new_entry.rakennus_id = rv.rakennus_id
          and new_entry.huoneistokirjain is not distinct from rv.huoneistokirjain
          and new_entry.huoneistonumero is not distinct from rv.huoneistonumero
          and new_entry.jakokirjain is not distinct from rv.jakokirjain
          and new_entry.alkupvm::date > rv.alkupvm::date
          and new_entry.found_in_dvv = True
          limit 1
      ) then (select (new_entry.alkupvm::date - interval '1 DAY')
        from jkr.rakennuksen_vanhimmat as new_entry
        where new_entry.rakennus_id = rv.rakennus_id
          and new_entry.huoneistokirjain is not distinct from rv.huoneistokirjain
          and new_entry.huoneistonumero is not distinct from rv.huoneistonumero
          and new_entry.jakokirjain is not distinct from rv.jakokirjain
          and new_entry.found_in_dvv = True
        limit 1)
      else
        -- if no applicable existing entry is found, use poimintapvm.
        poimintapvm 
    end
  where found_in_dvv is not True
  and loppupvm is null;
end;
$$ language plpgsql;

create or replace function update_kaytostapoisto_pvm(poimintapvm DATE) returns void as $$
begin
  update jkr.rakennus as r
  set kaytostapoisto_pvm = poimintapvm
  where found_in_dvv is not True
    and kaytostapoisto_pvm is null;
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