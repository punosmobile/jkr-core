#!/usr/bin/env bash
# Builds the jkr-core image in Azure Container Registry (az acr build), so no
# local Docker is needed.
#
# Usage: deploy/build-image.sh <dev|test|prod> [tag] [context]
#   environment  selects the settings file deploy/deploy.<env>.env (registry and subscription)
#   tag          defaults to the short SHA of the current commit; prod also gets the version
#   context      defaults to the repo root
#
# The image is built from the files in the context, not from git, so the working
# tree must be clean for the image to match the commit. ALLOW_DIRTY=1 skips the
# check, but then the tag must be given explicitly. Existing tags are never overwritten.

# Run the script directly, do not source it (. or source): an exit on error would
# close the caller's terminal, and zsh cannot parse this file.
if [ -n "${ZSH_VERSION:-}" ] || { [ -n "${BASH_VERSION:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; }; then
  echo 'Aja skripti suoraan ilman pistettä tai sourcea, esim. deploy/build-image.sh dev' >&2
  return 1
fi

source "$(dirname "$0")/common.sh"

load_env "${1:-}"
TAG=${2:-}
CONTEXT=${3:-$(cd "$(dirname "$0")/.." && pwd)}
[ -f "$CONTEXT/Dockerfile" ] || fail "Dockerfile puuttuu kansiosta $CONTEXT"

if [ -n "$(git -C "$CONTEXT" status --porcelain 2>/dev/null)" ]; then
  [ "${ALLOW_DIRTY:-0}" = 1 ] \
    || fail_tag 'Työhakemistossa on commitoimattomia muutoksia, joten image ei vastaisi commitia. Commitoi tai aja ALLOW_DIRTY=1 omalla testitagilla.'
  [ -n "$TAG" ] || fail_tag "ALLOW_DIRTY=1 vaatii oman testitagin, koska image ei vastaa commitia: ALLOW_DIRTY=1 deploy/build-image.sh $ENVIRONMENT <tagi>"
fi
[ -n "$TAG" ] || TAG=$(head_tag)

require_az

if azs acr repository show --name "$REGISTRY" --image "$IMAGE_NAME:$TAG" -o none 2>/dev/null; then
  fail_tag "Image $IMAGE_NAME:$TAG on jo olemassa. Tageja ei ylikirjoiteta, joten anna uusi tagi."
fi

info "Rakennetaan $IMAGE_NAME:$TAG"
azs acr build \
  --registry "$REGISTRY" \
  --image "$IMAGE_NAME:$TAG" \
  --file Dockerfile \
  "$CONTEXT"
ok "Valmis: $IMAGE_NAME:$TAG"
