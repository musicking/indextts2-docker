from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download


AUXILIARY_MODELS = {
    "w2v_bert": ("facebook/w2v-bert-2.0", "da985ba0987f70aaeb84a80f2851cfac8c697a7b"),
    "semantic_codec": ("amphion/MaskGCT", "265c6cef07625665d0c28d2faafb1415562379dc"),
    "campplus": ("funasr/campplus", "e4b6ede7ce16997aff4ae69fbca1f0175e2afede"),
    "bigvgan": (
        "nvidia/bigvgan_v2_22khz_80band_256x",
        "633ff708ed5b74903e86ff1298cf4a98e921c513",
    ),
}


def download_file(repo: str, revision: str, filename: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        source = hf_hub_download(
            repo_id=repo,
            revision=revision,
            filename=filename,
            local_dir=temp_dir,
        )
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-repo", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--model-dir", type=Path, default=Path("checkpoints"))
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=args.model_repo,
        revision=args.model_revision,
        local_dir=model_dir,
    )

    cache_dir = model_dir / "hf_cache"
    w2v_repo, w2v_revision = AUXILIARY_MODELS["w2v_bert"]
    snapshot_download(
        repo_id=w2v_repo,
        revision=w2v_revision,
        local_dir=cache_dir / "w2v-bert-2.0",
    )

    codec_repo, codec_revision = AUXILIARY_MODELS["semantic_codec"]
    download_file(
        codec_repo,
        codec_revision,
        "semantic_codec/model.safetensors",
        cache_dir / "semantic_codec_model.safetensors",
    )

    camp_repo, camp_revision = AUXILIARY_MODELS["campplus"]
    download_file(
        camp_repo,
        camp_revision,
        "campplus_cn_common.bin",
        cache_dir / "campplus_cn_common.bin",
    )

    bigvgan_repo, bigvgan_revision = AUXILIARY_MODELS["bigvgan"]
    for filename in ("config.json", "bigvgan_generator.pt"):
        download_file(
            bigvgan_repo,
            bigvgan_revision,
            filename,
            cache_dir / "bigvgan" / filename,
        )

    required = (
        model_dir / "config.yaml",
        model_dir / "bpe.model",
        model_dir / "gpt.pth",
        model_dir / "s2mel.pth",
        cache_dir / "w2v-bert-2.0" / "config.json",
        cache_dir / "semantic_codec_model.safetensors",
        cache_dir / "campplus_cn_common.bin",
        cache_dir / "bigvgan" / "bigvgan_generator.pt",
    )
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"Model download incomplete: {missing}")


if __name__ == "__main__":
    main()

