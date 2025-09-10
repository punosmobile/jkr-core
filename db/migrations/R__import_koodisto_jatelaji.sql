insert into jkr_koodistot.jatetyyppi(id, selite) values
    (1,'Biojäte'),
    (2,'Sekajäte'),
    (3,'Kartonki'),
    (4,'Lasi'),
    (5,'Liete'),
    (6,'Mustaliete'),
    (7,'Harmaaliete'),
    (8,'Metalli'),
    (9,'Muovi'),
    (10,'Pahvi'),
    (11,'Paperi'),
    (12,'Perusmaksu'),
    (13,'Energia'),
    (14,'AKP'),
    (99,'Muu')
on conflict do nothing;
