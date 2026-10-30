#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

for output_dir in \
  "$ROOT_DIR/grpc_service/generated" \
  "$ROOT_DIR/rest_facade/generated"
do
  mkdir -p "$output_dir"
  python -m grpc_tools.protoc \
    -I "$ROOT_DIR/proto" \
    --python_out="$output_dir" \
    --grpc_python_out="$output_dir" \
    "$ROOT_DIR/proto/domain.proto"
done

echo "Generated Python modules for both services."

