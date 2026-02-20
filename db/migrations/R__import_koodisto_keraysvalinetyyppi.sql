insert into jkr_koodistot.keraysvalinetyyppi(id, selite) values
    (1, 'PINTA'),
    (2, 'SYVÄ'),
    (3, 'Saostussäiliö'),
    (4, 'Umpisäiliö'),
    (5, 'RULLAKKO'),
    (6, 'SÄILIÖ'),
    (7, 'Pienpuhdistamo'),
    (8, 'PIKAKONTTI'),
    (9, 'NOSTOKONTTI'),
    (10, 'VAIHTOLAVA'),
    (11, 'JÄTESÄKKI'),
    (12, 'PURISTINSÄILIÖ'),
    (13, 'PURISTIN'),
    (14, 'VAIHTOLAVASÄILIÖ'),
    (15, 'PAALI'),
    (16, 'MONILOKERO'),
    (99, 'Muu')
on conflict (id) do update set selite = EXCLUDED.selite;
