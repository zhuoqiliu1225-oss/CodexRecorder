param([string]$Destination = (Join-Path $env:USERPROFILE '.agents\skills\codex-recorder'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $projectRoot '.agents\skills\recorder\SKILL.md'
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'app\server.py'))) {
    throw 'Install the complete CodexRecorder repository before installing its skill.'
}
$marker = Join-Path $Destination 'installation.json'
$repository = 'https://github.com/zhuoqiliu1225-oss/CodexRecorder'
if (Test-Path -LiteralPath $Destination) {
    if (-not (Test-Path -LiteralPath $marker)) {
        throw 'The destination already exists and is not managed by CodexRecorder. Use -Destination to choose another folder.'
    }
    $previous = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($previous.repository -ne $repository) {
        throw 'The destination belongs to another installation. No files were changed.'
    }
}
$content = Get-Content -LiteralPath $source -Raw -Encoding UTF8
$content = $content.Replace('name: recorder', 'name: codex-recorder')
$content = $content.Replace('仓库根目录是此技能目录的上三级。', '先读取此技能目录的 installation.json；projectRoot 字段是已安装程序的完整根目录。')
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $Destination 'SKILL.md'), $content, $utf8)
$config = @{ repository = $repository; projectRoot = $projectRoot; version = '0.2' } | ConvertTo-Json
[System.IO.File]::WriteAllText($marker, $config, $utf8)
Write-Host "Installed codex-recorder skill: $Destination"
Write-Host 'Keep the complete project folder in place. If the skill is not visible, start a new Codex chat.'
