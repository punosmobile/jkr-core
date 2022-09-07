alter table jkr.rakennus
alter column geom type geometry(point, 3067)
using st_transform(geom, 3067);

alter table jkr.kohde
alter column geom type geometry(polygon, 3067)
using st_transform(geom, 3067);
