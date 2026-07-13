import io
import sys
from pathlib import Path


APP_DIR = Path(__file__).parents[2] / "docker" / "app"
sys.path.insert(0, str(APP_DIR))

from speaker_store import SpeakerStore  # noqa: E402


def test_add_deduplicates_and_lists(tmp_path):
    store = SpeakerStore(tmp_path / "speakers")

    first = store.add(io.BytesIO(b"RIFF-fake-wave"), "Alice")
    second = store.add(io.BytesIO(b"RIFF-fake-wave"), "Alice updated")

    assert first["status"] == "new"
    assert second["status"] == "cached"
    assert first["speaker_id"] == second["speaker_id"]
    assert store.get(first["speaker_id"]).is_file()
    assert store.list()[0]["name"] == "Alice updated"
    assert "audio_path" not in store.list()[0]


def test_delete_removes_audio_and_metadata(tmp_path):
    store = SpeakerStore(tmp_path / "speakers")
    item = store.add(io.BytesIO(b"audio"))
    audio_path = store.get(item["speaker_id"])

    assert store.delete(item["speaker_id"])
    assert not audio_path.exists()
    assert store.get(item["speaker_id"]) is None
    assert not store.delete(item["speaker_id"])


def test_corrupt_index_is_not_silently_discarded(tmp_path):
    store = SpeakerStore(tmp_path / "speakers")
    store.index_path.write_text("not json", encoding="utf-8")

    try:
        store.list()
    except RuntimeError as exc:
        assert "Invalid speaker index" in str(exc)
    else:
        raise AssertionError("corrupt index should fail loudly")


def test_empty_upload_is_rejected(tmp_path):
    store = SpeakerStore(tmp_path / "speakers")

    try:
        store.add(io.BytesIO(b""))
    except ValueError as exc:
        assert "Empty speaker audio" in str(exc)
    else:
        raise AssertionError("empty uploads must not be cached")
