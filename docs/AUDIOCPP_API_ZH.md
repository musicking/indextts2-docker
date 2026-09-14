# IndexTTS 2.5 audio.cpp API 镜像

这套镜像从固定的最新 audio.cpp 源码编译原生 CUDA Server，内置四个 GGUF 模型。容器提供语音合成、识别和词级对齐 API，不启动 Gradio WebUI。API 分支为 `codex/audio-cpp-api`，不修改主线 WebUI。

## 镜像内容

- 镜像：`dockermaker0/indextts25-api:2.5.3`（发布成功后可拉取；旧版 `2.5.2` 保留）
- audio.cpp CUDA 12.9.2，从提交 `3eccab50bbdd757126f779687805e7164757eebc` 编译，仅启用需要的模型族及其依赖
- 全部 GGUF 固定到 Hugging Face 提交 `6d5436fc85f7a20c2e9f4e472b7f3a532f686444`，逐文件 SHA256 校验
- IndexTTS 2.5 F16：`indextts-2.5`
- VoxCPM2 Q8_0：`voxcpm2`
- Qwen3-ASR 1.7B Q8_0：`qwen3-asr-1.7b`
- Qwen3-ForcedAligner 0.6B Q8_0：`qwen3-forced-aligner-0.6b`
- API 端口：`7864`
- 模型 ID：`indextts-2.5`
- 健康检查：`GET /health`
- 模型列表：`GET /v1/models`
- 语音生成：`POST /v1/audio/speech`

该配置使用 F16 模型，并增加了说话人和情绪缓存槽位，目标是生产吞吐和重复请求性能，不以 8GB 显存为约束。当前运行时还包含 IndexTTS 2.5 调速、请求内 base64 参考音频、文本规范化修复、F16 权重执行优化，以及更完整的 CUDA GPU 架构支持。

## 启动

要求宿主机已经安装 NVIDIA 驱动、Docker 和 NVIDIA Container Toolkit。

```bash
docker compose -f docker-compose.audio-cpp.yml up -d
docker compose -f docker-compose.audio-cpp.yml logs -f
```

或者直接运行：

```bash
docker run -d \
  --name indextts25-api \
  --gpus all \
  --shm-size 1g \
  -p 7864:7864 \
  -v "$PWD/voices:/voices:ro" \
  --restart unless-stopped \
  dockermaker0/indextts25-api:latest
```

默认按需加载，启动后 `/health` 仅证明服务存活，不证明 CUDA 模型加载或推理成功。`/v1/models` 中 `loaded:false` 是正常状态，第一次使用对应模型时才加载。全部模型已在镜像中，启动时不下载。

部署升级：`docker compose -f docker-compose.audio-cpp.yml pull` 后执行 `up -d`。生产环境建议固定版本标签，不依赖滚动的 `latest`。

## VoxCPM2、ASR 与词级对齐

VoxCPM2 使用同一语音接口，参考文本必须与参考 WAV 内容一致：

```bash
curl http://127.0.0.1:7864/v1/audio/speech \
  -H 'Content-Type: application/json' -o voxcpm2.wav \
  -d '{"model":"voxcpm2","input":"你好，这是 VoxCPM2 测试。","voice_ref":"/voices/narrator.wav","reference_text":"这是用于克隆音色的参考音频文本。","response_format":"wav"}'
```

识别并返回词级时间戳（建议使用 16kHz WAV）：

```bash
curl http://127.0.0.1:7864/v1/audio/transcriptions/details \
  -F model=qwen3-asr-1.7b -F file=@input.wav
```

ASR 的 `session_options` 已关联内置 ForcedAligner，`default_request_options.return_timestamps` 为 `true`。普通 `/v1/audio/transcriptions` 只返回文本和 timing，不返回词数组；不要为了获取时间戳调用普通路由。details 的词时间可能是 sample offsets，应按响应 `sample_rate` 换算秒数。

已有准确文本时，直接调用独立对齐模型：

```bash
curl http://127.0.0.1:7864/v1/audio/alignments \
  -F model=qwen3-forced-aligner-0.6b -F language=Chinese \
  -F 'text=这是音频中实际说出的内容。' -F file=@input.wav
```

这不是 WhisperX，也不包含说话人分离。词对齐增加推理耗时和显存占用。ASR 辅助 aligner 与独立 aligner 是不同 session，不能假定共享显存。

## 准备音色

IndexTTS 2.5 是音色克隆模型。把参考音频放在宿主机的 `voices` 目录，例如：

```text
voices/
├── narrator.wav
└── prompt_text
```

`prompt_text` 每行使用 `<音频文件名（不含扩展名）>|<参考音频文本>`：

```text
narrator|这是用于克隆音色的参考音频文本。
```

请求中的 `voice` 填写 `narrator`，Server 会读取 `/voices/narrator.wav` 和对应的参考文本。

## 调用 API

检查服务：

