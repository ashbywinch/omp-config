#!/bin/bash
# Fetch one workflow run's logs from the REST endpoint and unpack them.
#
#   fetch-run-logs.sh <owner/repo> <run-id> [output-dir]
#
# The CLI (`gh run view <run-id> --log`) prints nothing for some runs — re-runs,
# and jobs that failed inside a step — while the endpoint serves the full logs.
set -eu -o pipefail

repo=${1:?usage: fetch-run-logs.sh <owner/repo> <run-id> [output-dir]}
run=${2:?usage: fetch-run-logs.sh <owner/repo> <run-id> [output-dir]}
out=${3:-logs}

curl -sL -H "Authorization: token $(gh auth token)" \
  "https://api.github.com/repos/$repo/actions/runs/$run/logs" -o "$out.zip"
unzip -o -q "$out.zip" -d "$out"
ls "$out"
