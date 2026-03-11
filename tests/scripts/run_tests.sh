#!/usr/bin/env bash
# run_tests.sh
# Nollaa testikanta ja ajaa testit kontainerissa.
#
# Kaytto:
#   ./tests/scripts/run_tests.sh            # Interaktiivinen valikko
#   ./tests/scripts/run_tests.sh --all      # Aja kaikki testit suoraan
#   ./tests/scripts/run_tests.sh --test test_kompostori  # Aja yksittainen testi
#
# Vaatimukset:
#   - Docker kaynnissa
#   - .env.local projektin juuressa (JKR_TEST_DB, JKR_TEST_DB_PORT, JKR_TEST_PASSWORD asetettu)

set -euo pipefail

# --- Varit ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# --- Polut ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.local"
COMPOSE_FILE="$PROJECT_ROOT/testing.docker-compose.yml"
TESTS_DIR="$PROJECT_ROOT/tests"

# --- Validoi .env.local ---
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}.env.local not found: $ENV_FILE${NC}"
    exit 1
fi

# --- Lue .env.local ---
declare -A ENV_VARS
while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*([^#][^=]*)[[:space:]]*=[[:space:]]*(.*)[[:space:]]*$ ]]; then
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]}"
        # Trim whitespace
        key="$(echo "$key" | xargs)"
        val="$(echo "$val" | xargs)"
        ENV_VARS["$key"]="$val"
    fi
done < "$ENV_FILE"

for var in JKR_TEST_DB JKR_TEST_DB_PORT JKR_TEST_PASSWORD JKR_USER; do
    if [ -z "${ENV_VARS[$var]:-}" ]; then
        echo -e "${RED}Variable $var missing or empty in .env.local${NC}"
        exit 1
    fi
done

TEST_DB="${ENV_VARS[JKR_TEST_DB]}"
TEST_PORT="${ENV_VARS[JKR_TEST_DB_PORT]}"

# --- Hae testitiedostot ---
mapfile -t TEST_FILES < <(find "$TESTS_DIR" -maxdepth 1 -name 'test_*.py' -printf '%f\n' | sed 's/\.py$//' | sort)

# --- Parsitaan argumentit ---
PYTEST_TARGET=""
RUN_LABEL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            PYTEST_TARGET="tests/"
            RUN_LABEL="Kaikki testit"
            shift
            ;;
        --test)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}--test vaatii testin nimen${NC}"
                exit 1
            fi
            TEST_NAME="$2"
            [[ "$TEST_NAME" != test_* ]] && TEST_NAME="test_$TEST_NAME"
            # Tarkista loytyykoo
            found=0
            for tf in "${TEST_FILES[@]}"; do
                if [ "$tf" = "$TEST_NAME" ]; then
                    found=1
                    break
                fi
            done
            if [ "$found" -eq 0 ]; then
                echo ""
                echo -e "${RED}Testitiedostoa '${TEST_NAME}.py' ei loydy.${NC}"
                echo ""
                echo -e "${YELLOW}Saatavilla olevat testit:${NC}"
                for tf in "${TEST_FILES[@]}"; do
                    echo "  $tf"
                done
                exit 1
            fi
            PYTEST_TARGET="tests/${TEST_NAME}.py"
            RUN_LABEL="$TEST_NAME"
            shift 2
            ;;
        *)
            echo -e "${RED}Tuntematon argumentti: $1${NC}"
            echo "Kaytto: $0 [--all | --test <nimi>]"
            exit 1
            ;;
    esac
done

# --- Interaktiivinen valikko jos ei argumentteja ---
if [ -z "$PYTEST_TARGET" ]; then
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  JKR Testivalikko${NC}"
    echo -e "${CYAN}  Kanta : $TEST_DB (portti $TEST_PORT)${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo "  0) Kaikki testit"

    for i in "${!TEST_FILES[@]}"; do
        num=$((i + 1))
        echo "  ${num}) ${TEST_FILES[$i]}"
    done

    echo ""
    read -rp "Valitse testi [0 = kaikki] (oletus: 0): " CHOICE
    CHOICE="${CHOICE:-0}"

    if [ "$CHOICE" = "0" ]; then
        PYTEST_TARGET="tests/"
        RUN_LABEL="Kaikki testit"
    elif [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
        idx=$((CHOICE - 1))
        if [ "$idx" -lt 0 ] || [ "$idx" -ge "${#TEST_FILES[@]}" ]; then
            echo -e "${RED}Virheellinen valinta: $CHOICE${NC}"
            exit 1
        fi
        PYTEST_TARGET="tests/${TEST_FILES[$idx]}.py"
        RUN_LABEL="${TEST_FILES[$idx]}"
    else
        echo -e "${RED}Virheellinen valinta: $CHOICE${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  JKR Testit kontainerissa${NC}"
echo -e "${CYAN}  Kanta : $TEST_DB (portti $TEST_PORT)${NC}"
echo -e "${CYAN}  Kohde : $RUN_LABEL${NC}"
echo -e "${CYAN}========================================${NC}"

# ============================================================
# [1/2] Nollaa testikanta
# ============================================================
echo ""
echo -e "${YELLOW}[1/2] Nollataan testikanta...${NC}"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v 2>/dev/null || true

echo -e "${GRAY}      Vanha kanta poistettu.${NC}"

# ============================================================
# [2/2] Aja testit kontainerissa
# ============================================================
echo ""
echo -e "${YELLOW}[2/2] Kaynnistetaan testikanta, ajetaan migraatiot ja testit...${NC}"
echo -e "${GRAY}      (Docker Compose: db_test -> flyway_test -> pytest)${NC}"
echo ""

PYTEST_CMD="cd /app && poetry install --no-root -q && poetry run python -m pytest $PYTEST_TARGET -v"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm jkr-core-runner bash -c "$PYTEST_CMD"
TEST_EXIT_CODE=$?

# --- Yhteenveto ---
echo ""
echo -e "${CYAN}========================================${NC}"
if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}  $RUN_LABEL - OK!${NC}"
else
    echo -e "${RED}  $RUN_LABEL - FAILED (exit code $TEST_EXIT_CODE)${NC}"
fi
echo -e "${CYAN}========================================${NC}"
echo -e "${GRAY}  Testikanta pyorii taustalla (sammuta: docker stop jkr_test_database)${NC}"

exit $TEST_EXIT_CODE
