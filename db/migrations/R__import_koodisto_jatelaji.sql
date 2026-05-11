insert into jkr_koodistot.jatetyyppi(id, selite) values
    (1, 'Biojäte'),
    (2, 'Sekajäte'),
    (3, 'Kartonkipakkaus'),
    (4, 'Lasipakkaus'),
    (5, 'Liete'),
    (6, 'Musta liete'),
    (7, 'Harmaa liete'),
    (8, 'Metalli'),
    (9, 'Muovipakkaus'),
    (10, '10'),
    (11, '11'),
    (12, '12'),
    (13, '13'),
    (14, 'Aluekeräyspiste'),
    (15, 'Monilokero'),
    (99, 'Muu')
on conflict (id) do update set selite = EXCLUDED.selite;
