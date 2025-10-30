-- Korjataan velvoitemallit 13-17 käyttämään v_biohapa_kohde viewiä
-- Biohapa-kohteet tarvitsevat biojätevelvoitteet riippumatta siitä ovatko ne erilliskeräysalueella

UPDATE jkr.velvoitemalli 
SET saanto = 'v_biohapa_kohde'
WHERE id IN (13, 14, 15, 16, 17);
