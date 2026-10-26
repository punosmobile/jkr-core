# shellcheck shell=bash disable=SC2034  # variables are used by the scripts that source this file
# Shared settings and helpers for the deploy scripts.
# Source from a script: source "$(dirname "$0")/common.sh"
# Must also work on macOS bash 3.2, so no associative arrays.

set -euo pipefail

# Resource names are not in the repo because it is public. load_env reads them.
LOCATION='westeurope'
IMAGE_NAME='jkr-core'

# Colours only on a terminal or in GitHub Actions (which renders them), never with NO_COLOR.
if [ -z "${NO_COLOR:-}" ] && { [ -t 2 ] || [ "${GITHUB_ACTIONS:-}" = true ]; }; then
  C_RED=$'\033[1;31m'; C_GREEN=$'\033[1;32m'; C_YELLOW=$'\033[1;33m'; C_BLUE=$'\033[1;34m'; C_OFF=$'\033[0m'
else
  C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_OFF=''
fi

info()    { printf '%s==>%s %s\n' "$C_BLUE" "$C_OFF" "$*"; }
ok()      { printf '    %s\n' "$*"; }
success() { printf '%s==> %s%s\n' "$C_GREEN" "$*" "$C_OFF"; }
warn()    { printf '    %sVAROITUS:%s %s\n' "$C_YELLOW" "$C_OFF" "$*" >&2; }
fail()    { printf '%sVIRHE:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }

# Tag errors always explain what the tag is supposed to contain.
fail_tag() {
  printf '%sVIRHE:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2
  cat >&2 <<EOF

Tagi on imagen tunniste rekisterissä. Käytä jotakin näistä:
  - commitin lyhyt SHA, esim. $(git -C "$(dirname "$0")/.." rev-parse --short HEAD 2>/dev/null || echo 1d1dd6b)
    (git rev-parse --short HEAD). Putki käyttää tätä, ja se on oletus ilman tagia.
  - versio tuotannossa ja palautuksissa, esim. v0.8.0
  - oma testitagi commitoimattomalle koodille, esim. testi-$(date +%Y%m%d%H%M)
Rekisterin uusimmat tagit:
  az acr repository show-tags -n $REGISTRY --repository $IMAGE_NAME --orderby time_desc --top 10 --subscription '$SUBSCRIPTION' -o tsv
EOF
  exit 1
}

# Every az call targets the subscription explicitly, so the user's default
# subscription neither affects the run nor gets changed.
azs() { az "$@" --subscription "$SUBSCRIPTION" --only-show-errors; }

require_az() {
  command -v az >/dev/null || fail 'Azure CLI (az) puuttuu.'
  # account show only reads the cache, so an expired login is caught only
  # by actually fetching a token.
  az account get-access-token --subscription "$SUBSCRIPTION" -o none 2>/dev/null \
    || fail "Ei voimassa olevaa kirjautumista subscriptioniin '$SUBSCRIPTION'. Aja: az login"
}

# Short SHA of the current commit. The same tag the pipeline uses.
head_tag() { git -C "$(dirname "$0")/.." rev-parse --short HEAD; }

# Current branch. GitHub Actions checks out a detached commit, so there the
# branch is read from an environment variable.
current_branch() { echo "${GITHUB_REF_NAME:-$(git -C "$(dirname "$0")/.." rev-parse --abbrev-ref HEAD)}"; }

# Per-environment resources. The ACR is shared by all and is found by name alone.
ENV_KEYS='SUBSCRIPTION REGISTRY RG APP'

# Reads the environment settings from deploy/deploy.<env>.env (template: deploy/deploy.example.env).
# In GitHub Actions there is no file; the same keys come from the environment's
# variables. Locally the file is required so that variables left in the shell
# from another environment are never used.
load_env() {
  ENVIRONMENT=${1:-}
  case "$ENVIRONMENT" in
    dev)  ENV_TAG='Development'; BRANCH='develop' ;;
    test) ENV_TAG='Test';        BRANCH='test' ;;
    prod) ENV_TAG='Production';  BRANCH='main' ;;
    *) fail "Tuntematon ympäristö '$ENVIRONMENT'. Käytä dev, test tai prod." ;;
  esac

  local file="${JKR_ENV_FILE:-$(dirname "$0")/deploy.$ENVIRONMENT.env}" key missing=''
  if [ -f "$file" ]; then
    # shellcheck source=/dev/null
    source "$file"
  elif [ "${GITHUB_ACTIONS:-}" != true ]; then
    fail "Asetustiedosto $file puuttuu. Kopioi deploy/deploy.example.env ja täytä arvot salasanahallinnasta."
  fi
  for key in $ENV_KEYS; do
    [ -n "${!key:-}" ] || missing="$missing $key"
  done
  [ -z "$missing" ] || fail "Ympäristön $ENVIRONMENT asetuksista puuttuu:$missing"
}
