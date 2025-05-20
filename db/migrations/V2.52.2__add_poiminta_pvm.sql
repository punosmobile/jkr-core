CREATE SEQUENCE IF NOT EXISTS jkr.dvv_poimintapvm_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;


GRANT ALL ON SEQUENCE jkr.dvv_poimintapvm_id_seq TO jkr_admin;

GRANT USAGE ON SEQUENCE jkr.dvv_poimintapvm_id_seq TO jkr_editor;


CREATE TABLE IF NOT EXISTS jkr.dvv_poimintapvm
(
    id integer NOT NULL DEFAULT nextval('jkr.dvv_poimintapvm_id_seq'::regclass),
    poimintapvm date NOT NULL
);

ALTER TABLE IF EXISTS jkr.dvv_poimintapvm
    OWNER to jkr_admin;

REVOKE ALL ON TABLE jkr.dvv_poimintapvm FROM jkr_editor;
REVOKE ALL ON TABLE jkr.dvv_poimintapvm FROM jkr_viewer;

GRANT ALL ON TABLE jkr.dvv_poimintapvm TO jkr_admin;

GRANT DELETE, INSERT, UPDATE ON TABLE jkr.dvv_poimintapvm TO jkr_editor;

GRANT SELECT ON TABLE jkr.dvv_poimintapvm TO jkr_viewer;

COMMENT ON TABLE jkr.dvv_poimintapvm
    IS 'dvv-aineiston poimintapäivien tallennus';

CREATE INDEX IF NOT EXISTS idx_dvv_poimintapvm_poimintapvm
    ON jkr.dvv_poimintapvm USING btree
    (poimintapvm DESC NULLS LAST)
    TABLESPACE pg_default;