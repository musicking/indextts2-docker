[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (git -C $repo status --porcelain) {
    throw 'The working tree must be clean before syncing upstream.'
}

if (-not (git -C $repo remote | Select-String -SimpleMatch 'upstream')) {
    git -C $repo remote add upstream https://github.com/index-tts/index-tts.git
}

git -C $repo fetch upstream main
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to fetch index-tts/index-tts.'
}

$paths = @(
    '.python-version', 'DISCLAIMER', 'LICENSE', 'LICENSE_ZH.txt', 'MANIFEST.in',
    'archive', 'assets', 'checkpoints', 'cli_tests', 'docs', 'examples',
    'indextts', 'tests', 'tools', 'pyproject.toml', 'uv.lock', 'webui.py'
)
git -C $repo restore --source upstream/main -- $paths
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to restore the upstream source tree.'
}

$revision = (git -C $repo rev-parse upstream/main).Trim()
[System.IO.File]::WriteAllText(
    (Join-Path $repo 'UPSTREAM_COMMIT'),
    "$revision`n",
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Synced official IndexTTS2 source to $revision"
Write-Host 'Review upstream dependency/model changes, run tests, then update the Dockerfile label if required.'

