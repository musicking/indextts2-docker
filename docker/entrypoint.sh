#!/usr/bin/env bash
set -Eeuo pipefail

if (($#)); then
  exec "$@"
fi

webui_args=(
  /app/webui.py
  --version 2.5
  --host 0.0.0.0
  --port "${WEBUI_PORT:-7863}"
  --model_dir "${MODEL_DIR:-/app/checkpoints}"
)

# The upstream WebUI flag is named --fp16 for compatibility, but IndexTTS 2.5
# maps it to BF16 internally.
[[ "${USE_BF16:-1}" == "1" ]] && webui_args+=(--fp16)
[[ "${USE_CUDA_KERNEL:-0}" == "1" ]] && webui_args+=(--cuda_kernel)
[[ "${USE_TORCH_COMPILE:-0}" == "1" ]] && webui_args+=(--torch_compile)

exec uv run python "${webui_args[@]}"
