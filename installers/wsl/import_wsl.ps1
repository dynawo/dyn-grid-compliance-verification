#Requires -Version 5.1
<#
.SYNOPSIS
    Imports the Dycov tool as a standalone WSL distribution and creates desktop/Start Menu shortcuts.

.DESCRIPTION
    This script imports dycov_rawimage.tar.gz as a WSL distribution named "DycovApp",
    then creates a desktop shortcut and a Start Menu entry that launch run_dycov_wsl.ps1.

    Must be run from the folder containing dycov_rawimage.tar.gz and run_dycov_wsl.ps1.

.NOTES
    (c) RTE - Grupo AIA
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

###############################################################################
# Config
###############################################################################

$DistroName   = "DycovApp"
$InstallRoot  = "C:\DycovApp"
$ImageFile    = "dycov_rawimage.tar.gz"
$RunScript    = "run_dycov_wsl.ps1"
$ShortcutName = "Dycov"

###############################################################################
# Helpers
###############################################################################

function Write-Step { param([string]$msg) Write-Host "`n==> $msg" -ForegroundColor Green }
function Write-Info { param([string]$msg) Write-Host "    $msg" -ForegroundColor Cyan }
function Write-Fail { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red }

function Exit-WithPause {
    param([string]$message, [int]$code = 1)
    Write-Fail $message
    Write-Host "`nPress any key to close..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit $code
}

###############################################################################
# Step 0 — Verify required files are present
###############################################################################

Write-Step "Verifying required files..."

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$ImagePath = Join-Path $ScriptDir $ImageFile
$RunScriptPath = Join-Path $ScriptDir $RunScript

if (-not (Test-Path $ImagePath)) {
    Exit-WithPause "Required file not found: $ImageFile`nMake sure it is in the same folder as this script."
}

if (-not (Test-Path $RunScriptPath)) {
    Exit-WithPause "Required file not found: $RunScript`nMake sure it is in the same folder as this script."
}

Write-Info "All required files found."

###############################################################################
# Step 1 — Check WSL is available
###############################################################################

Write-Step "Checking WSL availability..."

try {
    $null = & wsl --status 2>&1
} catch {
    Exit-WithPause "WSL is not available on this system. Please enable it first:`n  https://learn.microsoft.com/en-us/windows/wsl/install"
}

Write-Info "WSL is available."

###############################################################################
# Step 2 — Check if distro already exists
###############################################################################

Write-Step "Checking for existing '$DistroName' distribution..."

$existingDistros = & wsl --list --quiet 2>&1
# WSL outputs UTF-16 with null bytes; normalize to plain strings
$existingDistros = $existingDistros | ForEach-Object { "$_".Trim("`0").Trim() } | Where-Object { $_ -ne "" }

if ($existingDistros -contains $DistroName) {
    Write-Host "`nWARNING: A WSL distribution named '$DistroName' already exists." -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove it and reinstall? [y/N]"
    if ($response -notmatch '^[yY]') {
        Exit-WithPause "Installation cancelled by user." 0
    }

    Write-Info "Removing existing distribution..."
    & wsl --unregister $DistroName | Out-Null
    Write-Info "Existing distribution removed."
}

###############################################################################
# Step 3 — Import the distribution
###############################################################################

Write-Step "Importing '$DistroName' from $ImageFile..."
Write-Info "Install location: $InstallRoot"
Write-Info "This may take a few minutes..."

if (Test-Path $InstallRoot) {
    Remove-Item -Recurse -Force $InstallRoot
}
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

& wsl --import $DistroName $InstallRoot $ImagePath

if ($LASTEXITCODE -ne 0) {
    Exit-WithPause "WSL import failed with exit code $LASTEXITCODE."
}

Write-Info "Distribution imported successfully."

###############################################################################
# Step 4 — Create desktop shortcut
###############################################################################

Write-Step "Creating shortcuts..."

$WshShell    = New-Object -ComObject WScript.Shell
$PwshCmd = Get-Command pwsh -ErrorAction SilentlyContinue
if ($PwshCmd) {
    $PwshExe = $PwshCmd.Source
} else {
    $PwshExe = (Get-Command powershell).Source
}

$ShortcutArgs = "-NonInteractive -NoProfile -ExecutionPolicy Bypass -File `"$RunScriptPath`""

# Desktop shortcut
$DesktopPath    = [Environment]::GetFolderPath("Desktop")
$DesktopLnk     = Join-Path $DesktopPath "$ShortcutName.lnk"
$DesktopShortcut = $WshShell.CreateShortcut($DesktopLnk)
$DesktopShortcut.TargetPath       = $PwshExe
$DesktopShortcut.Arguments        = $ShortcutArgs
$DesktopShortcut.WorkingDirectory = $ScriptDir
$DesktopShortcut.Description      = "Launch the Dycov simulation tool"
$DesktopShortcut.Save()
Write-Info "Desktop shortcut created: $DesktopLnk"

# Start Menu shortcut
$StartMenuPath    = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs"
$StartMenuLnk     = Join-Path $StartMenuPath "$ShortcutName.lnk"
$StartMenuShortcut = $WshShell.CreateShortcut($StartMenuLnk)
$StartMenuShortcut.TargetPath       = $PwshExe
$StartMenuShortcut.Arguments        = $ShortcutArgs
$StartMenuShortcut.WorkingDirectory = $ScriptDir
$StartMenuShortcut.Description      = "Launch the Dycov simulation tool"
$StartMenuShortcut.Save()
Write-Info "Start Menu shortcut created: $StartMenuLnk"

###############################################################################
# Summary
###############################################################################

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Dycov installed successfully as WSL distribution '$DistroName'" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To launch Dycov:" -ForegroundColor Cyan
Write-Host "    - Double-click the '$ShortcutName' shortcut on your Desktop" -ForegroundColor Cyan
Write-Host "    - Or find it in the Start Menu" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to close..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
