#!/usr/bin/env bash
set -Eeuo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
  echo "The working tree must be clean before syncing upstream." >&2
  exit 1
fi

if ! git -C "$repo" remote get-url upstream >/dev/null 2>&1; then
  git -C "$repo" remote add upstream https://github.com/index-tts/index-tts.git
fi

git -C "$repo" fetch upstream main

paths=(
  .python-version DISCLAIMER LICENSE LICENSE_ZH.txt MANIFEST.in
  archive assets checkpoints cli_tests docs examples indextts tests tools
  pyproject.toml uv.lock webui.py
)
git -C "$repo" restore --source upstream/main -- "${paths[@]}"

revision="$(git -C "$repo" rev-parse upstream/main)"
printf '%s\n' "$revision" >"$repo/UPSTREAM_COMMIT"

echo "Synced official IndexTTS2 source to $revision"
echo "Review upstream dependency/model changes, run tests, then update the Dockerfile label if required."

