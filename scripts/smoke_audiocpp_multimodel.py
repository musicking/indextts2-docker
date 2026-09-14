"""Post-deployment API smoke checks; requires a short speech WAV and exact transcript.

Example:
  python scripts/smoke_audiocpp_multimodel.py --audio narrator.wav \
    --reference-text "The exact words spoken in the reference audio."

Checks response structure, not transcription accuracy, voice quality or throughput.
"""

import argparse
import base64
import json
from pathlib import Path
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MODEL_IDS = {"indextts-2.5", "voxcpm2", "qwen3-asr-1.7b", "qwen3-forced-aligner-0.6b"}


def request(base, endpoint, body=None, content_type=None, timeout=600):
    headers = {"Content-Type": content_type} if content_type else {}
    try:
        with urlopen(Request(base + endpoint, data=body, headers=headers), timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        raise RuntimeError(f"{endpoint}: HTTP {error.code}: {error.read().decode(errors='replace')}") from error


def multipart(fields, audio):
    boundary = "api-smoke-" + uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="speech.wav"\r\n'
        'Content-Type: audio/wav\r\n\r\n'.encode() + audio + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:7864")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--synthesis-text", default="你好，这是多模型 API 验收测试。")
    parser.add_argument("--output-dir", type=Path, default=Path("api-smoke-results"))
    args = parser.parse_args()
    base = args.url.rstrip("/")
    audio = args.audio.read_bytes()
    require(44 < len(audio) <= 5 * 1024 * 1024, "Use a short speech WAV smaller than 5 MiB.")
    require(audio[:4] == b"RIFF" and audio[8:12] == b"WAVE", "Input must be a RIFF WAV.")
    require(bool(args.reference_text.strip()), "An exact, non-empty transcript is required.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    request(base, "/health", timeout=30)
    listing = json.loads(request(base, "/v1/models", timeout=30))
    require(MODEL_IDS <= {model["id"] for model in listing["data"]}, "Required models are not registered.")

    def words_check(endpoint, fields, filename):
        body, content_type = multipart(fields, audio)
        result = json.loads(request(base, endpoint, body, content_type))
        (args.output_dir / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        require(bool(result.get("words")), f"{endpoint} returned no words; inspect {filename}.")
        print(f"PASS {endpoint}: {len(result['words'])} words", flush=True)

    words_check("/v1/audio/transcriptions/details", {"model": "qwen3-asr-1.7b"}, "asr.json")
    words_check("/v1/audio/alignments", {
        "model": "qwen3-forced-aligner-0.6b", "text": args.reference_text
    }, "alignment.json")

    for model in ("indextts-2.5", "voxcpm2"):
        body = json.dumps({
            "model": model, "input": args.synthesis_text,
            "voice_ref": {"type": "base64", "data": base64.b64encode(audio).decode("ascii")},
            "reference_text": args.reference_text, "response_format": "wav",
        }).encode()
        output = request(base, "/v1/audio/speech", body, "application/json")
        require(len(output) > 44 and output[:4] == b"RIFF" and output[8:12] == b"WAVE", f"{model} did not return a WAV.")
        (args.output_dir / f"{model}.wav").write_bytes(output)
        print(f"PASS {model}: WAV saved", flush=True)

    # Under the shipped single-resident configuration this also exercises reloading
    # Qwen ASR and its auxiliary aligner after switching through the other models.
    words_check("/v1/audio/transcriptions/details", {"model": "qwen3-asr-1.7b"}, "asr-after-switch.json")
    print(f"Smoke checks passed. Review audio quality and JSON in {args.output_dir.resolve()}.")


if __name__ == "__main__":
    main()
