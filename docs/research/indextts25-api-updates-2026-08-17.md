# IndexTTS 2.5 / audio.cpp API 更新调研（2026-08-17）

## 结论

- **需要更新 `dockermaker0/indextts25-api`。** 现有 audio.cpp 固定点 `04ba4375ed53bbd718bd2697e190007f6a19f426` 之后，已有 32 个主线提交；其中至少有三项与本 API 镜像直接相关：内联 base64 参考音频、`duration_factor` 调速、IndexTTS F16 权重/计算路径修复。
- 建议本次固定到调研时的 audio.cpp `main`：[`980bd4164b9de744b618a6b0d5e6e515de94999a`](https://github.com/0xShug0/audio.cpp/commit/980bd4164b9de744b618a6b0d5e6e515de94999a)，不要使用浮动 `main`。这些修复尚未进入新的正式标签；最新标签仍是 [`release-0.6`](https://github.com/0xShug0/audio.cpp/releases/tag/release-0.6)，且该标签早于现有固定点和下述更新。
- **官方 IndexTTS/WebUI 暂不需要再次同步。** 官方 `index-tts/index-tts` 当前 `main` 仍恰好是 `4f8792ff120cd3ea470dd511e997a17c86cddd10`，与上次同步点完全一致，没有新增提交。
- 官方 Hugging Face 模型仓库当前仍是 [`c39ce5ba981572cb187443877ff559dfb246ce63`](https://huggingface.co/IndexTeam/IndexTTS-2.5/commit/c39ce5ba981572cb187443877ff559dfb246ce63)，最后更新于 2026-08-12；无需重新下载另一版官方权重。audio.cpp 的 IndexTTS 2.5 GGUF 三个文件于 2026-08-13 加入，之后仅模型卡有更新，未发现 GGUF 权重替换，见 [GGUF 提交历史](https://huggingface.co/audio-cpp/audio.cpp-gguf/commits/main)。

## PR #239：调速已经合并

[audio.cpp PR #239](https://github.com/0xShug0/audio.cpp/pull/239) 已于 **2026-08-14 20:05:58 UTC** 合并，合并提交为 [`52b4e2c87894e5cd05cbfb30eca6367e5b25feb0`](https://github.com/0xShug0/audio.cpp/commit/52b4e2c87894e5cd05cbfb30eca6367e5b25feb0)。

实现与官方 IndexTTS 2.5 的 `duration_factor` 对齐：S2Mel 长度调节器的目标帧数改为：

```text
target_frames = content_frames * 1.72 * duration_factor
```

- 默认值：`1.0`
- `duration_factor > 1`：输出更长，语速更慢
- `duration_factor < 1`：输出更短，语速更快
- 必须是有限的正浮点数；`0`、负数或非有限值会被拒绝
- v2 和 v2.5 都接受此参数
- WebUI 滑块给出的范围是 `0.5`～`2.0`，但服务端代码只校验 `> 0`，API 本身没有硬性上限

### API 的准确请求格式

它不是 OpenAI `speed` 顶层字段，而是 audio.cpp 的模型请求选项，必须放在 `options.duration_factor`：

```bash
curl http://127.0.0.1:7864/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -o output.wav \
  -d '{
    "model": "indextts-2.5",
    "input": "这是一段加速后的语音。",
    "voice_ref": "/voices/reference.wav",
    "options": {
      "duration_factor": 0.8
    }
  }'
```

其中 `model` 要与镜像服务器配置中的模型 ID 一致。也可以在服务器模型配置的 `default_request_options` 中设置默认值；请求体内的 `options` 会覆盖默认值。服务端映射逻辑见 [server runtime](https://github.com/0xShug0/audio.cpp/blob/980bd4164b9de744b618a6b0d5e6e515de94999a/app/server/runtime.cpp)，参数说明见 [TTS 文档](https://github.com/0xShug0/audio.cpp/blob/980bd4164b9de744b618a6b0d5e6e515de94999a/docs/tts.md#indextts25)。

生产环境建议在 API 网关或调用 SDK 中把取值限制为例如 `0.5`～`2.0`。极端的大倍率会显著增加目标帧数、生成时间和内存压力；极端的小倍率也可能损害可懂度。

## 其他与生产 API 直接相关的更新

### 1. 支持请求内携带 base64 参考音频

[PR #226](https://github.com/0xShug0/audio.cpp/pull/226) 已合并为 [`c86c14e5dd0734c9dfb46f8c690442b0663bb509`](https://github.com/0xShug0/audio.cpp/commit/c86c14e5dd0734c9dfb46f8c690442b0663bb509)。`POST /v1/audio/speech` 的 `voice_ref` 现在接受：

```json
{
  "voice_ref": {
    "type": "base64",
    "data": "UklGRi..."
  }
}
```

也接受 `data:audio/wav;base64,...` URI。解码后的参考 WAV 上限为 **5 MiB**；更大的音频必须继续使用服务器路径。这个改动使客户端无需先把参考音频写入服务器共享目录，适合无状态 API 调用，但仍应在反向代理设置请求体大小上限。完整行为见 [audio.cpp Server 文档](https://github.com/0xShug0/audio.cpp/blob/980bd4164b9de744b618a6b0d5e6e515de94999a/app/server/README.md#post-v1audiospeech)。

### 2. IndexTTS F16 路径修复

[PR #247](https://github.com/0xShug0/audio.cpp/pull/247) 已合并为 [`9a5eb8647efb0ad34d2f6110349253129f7a89c6`](https://github.com/0xShug0/audio.cpp/commit/9a5eb8647efb0ad34d2f6110349253129f7a89c6)。修复前，部分宿主机派生权重会静默回退为 F32，CUDA 上的 S2Mel CFM 也固定使用 F32 精度。修复后：

- F16 GGUF 的 BigVGAN/GPT 派生权重继续按 checkpoint dtype 存储；
- CUDA 上 CFM 线性层使用模块默认精度；CPU 等其他后端仍保留原有 F32 规避策略；
- PR 作者在 RTX 2080 Ti 的 IndexTTS 测试中报告总耗时从 6889 ms 降至 5393 ms，约提升 **21.7%**。

该变更落在 v2/v2.5 共用的 `index_tts2` 实现路径中，因此推断也会惠及当前 F16 IndexTTS 2.5 镜像；不过 PR 的公开基准只写明 IndexTTS-2，升级后仍应在 2.5 上做音质与耗时回归测试。

### 3. `--voice-dir` 可由启动参数覆盖

[PR #246](https://github.com/0xShug0/audio.cpp/pull/246) 已合并为 [`f08e61d42c8b8f71713c9d2860d42524e1f2b6c6`](https://github.com/0xShug0/audio.cpp/commit/f08e61d42c8b8f71713c9d2860d42524e1f2b6c6)。服务器新增 `--voice-dir <directory>`，可覆盖 JSON 配置中的 `voice_dir`。这适合 Docker 用统一挂载目录管理音色库，减少为不同模型复制配置。

### 4. 老显卡构建修复

[PR #240](https://github.com/0xShug0/audio.cpp/pull/240) 已合并为 [`5f620b03a626fe5f49422dc8be14ffa5e4aad073`](https://github.com/0xShug0/audio.cpp/commit/5f620b03a626fe5f49422dc8be14ffa5e4aad073)，为 Linux 构建脚本增加 `--cuda-arch`，用于避免计算能力低于 8.9 的旧 GPU 因错误构建目标出现 core dump。若当前 Dockerfile自行调用 CMake 而不走 `build_linux.sh`，应检查是否已显式包含目标 GPU 架构；若使用脚本，则可利用该参数。

## 建议的升级与验证清单

1. 将 audio.cpp 源码从 `04ba4375...` 固定升级到 `980bd416...`，重新构建 `dockermaker0/indextts25-api`；保留旧 digest 作为快速回滚目标。
2. 镜像仍使用端口 `7864`，不要改动 WebUI 的 `7863`。
3. 在 README/API 示例中新增 `options.duration_factor`，并明确它与通常意义上的 `speed` 方向相反：数值越大越慢。
4. 对 `duration_factor=0.75/1.0/1.25` 分别生成同一文本，核对实际 WAV 时长、音色、可懂度和 GPU 峰值；同时验证非法的 `0`、负数会返回客户端错误。
5. 分别测试路径型 `voice_ref` 与 base64 `voice_ref`，并测试超过 5 MiB 的内联音频会被拒绝。
6. 对 F16 镜像进行冷启动、连续请求和并发排队回归，记录升级前后的 GPT、CFM、BigVGAN 与总耗时；不要只依赖 v2 的公开基准推断 2.5 提升幅度。
7. 本次不用更新官方 Python/WebUI 源码或官方模型权重；只有 audio.cpp API 分支需要升级。

## 核查基准

- IndexTTS 官方主线同步点/当前 HEAD：[`4f8792ff120cd3ea470dd511e997a17c86cddd10`](https://github.com/index-tts/index-tts/commit/4f8792ff120cd3ea470dd511e997a17c86cddd10)
- audio.cpp 现有镜像固定点：[`04ba4375ed53bbd718bd2697e190007f6a19f426`](https://github.com/0xShug0/audio.cpp/commit/04ba4375ed53bbd718bd2697e190007f6a19f426)
- audio.cpp 调研时当前 HEAD：[`980bd4164b9de744b618a6b0d5e6e515de94999a`](https://github.com/0xShug0/audio.cpp/commit/980bd4164b9de744b618a6b0d5e6e515de94999a)
- 官方 IndexTTS 2.5 模型：[`IndexTeam/IndexTTS-2.5`](https://huggingface.co/IndexTeam/IndexTTS-2.5)
- audio.cpp GGUF 模型：[`audio-cpp/audio.cpp-gguf/IndexTTS2.5-GGUF`](https://huggingface.co/audio-cpp/audio.cpp-gguf/tree/main/IndexTTS2.5-GGUF)
