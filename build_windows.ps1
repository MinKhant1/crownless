# Build dist\Crownless.exe. Run from the project folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}
$python = ".venv\Scripts\python.exe"
& $python -m pip install --disable-pip-version-check -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
& $python -m PyInstaller --noconfirm --clean crownless.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Write-Host "Done: dist\Crownless.exe"
