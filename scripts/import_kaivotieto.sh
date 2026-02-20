#!/bin/bash

# Kaivotietojen tuonti
# Tuodaan ensin aloitustiedot, sitten lopetukset kvartaaleittain

echo "=== Kaivotietojen tuonti ==="
echo "Aloitusaika: $(date)"

# Kaivotietojen aloitus
echo ""
echo "--- Kaivotietojen aloitus ---"
jkr import_kaivotiedot ../data/Liete/Kaivotiedot_aloitus.xlsx LSJ

# Q1 2024 lopetukset
echo ""
echo "--- Q1 2024 kaivotiedon lopetukset ---"
jkr import_kaivotiedon_lopetukset ../data/Liete/Kaivotiedot_lopetus_2024Q1.xlsx LSJ

# Q2 2024 lopetukset
echo ""
echo "--- Q2 2024 kaivotiedon lopetukset ---"
jkr import_kaivotiedon_lopetukset ../data/Liete/Kaivotiedot_lopetus_2024Q2.xlsx LSJ

# Q3 2023 lopetukset (jos olemassa)
if [ -f "../data/Liete/Kaivotiedot_lopetus_2023Q2.xlsx" ]; then
    echo ""
    echo "--- Q2 2023 kaivotiedon lopetukset ---"
    jkr import_kaivotiedon_lopetukset ../data/Liete/Kaivotiedot_lopetus_2023Q2.xlsx LSJ
fi

if [ -f "../data/Liete/Kaivotiedot_lopetus_2023Q3.xlsx" ]; then
    echo ""
    echo "--- Q3 2023 kaivotiedon lopetukset ---"
    jkr import_kaivotiedon_lopetukset ../data/Liete/Kaivotiedot_lopetus_2023Q3.xlsx LSJ
fi

echo ""
echo "=== Kaivotietojen tuonti valmis ==="
echo "Lopetusaika: $(date)"
