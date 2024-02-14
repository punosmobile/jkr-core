insert into jkr_koodistot.tapahtumalaji(koodi, selite) values
    ('PERUSMAKSU', 'Perusmaksu'),
    ('AKP', 'AKP'),
    ('TYHJENNYSVALI', 'Tyhjennysväli'),
    ('KESKEYTTAMINEN', 'Keskeyttäminen'),
    ('ERILLISKERAYKSESTA_POIKKEAMINEN', 'Erilliskeräyksestä poikkeaminen'),
    ('MUU', 'Muu poikkeaminen')
on conflict do nothing;