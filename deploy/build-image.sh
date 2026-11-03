#!/usr/bin/env bash
# Builds the jkr-core image and the migration image (db/Dockerfile) in Azure
# Container Registry (az acr build), so no local Docker is needed. Both get the
# same tag.
#
# Usage: deploy/build-image.sh <dev|test|prod> [tag] [context]
#   environment  selects the settings file deploy/deploy.<env>.env (registry and subscription)
#   tag          defaults to the short SHA of the current commit
#   context      defaults to the repo root
#   VERSION_TAG  optional second tag for the same image, e.g. v0.9.0 in prod. If it
#                already exists it is skipped with a warning (release without a version bump).
#
# The image is built from the files in the context, not from git, so the working
# tree must be clean for the image to match the commit. ALLOW_DIRTY=1 skips the
# check, but then the tag must be given explicitly. Existing tags are never
# overwritten: an image that already has the tag is skipped.

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

exists() { azs acr repository show --name "$REGISTRY" --image "$1" -o none 2>/dev/null; }

if exists "$IMAGE_NAME:$TAG" && exists "$MIGRATIONS_IMAGE:$TAG"; then
  fail_tag "Imaget $IMAGE_NAME:$TAG ja $MIGRATIONS_IMAGE:$TAG ovat jo olemassa. Tageja ei ylikirjoiteta, joten anna uusi tagi."
fi

build() { # image name, build context
  local name=$1 dir=$2 extra=''
  local image_args=(--image "$name:$TAG")
  if exists "$name:$TAG"; then
    ok "$name:$TAG on jo olemassa, ei rakenneta uudelleen"
    return
  fi
  if [ -n "${VERSION_TAG:-}" ]; then
    if exists "$name:$VERSION_TAG"; then
      warn "Versiotagi $name:$VERSION_TAG on jo olemassa, joten sitä ei lisätä. Versiota ei ole nostettu."
    else
      image_args+=(--image "$name:$VERSION_TAG")
      extra=" + $VERSION_TAG"
    fi
  fi
  info "Rakennetaan $name:$TAG$extra"
  # Run in the context directory: az acr build resolves --file from the current
  # directory, not from the context.
  (cd "$dir" && azs acr build --registry "$REGISTRY" "${image_args[@]}" --file Dockerfile .)
  ok "Valmis: $name:$TAG$extra"
}

build "$IMAGE_NAME" "$CONTEXT"
build "$MIGRATIONS_IMAGE" "$CONTEXT/db"
