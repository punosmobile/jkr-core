insert into jkr_koodistot.tapahtumalaji(koodi, selite) values
    ('1', 'Perusmaksu'),
    ('2', 'AKP'),
    ('3', 'Tyhjennysväli'),
    ('4', 'Keskeyttäminen'),
    ('5', 'Erilliskeräyksestä poikkeaminen'),
    ('100', 'Muu poikkeaminen')
on conflict do nothing;