# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.8.14@sha256:f3660c56d5b08d6c516360981bedc439f499b9bf37f46a216018da3777a74011 AS uv

FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04@sha256:ad6d59a3bbf3e82c1c849c9ac09cfc2a3e0bbb8655042fd899be6681b3fe2a85

ARG MODEL_REPO=IndexTeam/IndexTTS-2
ARG MODEL_REVISION=740dcaff396282ffb241903d150ac011cd4b1ede
ARG UPSTREAM_REVISION=b5bd6579e3b18fb80812e4c16ace452c79b05c9a

LABEL org.opencontainers.image.source="https://github.com/musicking/indextts2-docker" \
      org.opencontainers.image.url="https://github.com/index-tts/index-tts" \
      org.opencontainers.image.revision="${UPSTREAM_REVISION}"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=3.10 \
    HF_HOME=/root/.cache/huggingface \
    MODEL_DIR=/app/checkpoints \
    OUTPUT_DIR=/app/outputs

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ffmpeg libsndfile1 python3 python3-dev python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version README.md LICENSE MANIFEST.in ./
RUN uv sync --frozen --no-dev --extra webui --no-install-project

COPY . /app
RUN uv sync --frozen --no-dev --extra webui \
    && uv pip install --requirement docker/requirements.txt

# Download the official checkpoint and every auxiliary model at explicit
# revisions, so startup never silently resolves a newer set of weights.
RUN uv run python docker/download_models.py \
      --model-repo "${MODEL_REPO}" \
      --model-revision "${MODEL_REVISION}" \
      --model-dir checkpoints \
    && rm -rf /root/.cache/huggingface checkpoints/.cache

RUN mkdir -p /app/outputs/speakers \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 7860 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
  CMD curl -fsS http://127.0.0.1:8002/health || curl -fsS http://127.0.0.1:7860/ >/dev/null || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
