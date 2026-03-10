$ErrorActionPreference = 'Stop'

# Build readcode.exe using PyInstaller.
# Run from repo root: powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

python -m pip install --upgrade pip
python -m pip install pyinstaller

# Clean previous builds
if (Test-Path .\build) { Remove-Item -Recurse -Force .\build }
if (Test-Path .\dist) { Remove-Item -Recurse -Force .\dist }

pyinstaller --onefile --name readcode run.py

Write-Host "Built: dist\\readcode.exe"
