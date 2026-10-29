#!/usr/bin/env bash
# Shows the output of the migration init container from Log Analytics. The init
# container has finished by the time the backend runs, so az containerapp logs
# show cannot reach it.
#
# Usage: deploy/migration-logs.sh <dev|test|prod> [hours]
#   hours  how far back to look (default 24)
#
# Database addresses in Flyway's output are hidden, so the output is safe for
# public pipeline logs.

# Run the script directly, do not source it (. or source): an exit on error would
# close the caller's terminal, and zsh cannot parse this file.
if [ -n "${ZSH_VERSION:-}" ] || { [ -n "${BASH_VERSION:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; }; then
  echo 'Aja skripti suoraan ilman pistettä tai sourcea, esim. deploy/migration-logs.sh dev' >&2
  return 1
fi

source "$(dirname "$0")/common.sh"

load_env "${1:-}"
HOURS=${2:-24}
case "$HOURS" in
  ''|*[!0-9]*) fail "Tuntimäärän pitää olla kokonaisluku (nyt: $HOURS)." ;;
esac
require_az

# The workspace is found through the app, so no resource names are needed here.
aca_env=$(azs containerapp show --name "$APP" --resource-group "$RG" --query properties.managedEnvironmentId -o tsv)
workspace=$(azs containerapp env show --ids "$aca_env" \
  --query properties.appLogsConfiguration.logAnalyticsConfiguration.customerId -o tsv)
[ -n "$workspace" ] || fail "Container Apps -ympäristöllä ei ole Log Analytics -työtilaa."

info "Migraatioiden loki ($ENVIRONMENT, viimeiset $HOURS h)"
azs monitor log-analytics query --workspace "$workspace" -o tsv \
  --analytics-query "ContainerAppConsoleLogs_CL
    | where TimeGenerated > ago(${HOURS}h) and ContainerAppName_s == '$APP' and ContainerName_s == 'migrations'
    | order by TimeGenerated asc" \
  --query "[].[TimeGenerated, RevisionName_s, Log_s]" \
  | sed -E 's#jdbc:postgresql://[^ ]*#jdbc:postgresql://***#g'
