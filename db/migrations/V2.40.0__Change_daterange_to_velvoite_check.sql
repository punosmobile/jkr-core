DROP VIEW IF EXISTS jkr.v_velvoitteita_rikkovat;
DROP VIEW IF EXISTS jkr.v_velvoitteiden_kohteet; -- will be recreated in R__03_v_velvoitteita_rikkovat.sql


ALTER TABLE jkr.velvoite_status
DROP COLUMN pvm;
ALTER TABLE jkr.velvoite_status
ADD COLUMN jakso daterange NOT NULL;
COMMENT ON COLUMN jkr.velvoite_status.jakso
    IS 'Ajanjakso, jolla velvollisuuden täyttyminen on tarkistettu.';
CREATE UNIQUE INDEX uidx_velvoite_status_velvoite_id_jakso ON jkr.velvoite_status
USING btree
(
    velvoite_id,
    jakso
);


DROP VIEW IF EXISTS jkr.v_velvoite_status_current_date; -- a legacy view for checking status in the current date


DROP FUNCTION IF EXISTS jkr.velvoite_status; -- will be recreated in R__Add_velvoite_management_functions.sql
