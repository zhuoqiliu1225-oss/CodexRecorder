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
Write-Host '准备完成。首次启动会下载语音模型。请确认 codex login status 显示 ChatGPT 登录。'
Write-Host '在 Codex 中说“开始录音”，或运行 node scripts/control.cjs start。'
