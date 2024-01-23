insert into jkr_koodistot.paatostulos(koodi, selite) values
    ('0', 'kielteinen'),
    ('1', 'myönteinen')
on conflict do nothing;