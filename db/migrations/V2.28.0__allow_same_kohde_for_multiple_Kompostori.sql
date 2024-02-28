-- Remove unique constraint for kompostorin_kohteet_kohde_id
-- This allows keeping old kompostori for velvoitetarkistus.
DROP INDEX IF EXISTS uidx_kompostorin_kohteet_kohde_id;