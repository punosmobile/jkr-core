#!/usr/bin/env bash
# Shows the output of the migration job's runs from Log Analytics, one row per
# line with the run (replica) name. A finished run's output is no longer
# available from the job itself.
#
# Usage: deploy/migration-logs.sh <dev|test|prod> [hours]
#   hours  how far back to look (default 24)
#
# For local use, not for the pipeline: database addresses in jdbc URLs are
# hidden, but Flyway's error messages can show the database host in other forms.

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
# Lines that arrive together share TimeGenerated; _timestamp_d keeps their order.
azs monitor log-analytics query --workspace "$workspace" -o tsv \
  --analytics-query "ContainerAppConsoleLogs_CL
    | where TimeGenerated > ago(${HOURS}h) and ContainerJobName_s == '$MIGRATION_JOB'
    | order by _timestamp_d asc" \
  --query "[].[TimeGenerated, ContainerGroupName_s, Log_s]" \
  | sed -E 's#jdbc:postgresql://[^ ]*#jdbc:postgresql://***#g'
