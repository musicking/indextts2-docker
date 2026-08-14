#!/usr/bin/env bash
set -Eeuo pipefail

if (($#)); then
  exec "$@"
fi

config="${AUDIOCPP_CONFIG:-/etc/indextts/server.json}"

if [[ ! -r "${config}" ]]; then
  echo "audio.cpp server config is not readable: ${config}" >&2
  exit 1
fi

exec /app/audiocpp_server --config "${config}"
