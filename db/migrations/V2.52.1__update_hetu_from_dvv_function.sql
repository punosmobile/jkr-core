-- Matches and updates information (hetu) for osapuoli using first and last names as identifiers. 
create or replace function update_osapuoli_without_ytunnus_or_henkilotunnus() returns void as $$
declare
    rec jkr.osapuoli%rowtype;
begin
    for rec in select * from jkr.osapuoli where henkilotunnus is null and ytunnus is null
        and (nimi is null
        or postitoimipaikka is null
        or postinumero is null)
    loop
        update jkr.osapuoli
        set henkilotunnus = (
                select henkilotunnus from jkr.osapuoli
                where nimi = rec.nimi
                and nimi is not null and henkilotunnus is not null
                limit 1         
            )
        where
            henkilotunnus = rec.henkilotunnus;
    end loop;
   end;
$$ language plpgsql;