# IndexTTS2 Docker

基于 [IndexTTS2 官方仓库](https://github.com/index-tts/index-tts)最新源码构建的 CUDA Docker 镜像，提供：

- 官方 Gradio WebUI（宿主机端口 `7960`）
- REST API 和 Swagger UI（宿主机端口 `8030`，文档路径 `/docs`）
- 内容寻址的说话人参考音频缓存
- 中文/英文基础模型，以及越南语、日语社区模型变体
- 固定源码、CUDA 基础镜像和全部 Hugging Face revision 的稳定构建

当前同步的官方提交记录在 [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT) 中。官方源码的中文说明见
[`docs/README_zh.md`](docs/README_zh.md)。

> [!IMPORTANT]
> IndexTTS2 模型使用自己的模型许可，不是 MIT。越南语和日语 checkpoint 来自第三方社区，使用前请分别审查其模型卡、训练来源和许可。

## 目录

```text
docker/
  Dockerfile                  基础中文/英文镜像
  Dockerfile.vietnamese       越南语模型变体
  Dockerfile.japanese         日语模型变体
  entrypoint.sh               API/WebUI 进程管理
  app/                        Docker 专用 REST API
tests/docker/                 Docker 扩展的单元测试
indextts/                     官方最新 IndexTTS2 源码
tools/, cli_tests/, tests/    官方工具及测试
```

## 直接运行

```bash
docker run -d \
  --name indextts2 \
  --gpus all \
  --shm-size 8g \
  -p 8030:8002 \
  -p 7960:7860 \
  -v indextts2-outputs:/app/outputs \
  musicking/indextts2:latest
```

访问：

- WebUI：<http://localhost:7960>
- API 文档：<http://localhost:8030/docs>
- 健康检查：<http://localhost:8030/health>

默认同时启动 API 和 WebUI，因此会在同一张 GPU 上加载两份模型。显存不足时只启动一个服务：

```bash
# 只启动 API
docker run --gpus all -e INDEXTTS_SERVICES=api -p 8030:8002 musicking/indextts2:latest

# 只启动 WebUI
docker run --gpus all -e INDEXTTS_SERVICES=webui -p 7960:7860 musicking/indextts2:latest
```

## REST API

先上传参考音频：

```bash
curl -X POST http://localhost:8030/speakers \
  -F "audio=@reference.wav" \
  -F "name=Alice"
```

返回的 `speaker_id` 可重复使用：

```bash
curl -X POST http://localhost:8030/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"你好，这是一次测试。","speaker_id":"spk_xxxxxxxxxxxxxxxx"}' \
  --output result.wav
```

说话人缓存只保存上传音频和 JSON 元数据，不再反序列化不安全的 pickle，也不依赖 IndexTTS2 的私有 GPU 缓存字段。单进程推理由锁串行化，避免并发请求破坏模型状态。

## 本地构建

### 为什么使用 CUDA 12.8.1

当前官方 `pyproject.toml` 固定 `torch==2.8.*`，并从 PyTorch 的 `cu128` 仓库安装 CUDA 12.8 构建；官方文档也建议源码安装环境使用 CUDA Toolkit 12.8 或更高版本。因此基础镜像选择 CUDA 12.8.1，主要目的是让容器工具链、PyTorch wheel 和可选 CUDA kernel 保持 ABI/编译环境一致。

使用 Docker 时，宿主机不需要安装 CUDA Toolkit 12.8；CUDA 用户态库位于镜像内。宿主机需要足够新的 NVIDIA 驱动，以及 NVIDIA Container Toolkit。

基础镜像包含官方完整 checkpoint 和运行所需的辅助模型：

```bash
docker build -f docker/Dockerfile -t musicking/indextts2:latest .
```

语言镜像从刚构建的基础镜像派生：

```bash
docker build -f docker/Dockerfile.vietnamese \
  --build-arg BASE_IMAGE=musicking/indextts2:latest \
  -t musicking/indextts2:latest-vietnamese .

docker build -f docker/Dockerfile.japanese \
  --build-arg BASE_IMAGE=musicking/indextts2:latest \
  -t musicking/indextts2:latest-japanese .
```

越南语镜像同时替换匹配的 `config.yaml`、`bpe.model` 和 `gpt.pth`；旧项目只替换 `gpt.pth` 的 tokenizer 不一致问题已修复。日语镜像同样保持配置、BPE tokenizer 和 GPT checkpoint 成套匹配。

所有模型 revision 都固定在 Dockerfile 中。需要明确升级时通过 build args 覆盖，而不是在相同 Dockerfile 下悄悄获得不同权重。

## Compose

```bash
docker compose up -d --build
```

这条命令只构建并运行 `docker-compose.yml` 中的基础中文/英文镜像，不会同时构建越南语和日语镜像。

如果只需要越南语，且本地还没有基础镜像：

```bash
docker compose build indextts2
docker build -f docker/Dockerfile.vietnamese \
  --build-arg BASE_IMAGE=musicking/indextts2:latest \
  -t musicking/indextts2:latest-vietnamese .
docker push musicking/indextts2:latest-vietnamese
```

如果基础镜像已发布，也可以先 `docker pull musicking/indextts2:latest`，然后只执行语言镜像的 `docker build` 和 `docker push`。日语只需将 Dockerfile 和标签分别换为 `Dockerfile.japanese` 与 `latest-japanese`。

GitHub Actions 手工发布时可通过 `flavor` 选择 `base`、`vietnamese`、`japanese` 或 `all`。单独发布语言版时使用 Docker Hub 上现有的 `latest` 基础镜像；选择 `all` 时则使用本次工作流刚构建的同一 Git commit 基础镜像。

注意：不要把一个空的宿主机 `checkpoints/` 挂载到 `/app/checkpoints`，否则会遮蔽镜像内置模型。

## 验证

```bash
uv sync --frozen --extra test
uv pip install -r docker/requirements.txt
uv run pytest tests/docker
```

## 维护原则

- 官方源码以 `index-tts/index-tts` 为唯一上游。
- 上游源码更新与模型 revision 更新分开审核。
- Docker 发布工作流使用 `musicking/indextts2`，并实际执行 push。
- 构建失败不会再用 `|| true` 静默忽略模型错误。
- 生成物、性能实验报告和临时 benchmark 不提交到仓库。

同步下一版官方源码前先确保工作区干净，然后运行：

```powershell
.\scripts\sync-upstream.ps1
```

Linux/macOS：

```bash
./scripts/sync-upstream.sh
```

脚本只更新官方源码、工具和依赖文件，不覆盖本仓库的 `docker/`、Docker README、Compose 和发布工作流。同步后仍需审核上游依赖变化，并相应更新 `docker/Dockerfile` 中的 `UPSTREAM_REVISION`。
