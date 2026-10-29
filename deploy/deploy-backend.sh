#!/usr/bin/env bash
# Deploys the backend Container App (building the images of the commit first if
# they do not exist yet) and waits until the new revision is healthy. The migration image with the same tag runs as an init
# container before the backend starts, so migrations are part of the deploy; a
# failed migration stops the revision. Old revisions are deactivated only after
# the new one is healthy, so on a failed deploy the old version keeps running,
# and the Container App is set back to the previous template so the failed
# deploy cannot complete later on its own.
#
# Usage: deploy/deploy-backend.sh <dev|test|prod> [tag]
#   tag        defaults to the short SHA of the current commit. Then the deploy
#              only runs from the environment's own branch (develop, test, main),
#              and the image is built first if it does not exist yet. An explicit
#              tag (e.g. rollback to v0.8.0) skips the branch check, but the image
#              must already exist. A tag from before the migration image (e.g.
#              v0.8.0) deploys without changing the init container.
#   TIMEOUT_S  wait time in seconds (default 600)
#
# The script creates no resources and does not write to Key Vault; the Azure service provider manages them.
# Output contains no addresses or identifiers, because pipeline logs are public.

# Run the script directly, do not source it (. or source): an exit on error would
# close the caller's terminal, and zsh cannot parse this file.
if [ -n "${ZSH_VERSION:-}" ] || { [ -n "${BASH_VERSION:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; }; then
  echo 'Aja skripti suoraan ilman pistettä tai sourcea, esim. deploy/deploy-backend.sh dev' >&2
  return 1
fi

source "$(dirname "$0")/common.sh"

load_env "${1:-}"
TAG=${2:-}
TIMEOUT_S=${TIMEOUT_S:-600}

if [ -z "$TAG" ]; then
  branch=$(current_branch)
  [ "$branch" = "$BRANCH" ] \
    || fail_tag "Ympäristöön $ENVIRONMENT julkaistaan ilman tagia vain haarasta $BRANCH (nyt: $branch). Vaihda haaraa tai anna tagi: deploy/deploy-backend.sh $ENVIRONMENT <tagi>"
  TAG=$(head_tag)
  ok "Tagi: $TAG (haaran $BRANCH nykyinen commit)"
fi

# Prod is normally deployed by the pipeline, where another developer approves.
# A manual prod deploy asks for confirmation so that it is never started by
# accident. It does not replace that approval.
if [ "$ENVIRONMENT" = prod ] && [ "${GITHUB_ACTIONS:-}" != true ]; then
  [ -t 0 ] || fail 'Tuotantojulkaisu käsin vaatii vahvistuksen terminaalissa.'
  printf '%sTuotantojulkaisu käsin: %s.%s Onko toinen kehittäjä hyväksynyt julkaisun? Kirjoita prod jatkaaksesi: ' \
    "$C_YELLOW" "$IMAGE_NAME:$TAG" "$C_OFF"
  read -r answer
  [ "$answer" = prod ] || fail 'Julkaisu peruttu.'
fi

require_az

command -v jq >/dev/null || fail 'jq puuttuu.'

exists() { azs acr repository show --name "$REGISTRY" --image "$1" -o none 2>/dev/null; }
MIGRATIONS="$REGISTRY.azurecr.io/$MIGRATIONS_IMAGE:$TAG"
if ! exists "$IMAGE_NAME:$TAG" || ! exists "$MIGRATIONS_IMAGE:$TAG"; then
  if [ -z "${2:-}" ]; then
    info "Imageja tagille $TAG ei vielä ole, rakennetaan ne ensin"
    ALLOW_DIRTY=0 "$(dirname "$0")/build-image.sh" "$ENVIRONMENT" "$TAG"
  else
    exists "$IMAGE_NAME:$TAG" \
      || fail_tag "Imagea $IMAGE_NAME:$TAG ei löydy rekisteristä. Rakenna se ensin (deploy/build-image.sh $ENVIRONMENT $TAG) tai valitse olemassa oleva tagi."
    warn "Migraatioimagea $MIGRATIONS_IMAGE:$TAG ei ole (tagi ennen migraatioputkea). Init container jää ennalleen."
    MIGRATIONS=''
  fi
fi
# The version tag is added only when the images are built in this run.
if [ -n "${VERSION_TAG:-}" ] && ! exists "$IMAGE_NAME:$VERSION_TAG"; then
  warn "Versiotagia $IMAGE_NAME:$VERSION_TAG ei ole, koska commitin imaget oli rakennettu jo aiemmin. Julkaisu jatkuu SHA-tagilla."
fi

IMAGE="$REGISTRY.azurecr.io/$IMAGE_NAME:$TAG"
deadline=$(( $(date +%s) + TIMEOUT_S ))

# Template of the revision that serves traffic now. A failed update stays in the
# Container App template, and Azure carries it out later on its own once the
# cause is fixed (seen 22.10.2026 when AcrPull was restored). So on failure the
# template is set back to this one. revisionSuffix must not be reused, and an
# empty init container list (not null) removes an init container in a PATCH.
APP_ID=$(azs containerapp show --name "$APP" --resource-group "$RG" --query id -o tsv)
ready_revision=$(azs containerapp show --name "$APP" --resource-group "$RG" --query properties.latestReadyRevisionName -o tsv)
if [ -n "$ready_revision" ]; then
  PREV_TEMPLATE=$(azs containerapp revision show --name "$APP" --resource-group "$RG" \
    --revision "$ready_revision" --query properties.template -o json | jq -c 'del(.revisionSuffix) | .initContainers //= []')
else
  PREV_TEMPLATE=$(azs containerapp show --name "$APP" --resource-group "$RG" --query properties.template -o json | jq -c 'del(.revisionSuffix) | .initContainers //= []')
fi
PREV_IMAGE=$(printf '%s' "$PREV_TEMPLATE" | jq -r '.containers[0].image')

# New template: the backend image, and the migration image as the init container
# with the backend's database settings (the same Key Vault secret references).
NEW_TEMPLATE=$(printf '%s' "$PREV_TEMPLATE" | jq -c --arg image "$IMAGE" --arg migrations "$MIGRATIONS" '
  .containers[0].image = $image
  | if $migrations == "" then . else
      .initContainers = [{
        name: "migrations",
        image: $migrations,
        env: [.containers[0].env[] | select(.name | test("^JKR_(DB_HOST|DB_PORT|DB|USER|PASSWORD)$"))],
        resources: {cpu: 0.5, memory: "1Gi"}
      }]
    end')

# PATCH only the template; configuration (secrets, ingress, registries) stays as is.
# Returns at once, like --no-wait, so the script polls the state itself. Same API
# version as Azure CLI, so the template it reads (e.g. scale settings) is accepted.
patch_template() {
  az rest --method patch --only-show-errors -o none \
    --url "https://management.azure.com$APP_ID?api-version=2025-07-01" \
    --body "$(printf '%s' "$1" | jq -c '{properties: {template: .}}')"
}

fail_and_restore() {
  printf '%sVIRHE:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2
  if [ "$PREV_TEMPLATE" != "$NEW_TEMPLATE" ]; then
    info "Palautetaan $APP edelliseen määrittelyyn (${PREV_IMAGE##*/})" >&2
    if patch_template "$PREV_TEMPLATE" 2>/dev/null; then
      printf '%sPALAUTETTU:%s Ajossa on edelleen edellinen versio %s. Julkaisua %s ei tehty, eikä se toteudu myöhemmin itsestään.\n' \
        "$C_YELLOW" "$C_OFF" "${PREV_IMAGE##*/}" "$IMAGE_NAME:$TAG" >&2
    else
      printf '%sPALAUTUS EPÄONNISTUI:%s Määrittelyssä on yhä %s, ja Azure voi julkaista sen myöhemmin itsestään. Palauta hetken kuluttua käsin: deploy/deploy-backend.sh %s %s\n' \
        "$C_RED" "$C_OFF" "$IMAGE_NAME:$TAG" "$ENVIRONMENT" "${PREV_IMAGE##*:}" >&2
    fi
  fi
  exit 1
}

info "Päivitetään $APP imageen $IMAGE_NAME:$TAG${MIGRATIONS:+ (migraatiot: $MIGRATIONS_IMAGE:$TAG)}"
# The script polls the state itself, so a dropped connection cannot abort a
# deploy that Azure is already carrying out. Running the script again with the
# same tag resumes from where it stopped.
patch_template "$NEW_TEMPLATE" \
  || fail "Azure hylkäsi päivityksen (yllä), joten mitään ei muutettu ja vanha versio jatkaa toimintaansa."

# The Container App update can fail without creating a revision, e.g. when the
# identity lacks AcrPull on the registry. The latest revision is then still the
# old, healthy one, so the update counts as done only when the app has succeeded
# and its latest revision runs the requested image. Failed queries are retried
# until the deadline.
info 'Odotetaan Container Appin päivityksen valmistumista'
while :; do
  read -r app_state REVISION <<< "$(azs containerapp show --name "$APP" --resource-group "$RG" \
    --query "join(' ', [properties.provisioningState || 'none', properties.latestRevisionName || 'none'])" -o tsv 2>/dev/null \
    || echo 'ei-yhteyttä none')"
  if [ "$app_state" = Failed ] || [ "$app_state" = Canceled ]; then
    fail_and_restore "Container Appin $APP päivitys epäonnistui ($app_state). Yleisin syy on puuttuva AcrPull-oikeus rekisteriin $REGISTRY. Tarkista: Activity log tai az containerapp logs show -n $APP -g $RG --type system"
  fi
  revision_image=''
  if [ "$app_state" = Succeeded ]; then
    revision_image=$(azs containerapp revision show --name "$APP" --resource-group "$RG" --revision "$REVISION" \
      --query "properties.template.containers[0].image" -o tsv 2>/dev/null || true)
    [ "$revision_image" = "$IMAGE" ] && break
  fi
  [ "$(date +%s)" -lt "$deadline" ] \
    || fail_and_restore "Container Appin $APP päivitys ei valmistunut $TIMEOUT_S sekunnissa (tila $app_state, uusin revisio $REVISION ${revision_image:+imagella ${revision_image##*/}})."
  ok "Tila: $app_state"
  sleep 15
done
ok "Revisio: $REVISION"

info "Odotetaan, että revisio on terve (enintään $TIMEOUT_S s)"
while :; do
  state=$(azs containerapp revision show --name "$APP" --resource-group "$RG" --revision "$REVISION" \
    --query "join(' ', [properties.provisioningState || 'none', properties.healthState || 'none', properties.runningState || 'none'])" -o tsv 2>/dev/null \
    || echo 'ei-yhteyttä none none')
  read -r provisioning health running <<< "$state"
  ok "$provisioning / $health / $running"

  if [ "$provisioning" = Provisioned ] && [ "$health" = Healthy ]; then
    break
  fi
  if [ "$provisioning" = Failed ] || [ "$running" = Failed ]; then
    fail_and_restore "Revisio $REVISION epäonnistui. Syy: az containerapp logs show -n $APP -g $RG --revision $REVISION --type system, migraatiot: deploy/migration-logs.sh $ENVIRONMENT"
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    fail_and_restore "Revisio $REVISION ei ollut terve $TIMEOUT_S sekunnissa. Jos migraatiot kaatuivat: deploy/migration-logs.sh $ENVIRONMENT"
  fi
  sleep 15
done

# The shared SQLite event store (/dbdumps/system) cannot handle two concurrent
# writers, so old revisions are shut down right away instead of at ACA's own pace.
info 'Deaktivoidaan vanhat revisiot'
for old in $(azs containerapp revision list --name "$APP" --resource-group "$RG" \
  --query "[?properties.active && name!='$REVISION'].name" -o tsv); do
  if azs containerapp revision deactivate --name "$APP" --resource-group "$RG" --revision "$old" -o none; then
    ok "Deaktivoitu: $old"
  else
    warn "Revision $old deaktivointi ei onnistunut."
  fi
done

success "Valmis: $ENVIRONMENT ajaa imagea $IMAGE_NAME:$TAG (revisio $REVISION)"
