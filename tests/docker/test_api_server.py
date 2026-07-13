import io
import sys
from pathlib import Path


APP_DIR = Path(__file__).parents[2] / "docker" / "app"
sys.path.insert(0, str(APP_DIR))

from api_server import create_app  # noqa: E402
from speaker_store import SpeakerStore  # noqa: E402


class FakeTTS:
    device = "test"

    def __init__(self):
        self.calls = []

    def infer(self, **kwargs):
        self.calls.append(kwargs)
        Path(kwargs["output_path"]).write_bytes(b"RIFF-result")


def test_upload_synthesize_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    tts = FakeTTS()
    app = create_app(tts=tts, store=SpeakerStore(tmp_path / "speakers"))
    client = app.test_client()

    upload = client.post(
        "/speakers",
        data={"audio": (io.BytesIO(b"RIFF-prompt"), "prompt.wav"), "name": "Alice"},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    speaker_id = upload.get_json()["speaker_id"]

    response = client.post("/tts", json={"text": "hello", "speaker_id": speaker_id})
    assert response.status_code == 200
    assert response.data == b"RIFF-result"
    assert tts.calls[0]["text"] == "hello"

    assert client.delete(f"/speakers/{speaker_id}").status_code == 200
    assert client.post("/tts", json={"text": "hello", "speaker_id": speaker_id}).status_code == 404


def test_rejects_invalid_emotion_vector(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    store = SpeakerStore(tmp_path / "speakers")
    speaker = store.add(io.BytesIO(b"audio"))
    app = create_app(tts=FakeTTS(), store=store)

    response = app.test_client().post(
        "/tts",
        json={"text": "hello", "speaker_id": speaker["speaker_id"], "emo_vector": [1, 2]},
    )
    assert response.status_code == 400

