insert into jkr_koodistot.osapuolenrooli(id, selite) values
    (1,'Omistaja'),
    (2,'Vanhin asukas'),
    (3,'Asiakas')
on conflict (id) do update set selite = excluded.selite;
