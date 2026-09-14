# syntax=docker/dockerfile:1.7

ARG AUDIOCPP_REVISION=3eccab50bbdd757126f779687805e7164757eebc
FROM nvidia/cuda:12.9.2-devel-ubuntu24.04 AS build
ARG AUDIOCPP_REVISION
RUN apt-get update && apt-get install -y --no-install-recommends git gcc-14 g++-14 cmake ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV CC=gcc-14 CXX=g++-14 CUDAHOSTCXX=g++-14
WORKDIR /src
RUN git init . && git remote add origin https://github.com/0xShug0/audio.cpp.git \
    && git fetch --depth 1 origin "${AUDIOCPP_REVISION}" && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${AUDIOCPP_REVISION}"
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DAUDIOCPP_MODEL_SET=custom \
    -DAUDIOCPP_MODELS="index_tts2;voxcpm2;qwen3_asr;qwen3_forced_aligner" \
    -DENGINE_ENABLE_CPU_ALL_VARIANTS=ON -DENGINE_ENABLE_CUDA=ON -DENGINE_ENABLE_CUDA_GRAPHS=ON \
    -DENGINE_ENABLE_VULKAN=OFF -DENGINE_ENABLE_OPENMP=ON \
    -DENGINE_BUILD_EXAMPLES=OFF -DENGINE_BUILD_TESTS=OFF -DENGINE_BUILD_WARMBENCH=OFF \
    -DAUDIOCPP_VERSION="git-${AUDIOCPP_REVISION}" -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined \
    && cmake --build build --parallel 2 --target audiocpp_server audiocpp_cli \
    && mkdir -p /out && cp build/bin/audiocpp_server build/bin/audiocpp_cli /out/ \
    && find build -name '*.so*' -exec cp -P {} /out/ \;

FROM nvidia/cuda:12.9.2-runtime-ubuntu24.04
ARG AUDIOCPP_REVISION
ARG MODEL_REVISION=6d5436fc85f7a20c2e9f4e472b7f3a532f686444
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV LD_LIBRARY_PATH=/app:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
COPY --from=build /out/ /app/
COPY --from=build /src/model_specs/ /app/model_specs/
COPY --from=build /src/LICENSE /licenses/audio.cpp-LICENSE
RUN cp /usr/share/common-licenses/Apache-2.0 /licenses/Apache-2.0
ADD https://huggingface.co/IndexTeam/IndexTTS-2.5/resolve/c39ce5ba981572cb187443877ff559dfb246ce63/LICENSE /licenses/IndexTTS-LICENSE
ADD https://huggingface.co/OpenBMB/VoxCPM2/resolve/32279effe8c19989596f05d353d1447f51d9e915/README.md /licenses/VoxCPM2-model-card.md
ADD https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf/resolve/bcd2b5b7f32b480ab5790554cfa8347f246a14f3/README.md /licenses/Qwen3-ASR-model-card.md
ADD https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/c7cbfc2048c462b0d63a45797104fc9db3ad62b7/README.md /licenses/Qwen3-ForcedAligner-model-card.md
RUN chmod -R a+rX /licenses

LABEL org.opencontainers.image.source="https://github.com/musicking/indextts2-docker" \
      org.opencontainers.image.url="https://github.com/0xShug0/audio.cpp" \
      org.opencontainers.image.title="IndexTTS 2.5 audio.cpp API" \
      org.opencontainers.image.description="Source-built CUDA API with IndexTTS 2.5, VoxCPM2, Qwen3-ASR 1.7B and ForcedAligner bundled" \
      org.opencontainers.image.revision="${AUDIOCPP_REVISION}" \
      ai.indextts.model.revision="${MODEL_REVISION}" \
      ai.indextts.model.precision="f16"

USER 0:0

RUN mkdir -p /models/IndexTTS2.5 /voices \
    && chown -R 1000:1000 /models /voices

ADD --checksum=sha256:87bed9b82fc8f22119a1a1042332091016c28e37f29b0e93343ccdbfa76ef66a --chown=1000:1000 \
  "https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/${MODEL_REVISION}/IndexTTS2.5-GGUF/index-tts2_5-f16.gguf?download=true" \
  /models/IndexTTS2.5/index-tts2_5-f16.gguf

ADD --checksum=sha256:c8e01ab4416011e12a28f24ede298a1aa5ce64b43f8e8aaad53b1e2fe7c96432 --chown=1000:1000 \
  "https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/${MODEL_REVISION}/VoxCPM2-GGUF/voxcpm2-q8_0.gguf?download=true" \
  /models/VoxCPM2/voxcpm2-q8_0.gguf
ADD --checksum=sha256:da4fc2ac7f24dee784d1684eb1f35836cdbf559519452ae11777670734c0a4f8 --chown=1000:1000 \
  "https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/${MODEL_REVISION}/Qwen3-ASR-1.7B-GGUF/qwen3-asr-1.7b-q8_0.gguf?download=true" \
  /models/Qwen3-ASR-1.7B/qwen3-asr-1.7b-q8_0.gguf
ADD --checksum=sha256:75209490b11cec2b0db749ca5f4ff92266f58efd30f7fd04d9eb2a3ac9cc929f --chown=1000:1000 \
  "https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/${MODEL_REVISION}/Qwen3-ForcedAligner-0.6B-GGUF/qwen3-forced-aligner-0.6b-q8_0.gguf?download=true" \
  /models/Qwen3-ForcedAligner/qwen3-forced-aligner-0.6b-q8_0.gguf

COPY --chown=1000:1000 docker/audio-cpp/server.json /etc/indextts/server.json
COPY --chown=1000:1000 docker/audio-cpp/entrypoint.sh /app/indextts-entrypoint.sh

RUN chmod 0555 /app/indextts-entrypoint.sh

USER 1000:1000

EXPOSE 7864

HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=3 \
  CMD ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:7864/health"]

ENTRYPOINT ["/app/indextts-entrypoint.sh"]
