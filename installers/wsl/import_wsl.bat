@echo off
:: Bootstrap launcher for import_wsl.ps1
:: Double-click this file to install Dycov.
:: This bypasses PowerShell's execution policy restriction for unsigned scripts.

powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -File "%~dp0import_wsl.ps1"
