insert into jkr_koodistot.akppoistosyy(id, selite) values
    (1, 'Pihapiiri'),
    (2, 'Pitkä matka'),
    (11, 'Ei käytössä')
on conflict do nothing;