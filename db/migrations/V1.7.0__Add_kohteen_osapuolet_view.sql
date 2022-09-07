create view jkr.v_kohteen_osapuolet as
select
  ko.kohde_id,
  ko.osapuolenrooli_id,
  op.*
from
  jkr.kohteen_osapuolet ko
  join jkr.osapuoli op
    ON op.id = ko.osapuoli_id
;
