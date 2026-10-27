$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $projectRoot ('data\installer-test-' + [guid]::NewGuid().ToString('N'))
$destination = Join-Path $testRoot 'codex-recorder'
& (Join-Path $projectRoot 'scripts\install_skill.ps1') -Destination $destination
$marker = Get-Content -LiteralPath (Join-Path $destination 'installation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($marker.projectRoot -ne $projectRoot) { throw 'Installed skill points to the wrong project.' }
$skill = Get-Content -LiteralPath (Join-Path $destination 'SKILL.md') -Raw -Encoding UTF8
if (-not $skill.Contains('name: codex-recorder') -or -not $skill.Contains('installation.json')) { throw 'Installed skill is not self-locating.' }
& (Join-Path $projectRoot 'scripts\install_skill.ps1') -Destination $destination
$unmanaged = Join-Path $testRoot 'unmanaged'
New-Item -ItemType Directory -Path $unmanaged -Force | Out-Null
$sentinel = Join-Path $unmanaged 'SKILL.md'
Set-Content -LiteralPath $sentinel -Value 'Existing unrelated skill' -Encoding UTF8
$rejected = $false
try {
    & (Join-Path $projectRoot 'scripts\install_skill.ps1') -Destination $unmanaged
} catch {
    $rejected = $true
}
if (-not $rejected -or (Get-Content -LiteralPath $sentinel -Raw -Encoding UTF8).Trim() -ne 'Existing unrelated skill') {
    throw 'Installer overwrote an unrelated skill.'
}
Write-Host 'PASS: project pointer, repeat install, and unrelated-skill protection.'
