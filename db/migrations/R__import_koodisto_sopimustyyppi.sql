insert into jkr_koodistot.sopimustyyppi(id, selite) values
    (1,'Tyhjennyssopimus'),
    (2,'Kimppasopimus'),
    (3,'Aluekeräyssopimus'),
    (4,'Putkikeräyssopimus')
on conflict do nothing;
