from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from threading import RLock
from typing import BinaryIO


class SpeakerStore:
    """Content-addressed speaker audio storage with atomic JSON metadata."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._lock = RLock()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.index_path.exists():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Invalid speaker index: {self.index_path}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid speaker index: {self.index_path}")
        return data

    def _save(self, index: dict[str, dict[str, str]]) -> None:
        fd, temp_name = tempfile.mkstemp(prefix="index-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(index, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.index_path)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def add(self, stream: BinaryIO, name: str | None = None) -> dict[str, str]:
        digest = hashlib.sha256()
        byte_count = 0
        fd, temp_name = tempfile.mkstemp(prefix="upload-", suffix=".wav", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as output:
                while chunk := stream.read(1024 * 1024):
                    byte_count += len(chunk)
                    digest.update(chunk)
                    output.write(chunk)
            sha256 = digest.hexdigest()
            if byte_count == 0:
                raise ValueError("Empty speaker audio")
            speaker_id = f"spk_{sha256[:16]}"
            audio_path = self.root / f"{speaker_id}.wav"
            with self._lock:
                index = self._load()
                existed = speaker_id in index and audio_path.exists()
                if not existed:
                    shutil.move(temp_name, audio_path)
                index[speaker_id] = {
                    "speaker_id": speaker_id,
                    "name": (name or speaker_id).strip() or speaker_id,
                    "sha256": sha256,
                    "audio_path": str(audio_path),
                }
                self._save(index)
            return {**index[speaker_id], "status": "cached" if existed else "new"}
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def get(self, speaker_id: str) -> Path | None:
        with self._lock:
            item = self._load().get(speaker_id)
        if not item:
            return None
        path = Path(item["audio_path"]).resolve()
        if path.parent != self.root or not path.is_file():
            return None
        return path

    def list(self) -> list[dict[str, str]]:
        with self._lock:
            return [
                {key: value for key, value in item.items() if key != "audio_path"}
                for item in self._load().values()
            ]

    def delete(self, speaker_id: str) -> bool:
        with self._lock:
            index = self._load()
            item = index.pop(speaker_id, None)
            if item is None:
                return False
            path = Path(item["audio_path"]).resolve()
            if path.parent == self.root:
                path.unlink(missing_ok=True)
            self._save(index)
            return True
