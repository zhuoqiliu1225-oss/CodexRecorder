$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $projectRoot 'verification'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speech.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female, [System.Speech.Synthesis.VoiceAge]::Adult, 0, [System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
    $speech.SetOutputToWaveFile((Join-Path $destination 'sample-en.wav'))
    $speech.Speak('We will launch the first version next Friday. Alice will finish testing on Thursday. The budget is five hundred dollars.')
} finally {
    $speech.Dispose()
}
Write-Host 'Synthetic fixture saved to verification/sample-en.wav'
