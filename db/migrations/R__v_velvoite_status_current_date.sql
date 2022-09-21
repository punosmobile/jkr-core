CREATE VIEW jkr.v_velvoite_status_current_date
AS

SELECT velvoite_status.velvoite_id,
    velvoite_status.pvm,
    velvoite_status.ok
   FROM jkr.velvoite_status(CURRENT_DATE) velvoite_status(velvoite_id, pvm, ok);
-- ddl-end --
ALTER VIEW jkr.v_velvoite_status_current_date OWNER TO jkr_admin;
-- ddl-end --
