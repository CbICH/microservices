#!/usr/bin/env sh
set -eu

BASE_URL=${BASE_URL:-http://localhost:8080}

attempt=0
until curl --fail --silent --show-error "$BASE_URL/health" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Gateway did not become ready: $BASE_URL" >&2
    exit 1
  fi
  sleep 1
done

curl --fail --silent --show-error \
  -H 'X-Request-ID: lab5-smoke-read' \
  "$BASE_URL/api/v1/entities/demo-1"
printf '\n'

curl --fail --silent --show-error \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: lab5-smoke-command' \
  -d '{"command":"publish"}' \
  "$BASE_URL/api/v1/entities/demo-1/state"
printf '\nSmoke test passed.\n'

