alter table jkr.kiinteisto
alter column geom type geometry(multipolygon, 3067)
using st_transform(st_multi(geom), 3067);

alter table jkr.taajama
alter column geom type geometry(multipolygon, 3067)
using st_transform(st_multi(geom), 3067);

alter table jkr.pohjavesialue
alter column geom type geometry(multipolygon, 3067)
using st_transform(st_multi(geom), 3067);

alter table jkr.jatteenkuljetusalue
alter column geom type geometry(multipolygon, 3067)
using st_transform(st_multi(geom), 3067);
