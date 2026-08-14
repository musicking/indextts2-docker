# syntax=docker/dockerfile:1.7

# The dated tag and OCI digest make the native runtime reproducible. This
# revision contains audio.cpp release-0.6 plus the IndexTTS 2.5 fixes available
# on 2026-08-14.
ARG AUDIOCPP_IMAGE=ghcr.io/0xshug0/audio.cpp:full-cuda12-20260814-04ba437@sha256:73355831b1a31bc417778c7ff922bd80dd12f5ae07b8e9cbbd800a66a3290ea8

FROM ${AUDIOCPP_IMAGE}

ARG AUDIOCPP_REVISION=04ba4375ed53bbd718bd2697e190007f6a19f426
ARG MODEL_REVISION=597048d9a920592808d7d4e2acd7b9c4596a143a

LABEL org.opencontainers.image.source="https://github.com/musicking/indextts2-docker" \
      org.opencontainers.image.url="https://github.com/0xShug0/audio.cpp" \
      org.opencontainers.image.title="IndexTTS 2.5 audio.cpp API" \
      org.opencontainers.image.description="CUDA 12 audio.cpp API server with the IndexTTS 2.5 F16 GGUF model bundled" \
      org.opencontainers.image.revision="${AUDIOCPP_REVISION}" \
      ai.indextts.model.revision="${MODEL_REVISION}" \
      ai.indextts.model.precision="f16"

USER 0:0

RUN mkdir -p /models/IndexTTS2.5 /voices \
    && chown -R 1000:1000 /models /voices

ADD --checksum=sha256:87bed9b82fc8f22119a1a1042332091016c28e37f29b0e93343ccdbfa76ef66a --chown=1000:1000 \
  "https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/597048d9a920592808d7d4e2acd7b9c4596a143a/IndexTTS2.5-GGUF/index-tts2_5-f16.gguf?download=true" \
  /models/IndexTTS2.5/index-tts2_5-f16.gguf

COPY --chown=1000:1000 docker/audio-cpp/server.json /etc/indextts/server.json
COPY --chown=1000:1000 docker/audio-cpp/entrypoint.sh /app/indextts-entrypoint.sh

RUN chmod 0555 /app/indextts-entrypoint.sh

USER 1000:1000

EXPOSE 7863

HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=3 \
  CMD ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:7863/health"]

ENTRYPOINT ["/app/indextts-entrypoint.sh"]
