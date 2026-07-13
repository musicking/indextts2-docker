from __future__ import annotations

import os
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from flask import Flask, jsonify, request, send_file
from flask_swagger_ui import get_swaggerui_blueprint

from speaker_store import SpeakerStore


EMOTION_KEYS = (
    "happy", "angry", "sad", "afraid", "disgusted", "melancholic", "surprised", "calm"
)


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.lower() in {"1", "true", "yes", "on"}


def _load_tts():
    from indextts.infer_v2 import IndexTTS2

    model_dir = os.getenv("MODEL_DIR", "/app/checkpoints")
    return IndexTTS2(
        cfg_path=str(Path(model_dir) / "config.yaml"),
        model_dir=model_dir,
        use_fp16=_as_bool("USE_FP16", True),
        use_cuda_kernel=_as_bool("USE_CUDA_KERNEL", True),
        use_torch_compile=_as_bool("USE_TORCH_COMPILE", False),
    )


def _openapi_spec() -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "IndexTTS2 Docker API", "version": "3.0.0"},
        "paths": {
            "/health": {"get": {"summary": "Readiness and model status"}},
            "/speakers": {
                "get": {"summary": "List cached speaker prompts"},
                "post": {"summary": "Upload a speaker prompt (multipart audio + optional name)"},
            },
            "/speakers/{speaker_id}": {
                "delete": {
                    "summary": "Delete a cached speaker prompt",
                    "parameters": [{"name": "speaker_id", "in": "path", "required": True}],
                }
            },
            "/tts": {"post": {"summary": "Synthesize speech from JSON text and speaker_id"}},
        },
    }


def create_app(tts=None, store: SpeakerStore | None = None) -> Flask:
    output_dir = Path(os.getenv("OUTPUT_DIR", "/app/outputs")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    store = store or SpeakerStore(output_dir / "speakers")
    tts = tts or _load_tts()
    inference_lock = Lock()

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "32")) * 1024 * 1024
    app.register_blueprint(
        get_swaggerui_blueprint("/docs", "/openapi.json", config={"app_name": "IndexTTS2 Docker API"}),
        url_prefix="/docs",
    )

    @app.get("/openapi.json")
    def openapi():
        return jsonify(_openapi_spec())

    @app.get("/health")
    def health():
        return jsonify(status="ready", device=str(tts.device), speakers=len(store.list()))

    @app.get("/speakers")
    def list_speakers():
        speakers = store.list()
        return jsonify(speakers=speakers, count=len(speakers))

    def add_speaker():
        audio = request.files.get("audio")
        if audio is None or not audio.filename:
            return jsonify(error="multipart field 'audio' is required"), 400
        try:
            result = store.add(audio.stream, request.form.get("name") or request.form.get("speaker_name"))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(result), 201 if result["status"] == "new" else 200

    app.add_url_rule("/speakers", view_func=add_speaker, methods=["POST"])
    app.add_url_rule("/upload_speaker", view_func=add_speaker, methods=["POST"])

    @app.delete("/speakers/<speaker_id>")
    def delete_speaker(speaker_id: str):
        if not store.delete(speaker_id):
            return jsonify(error="speaker not found"), 404
        return jsonify(status="deleted", speaker_id=speaker_id)

    @app.post("/tts")
    def synthesize():
        data = request.get_json(silent=True) or {}
        text = data.get("text")
        speaker_id = data.get("speaker_id")
        if not isinstance(text, str) or not text.strip() or not isinstance(speaker_id, str):
            return jsonify(error="JSON fields 'text' and 'speaker_id' are required"), 400
        speaker_path = store.get(speaker_id)
        if speaker_path is None:
            return jsonify(error="speaker not found"), 404

        emotion = data.get("emo_vector")
        if emotion is None and any(key in data for key in EMOTION_KEYS):
            emotion = [float(data.get(key, 0.0)) for key in EMOTION_KEYS]
        if emotion is not None and (
            not isinstance(emotion, list)
            or len(emotion) != 8
            or any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in emotion)
        ):
            return jsonify(error="emo_vector must contain eight numbers between 0 and 1"), 400

        output_path = output_dir / f"tts_{uuid.uuid4().hex}.wav"
        kwargs = {
            "spk_audio_prompt": str(speaker_path),
            "text": text.strip(),
            "output_path": str(output_path),
            "emo_vector": emotion,
            "emo_alpha": min(1.0, max(0.0, float(data.get("emo_alpha", 1.0)))),
            "use_emo_text": bool(data.get("use_emo_text", False)),
            "emo_text": data.get("emo_text"),
            "use_random": bool(data.get("use_random", False)),
            "verbose": bool(data.get("verbose", False)),
            "max_text_tokens_per_segment": min(
                600, max(20, int(data.get("max_text_tokens_per_segment", 120)))
            ),
        }
        with inference_lock:
            tts.infer(**kwargs)
        return send_file(output_path, mimetype="audio/wav", download_name=output_path.name)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("API_PORT", "8002")))
