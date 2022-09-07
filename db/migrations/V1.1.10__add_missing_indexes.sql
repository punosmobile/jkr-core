-- object: idx_rakennus_kiinteistotunnus | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_rakennus_kiinteistotunnus CASCADE;
CREATE INDEX idx_rakennus_kiinteistotunnus ON jkr.rakennus USING btree (kiinteistotunnus);

-- ddl-end --
-- object: idx_osapuoli_ytunnus | type: INDEX --
-- DROP INDEX IF EXISTS jkr.idx_osapuoli_ytunnus CASCADE;
CREATE INDEX idx_osapuoli_ytunnus ON jkr.osapuoli USING btree (ytunnus);

-- ddl-end --
-- [ Changed objects ] --
ALTER TABLE jkr.sopimus
  ALTER COLUMN sopimustyyppi_id SET NOT NULL;

