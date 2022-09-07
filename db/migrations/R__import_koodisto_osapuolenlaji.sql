insert into jkr_koodistot.osapuolenrooli(id, selite) values
    (1,'Asiakas'),
    (2,'Yhteystieto')
on conflict do nothing;
