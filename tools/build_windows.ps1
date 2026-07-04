param(
    [switch]$InstallBuildDeps,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Spec = Join-Path $Root "packaging\SmartVoice.spec"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Create it with: python -m venv .venv"
}

Set-Location $Root

if ($InstallBuildDeps) {
    & $Python -m pip install -r Requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install build dependencies."
    }
}

& $Python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Run: .\tools\build_windows.ps1 -InstallBuildDeps"
}

if (-not $SkipTests) {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed. Build stopped."
    }
}

foreach ($RelativePath in @("build", "dist\SmartVoice")) {
    $Target = Join-Path $Root $RelativePath
    if (Test-Path $Target) {
        $Resolved = Resolve-Path $Target
        if (-not $Resolved.Path.StartsWith($Root)) {
            throw "Refusing to remove path outside project: $Resolved"
        }
        Remove-Item -LiteralPath $Resolved.Path -Recurse -Force
    }
}

& $Python -m PyInstaller $Spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$Exe = Join-Path $Root "dist\SmartVoice\SmartVoice.exe"
if (-not (Test-Path $Exe)) {
    throw "Build completed but SmartVoice.exe was not found."
}

Write-Host "Built: $Exe"
