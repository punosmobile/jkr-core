insert into jkr_koodistot.rakennuksenolotila(koodi, selite) values
    ('01','käytetään vakinaiseen asumiseen'),
    ('02','toimitila- tai tuotantokäytössä'),
    ('03','käytetään loma-asumiseen'),
    ('04','käytetään muuhun tilapäiseen asumiseen'),
    ('05','tyhjillään (esim. myynnissä)'),
    ('06','purettu uudisrakentamisen vuoksi'),
    ('07','purettu muusta syystä'),
    ('08','tuhoutunut'),
    ('09','ränsistymien vuoksi hylätty'),
    ('10','käytöstä ei ole tietoa'),
    ('11','muu (sauna, liiteri, kellotapuli, ym.)')
on conflict do nothing;
