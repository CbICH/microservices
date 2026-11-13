#!/usr/bin/env sh
set -eu

BASE_URL=${BASE_URL:-http://127.0.0.1:8080}
REQUEST_PATH=${REQUEST_PATH:-/api/v1/entities/demo-1}
REQUESTS=${REQUESTS:-100}
PARALLELISM=${PARALLELISM:-5}

seq 1 "$REQUESTS" | xargs -P "$PARALLELISM" -I{} \
  curl --silent --show-error --insecure \
    -H "X-Request-ID: lab6-{}" \
    -o /dev/null \
    -w '%{http_code}\n' \
    "${BASE_URL}${REQUEST_PATH}" \
  | sort | uniq -c

