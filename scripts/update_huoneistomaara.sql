UPDATE jkr.rakennus
SET huoneistomaara = huoneistomaara.i_huoneistojen_lkm
FROM jkr_dvv.huoneistomaara
WHERE rakennus.prt = huoneistomaara.c_vtj_prt;
