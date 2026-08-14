# IndexTTS 2.5 WebUI Docker

基于官方 [IndexTTS](https://github.com/index-tts/index-tts) 源码构建的
IndexTTS 2.5 CUDA 镜像，默认只启动 Gradio WebUI，监听 `7863` 端口。

镜像包含固定版本的 IndexTTS 2.5 checkpoint 和运行所需的辅助模型，启动时不需要重新下载大模型。
当前固定的官方源码提交见 [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT)。

> [!IMPORTANT]
> IndexTTS 源码和模型使用其各自许可，不是 MIT。商用或分发前请阅读仓库中的
> `LICENSE`、`DISCLAIMER` 以及模型仓库的许可文件。

## 直接运行

要求宿主机已安装 NVIDIA 驱动、Docker 和 NVIDIA Container Toolkit。

```bash
docker run -d \
  --name indextts25 \
  --gpus all \
  --shm-size 8g \
  -p 7863:7863 \
  -v indextts25-outputs:/app/outputs \
  --restart unless-stopped \
  dockermaker0/indextts2:latest
```

浏览器访问：<http://localhost:7863>

查看日志：

```bash
docker logs -f indextts25
```

## Docker Compose

```bash
docker compose up -d
docker compose logs -f
```

默认配置：

- IndexTTS 版本：`2.5`
- WebUI 容器端口：`7863`
- BF16：开启
- CUDA 自定义 kernel：关闭，优先保证兼容性
- 输出目录：Docker volume `indextts25-outputs`

可以通过环境变量覆盖运行参数：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WEBUI_PORT` | `7863` | WebUI 监听端口 |
| `USE_BF16` | `1` | 设为 `0` 关闭 BF16 |
| `USE_CUDA_KERNEL` | `0` | 设为 `1` 开启 BigVGAN CUDA kernel |
| `USE_TORCH_COMPILE` | `0` | 设为 `1` 开启 torch.compile |
| `MODEL_DIR` | `/app/checkpoints` | 模型目录 |

## 本地构建

```bash
docker build -f docker/Dockerfile -t dockermaker0/indextts2:2.5 .
```

构建参数均固定为可复现版本：

- 官方源码：`4f8792ff120cd3ea470dd511e997a17c86cddd10`
- 模型：`IndexTeam/IndexTTS-2.5`
- 模型 revision：`c39ce5ba981572cb187443877ff559dfb246ce63`
- CUDA 基础镜像：`12.8.1 + cuDNN + Ubuntu 22.04`
- Python：`3.11`
- PyTorch：官方项目锁定的 `2.8.x + cu128`

## GitHub Actions 发布

`.github/workflows/docker-publish.yml` 会在以下情况构建并推送 Docker Hub：

- 发布 GitHub Release；
- 在 Actions 页面手动运行并输入版本号。

目标镜像：

```text
dockermaker0/indextts2:<version>
dockermaker0/indextts2:2.5
dockermaker0/indextts2:latest
dockermaker0/indextts2:sha-<git-sha>
```

工作流使用 GitHub Environment `docker` 中的 `DOCKER_USERNAME` 和
`DOCKER_PASSWORD` secrets。

## 分支

- `main`：IndexTTS 2.5 WebUI 镜像。
- `archive/indextts-2.0`：升级前的 IndexTTS 2.0 完整备份。
