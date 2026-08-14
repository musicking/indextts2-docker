# IndexTTS 2.5 audio.cpp API 镜像

这套镜像使用 audio.cpp 原生 CUDA Server 和 IndexTTS 2.5 F16 GGUF 模型，模型已经固化在镜像中。容器启动后提供 OpenAI 风格的语音接口，不启动 Gradio WebUI。

## 镜像内容

- audio.cpp CUDA 12，固定到提交 `04ba4375ed53bbd718bd2697e190007f6a19f426`
- IndexTTS 2.5 F16 GGUF，固定到 Hugging Face 提交 `597048d9a920592808d7d4e2acd7b9c4596a143a`
- API 端口：`7863`
- 模型 ID：`indextts-2.5`
- 健康检查：`GET /health`
- 模型列表：`GET /v1/models`
- 语音生成：`POST /v1/audio/speech`

该配置使用 F16 模型，并增加了说话人和情绪缓存槽位，目标是生产吞吐和重复请求性能，不以 8GB 显存为约束。

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
  --shm-size 8g \
  -p 7863:7863 \
  -v "$PWD/voices:/voices:ro" \
  --restart unless-stopped \
  dockermaker0/indextts2:audio-cpp-latest
```

首次启动会加载完整模型，`/health` 在模型加载完成后才会成功。模型已经在镜像中，不会在启动时下载。

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
curl http://127.0.0.1:7863/health
curl http://127.0.0.1:7863/v1/models
```

生成语音：

```bash
curl http://127.0.0.1:7863/v1/audio/speech \
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

## 生产注意事项

- audio.cpp 对同一个模型串行执行推理；超过等待上限的新请求返回 HTTP 503。需要在上游设置有界队列和重试策略。
- 服务本身没有鉴权。不要直接暴露到公网，应放在 Nginx、Caddy 或 API Gateway 后面实现 HTTPS、鉴权、限流和请求审计。
- 当前 IndexTTS 2.5 是离线生成，不支持流式语音输出。
- `server.json` 默认不记录请求正文，避免文本和本地文件路径进入日志。
- 如需修改设备、线程数、缓存或端口，可以挂载完整配置并设置 `AUDIOCPP_CONFIG`：

```bash
docker run --gpus all \
  -p 9000:9000 \
  -e AUDIOCPP_CONFIG=/config/server.json \
  -v "$PWD/server.json:/config/server.json:ro" \
  -v "$PWD/voices:/voices:ro" \
  dockermaker0/indextts2:audio-cpp-latest
```

## 本地构建

构建过程会下载约 4.55GB 的 F16 GGUF 模型：

```bash
docker build \
  -f docker/audio-cpp/Dockerfile \
  -t dockermaker0/indextts2:audio-cpp-local \
  .
```

模型文件和 audio.cpp 基础镜像都固定了提交及校验值，避免上游更新导致同一 Dockerfile 产生不同运行结果。
