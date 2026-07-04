param(
    [string]$InnoSetupCompiler = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $Root "dist\SmartVoice\SmartVoice.exe"
$Script = Join-Path $Root "packaging\SmartVoice.iss"

if (-not (Test-Path $Exe)) {
    throw "SmartVoice.exe not found. Run .\tools\build_windows.ps1 first."
}

if (-not $InnoSetupCompiler) {
    $Candidates = @(
        "ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )

    foreach ($Candidate in $Candidates) {
        if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
            $InnoSetupCompiler = $Candidate
            break
        }
    }
}

if (-not $InnoSetupCompiler) {
    throw "Inno Setup compiler not found. Install Inno Setup 6 or pass -InnoSetupCompiler path."
}

Set-Location $Root
& $InnoSetupCompiler $Script
if ($LASTEXITCODE -ne 0) {
    throw "Installer build failed."
}

Write-Host "Installer output: $Root\dist\installer"
