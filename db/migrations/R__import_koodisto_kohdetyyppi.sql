insert into jkr_koodistot.kohdetyyppi(id, selite) values
    (1,'aluekeräys'),
    (2,'lähikeräys'),
    (3,'putkikeräys'),
    (4,'kiinteistö')
on conflict do nothing;
