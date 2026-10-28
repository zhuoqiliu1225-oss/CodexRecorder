param([string]$Python = 'python', [string]$Model = 'base', [switch]$SkipTranslationModel)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 环境创建失败。请安装 Python 3.11 或更高版本。' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败。' }
if (-not (Test-Path -LiteralPath 'local.settings.json')) {
    @{ model = $Model; port = 18764; device = 'auto'; codex = 'codex'; cuda_library_dirs = @() } | ConvertTo-Json | Set-Content -LiteralPath 'local.settings.json' -Encoding utf8
}
if (-not $SkipTranslationModel) {
    Write-Host '准备本地多语言翻译模型（约 500 MB），首次需要下载。'
    & '.\.venv\Scripts\python.exe' scripts/prepare_translation.py
    if ($LASTEXITCODE -ne 0) { throw '翻译模型下载未完成，可重试或使用 -SkipTranslationModel。' }
    $settings = Get-Content local.settings.json | ConvertFrom-Json
    $settings | Add-Member -NotePropertyName multilingual_model -NotePropertyValue 'models/m2m100' -Force
    $settings | ConvertTo-Json | Set-Content local.settings.json -Encoding utf8
}
Write-Host '依赖安装完成。首次启动仍需下载语音模型、加载并暖机；时间取决于网络、模型大小和硬件。'
Write-Host 'Dependencies installed. The first service start still downloads, loads and warms up models; allow time for this.'
Write-Host '接下来运行 scripts/install_skill.ps1，再运行 node scripts/control.cjs serve。'
Write-Host 'Next: run scripts/install_skill.ps1, then node scripts/control.cjs serve (no microphone recording yet).'
Write-Host '用 node scripts/control.cjs status 确认 engine.status 为 ready；请勿反复启动。'
Write-Host 'Wait for engine.status=ready. Confirm codex login status uses ChatGPT, then ask $codex-recorder to start recording.'
Write-Host '使用指南 / User guide: docs/USAGE.zh-CN.md / docs/USAGE.md'
