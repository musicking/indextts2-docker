#!/usr/bin/env bash
set -Eeuo pipefail

if (($#)); then
  exec "$@"
fi

services="${INDEXTTS_SERVICES:-api,webui}"
pids=()

shutdown() {
  if ((${#pids[@]})); then
    kill -TERM "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
}
trap shutdown TERM INT EXIT

if [[ ",${services}," == *",api,"* ]]; then
  uv run gunicorn \
    --bind "0.0.0.0:${API_PORT:-8002}" \
    --workers 1 \
    --threads 1 \
    --timeout "${API_TIMEOUT:-600}" \
    --chdir /app/docker/app \
    "api_server:create_app()" &
  pids+=("$!")
fi

if [[ ",${services}," == *",webui,"* ]]; then
  webui_args=(
    /app/webui.py
    --host 0.0.0.0
    --port "${WEBUI_PORT:-7860}"
    --model_dir "${MODEL_DIR:-/app/checkpoints}"
  )
  [[ "${USE_FP16:-1}" == "1" ]] && webui_args+=(--fp16)
  [[ "${USE_CUDA_KERNEL:-1}" == "1" ]] && webui_args+=(--cuda_kernel)
  [[ "${USE_TORCH_COMPILE:-0}" == "1" ]] && webui_args+=(--torch_compile)
  uv run python "${webui_args[@]}" &
  pids+=("$!")
fi

if ((${#pids[@]} == 0)); then
  echo "INDEXTTS_SERVICES must contain api, webui, or both" >&2
  exit 64
fi

# Exit if either service fails; the trap terminates the remaining process.
wait -n "${pids[@]}"