```bash
curl http://127.0.0.1:7864/health
curl http://127.0.0.1:7864/v1/models
```

生成语音：

```bash
curl http://127.0.0.1:7864/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -o output.wav \
  -d '{
    "model": "indextts-2.5",
    "input": "你好，这是 IndexTTS 2.5 的生产 API 测试。",
    "voice": "narrator",
    "response_format": "wav",
    "seed": 1234
  }'
```

也可以直接传容器内的参考音频路径：

```json
{
  "model": "indextts-2.5",
  "input": "需要合成的文字",
  "voice_ref": "/voices/narrator.wav",
  "reference_text": "这是用于克隆音色的参考音频文本。"
}
```

情绪控制等 audio.cpp 扩展参数可直接放在请求 JSON 中，例如 `emotion_alpha`、`emotion_vector`、`use_emotion_text`、`emotion_text`、`temperature`、`top_k`、`top_p` 和 `num_beams`。

### 调整语速

`duration_factor` 是输出时长倍率，必须是正数：大于 `1` 会减慢语速，小于 `1` 会加快语速，`1.0` 为默认速度。它不是 OpenAI 请求体顶层的 `speed` 字段，必须放在 `options` 对象中：

```bash
curl http://127.0.0.1:7864/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -o slower.wav \
  -d '{
    "model": "indextts-2.5",
    "input": "这段语音使用较慢的速度生成。",
    "voice": "narrator",
    "options": {
      "duration_factor": 1.25
    }
  }'
```

例如 `0.8` 会加快，`1.25` 会减慢。它通过改变 S2Mel 目标帧长度实现调速，不是对生成后的 WAV 做变速处理。audio.cpp 目前只校验该值大于 `0`；生产网关建议把客户端输入限制在 `0.5`～`2.0`，避免极端值显著增加延迟、内存占用或损害可懂度。

### 请求内发送参考音频

客户端不方便挂载共享目录时，可以直接发送不超过 5MiB 的 base64 WAV。`data:` URI 和纯 base64 字符串都支持：

```json
{
  "model": "indextts-2.5",
  "input": "使用请求中上传的参考音频克隆音色。",
  "voice_ref": {
    "type": "base64",
    "data": "UklGRh..."
  },
  "reference_text": "参考音频中实际说出的文本。",
  "options": {
    "duration_factor": 1.0
  }
}
```

## 生产注意事项

- audio.cpp 对同一个模型串行执行推理；超过等待上限的新请求返回 HTTP 503。需要在上游设置有界队列和重试策略。
- 服务本身没有鉴权。不要直接暴露到公网，应放在 Nginx、Caddy 或 API Gateway 后面实现 HTTPS、鉴权、限流和请求审计。
- 当前 IndexTTS 2.5 是离线生成，不支持流式语音输出。
- 默认设置 `lazy_load:true`、`max_loaded_models:1`，最多一个顶层模型驻留，切换时 LRU 卸载空闲模型；正在推理的模型不会被驱逐，全部驻留模型繁忙时可能返回 503。ASR 内部辅助 aligner 不计作另一个顶层模型，但会增加实际内存。显存充足时可挂载配置提高驻留上限，避免频繁切换；不以 8GB 显存为约束。
- 持续并发 ASR/TTS 建议部署独立容器与 GPU/队列隔离。模型权重约 11.1GB（十进制），镜像还包含 CUDA 运行时。
- VoxCPM2、Qwen3-ASR 和 ForcedAligner 原始模型标注 Apache-2.0；IndexTTS 权重仍遵循其原始模型许可。转换仓库及运行时许可不替代模型许可，使用者须遵守通知、归属和原模型条款。
- `server.json` 默认不记录请求正文，避免文本和本地文件路径进入日志。
- 如需修改设备、线程数、缓存或端口，可以挂载完整配置并设置 `AUDIOCPP_CONFIG`：

```bash
docker run --gpus all \
  -p 9000:9000 \
  -e AUDIOCPP_CONFIG=/config/server.json \
  -v "$PWD/server.json:/config/server.json:ro" \
  -v "$PWD/voices:/voices:ro" \
  dockermaker0/indextts25-api:latest
```

## 本地构建

构建过程会从固定提交编译 CUDA，并下载约 11.1GB 的 GGUF 权重，需要充足磁盘、内存和较长编译时间：

```bash
docker build \
  -f docker/audio-cpp/Dockerfile \
  -t dockermaker0/indextts25-api:local \
  .
```

audio.cpp 源码与权重固定提交，权重固定 SHA256；CUDA 基础镜像固定版本标签（非 digest），系统依赖来自 apt，不能声称整个构建逐字节可重现。

GitHub 发布流程先构建并加载镜像，验证服务启动及四个模型登记，再发布。托管 runner 没有 NVIDIA GPU，这些检查不替代实际 CUDA 推理验收。生产上线前需测试两种 TTS、ASR words 非空、独立对齐、模型切换及忙碌时 503。
