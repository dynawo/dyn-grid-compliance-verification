#Requires -Version 5.1
<#
.SYNOPSIS
    Launches the Dycov tool inside the DycovApp WSL distribution.

.DESCRIPTION
    Equivalent to run_dycov_docker.sh for Linux/Docker users.

    Checks that the DycovApp WSL distribution is installed and launches it.
    No working directory mapping is needed: WSL mounts the host drives
    automatically under /mnt/c/, /mnt/d/, etc.

.NOTES
    (c) RTE - Grupo AIA
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

###############################################################################
# Config
###############################################################################

$DistroName = "DycovApp"

###############################################################################
# Helpers
###############################################################################

function Write-Fail { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red }

function Exit-WithPause {
    param([string]$message, [int]$code = 1)
    Write-Fail $message
    Write-Host "`nPress any key to close..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit $code
}

###############################################################################
# Step 1 — Check the distribution exists
###############################################################################

$existingDistros = & wsl --list --quiet 2>&1
$existingDistros = $existingDistros | ForEach-Object { "$_".Trim("`0").Trim() } | Where-Object { $_ -ne "" }

if ($existingDistros -notcontains $DistroName) {
    Exit-WithPause "'$DistroName' WSL distribution not found.`nPlease run import_wsl.bat first."
}

###############################################################################
# Step 2 — Launch the distribution
###############################################################################

Write-Host "`nLaunching Dycov..." -ForegroundColor Green
Write-Host ""

& wsl -d $DistroName -- bash /start_dycov.sh