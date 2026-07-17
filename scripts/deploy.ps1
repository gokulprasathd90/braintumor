#Requires -Version 5.1
# ─── scripts/deploy.ps1 ───────────────────────────────────────────────────────
#
# Production deployment script for Brain Tumour Detection (Windows / PowerShell).
#
# Usage:
#   .\scripts\deploy.ps1 [OPTIONS]
#
# Parameters:
#   -Environment   staging | production  (default: staging)
#   -Version       image tag to deploy   (default: latest)
#   -NoPull        skip docker image pull
#   -Build         build images locally before deploying
#   -Rollback      roll back to the previous version
#   -Status        show current deployment status and exit
#
# Examples:
#   .\scripts\deploy.ps1 -Environment staging
#   .\scripts\deploy.ps1 -Environment production -Version v1.2.3
#   .\scripts\deploy.ps1 -Build
#   .\scripts\deploy.ps1 -Rollback
#   .\scripts\deploy.ps1 -Status

[CmdletBinding()]
param(
    [ValidateSet("staging", "production")]
    [string]$Environment = "staging",

    [string]$Version = "latest",

    [switch]$NoPull,
    [switch]$Build,
    [switch]$Rollback,
    [switch]$Status
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ─────────────────────────────────────────────────────────────────────
$RepoRoot    = Split-Path -Parent $PSScriptRoot
$ComposeBase = Join-Path $RepoRoot "docker\docker-compose.yml"
$ComposeProd = Join-Path $RepoRoot "docker\docker-compose.prod.yml"
$BackupDir   = Join-Path $RepoRoot ".backups"
$LogDir      = Join-Path $RepoRoot "logs"
$LogFile     = Join-Path $LogDir "deploy-$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir    | Out-Null

# ── Logging helpers ───────────────────────────────────────────────────────────
function Write-Log {
    param([string]$Level, [string]$Message, [System.ConsoleColor]$Color = "White")
    $ts      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry   = "[$ts] [$Level] $Message"
    Write-Host $entry -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $entry
}

function Info    ([string]$msg) { Write-Log "INFO " $msg Cyan    }
function Success ([string]$msg) { Write-Log "OK   " $msg Green   }
function Warn    ([string]$msg) { Write-Log "WARN " $msg Yellow  }
function Err     ([string]$msg) { Write-Log "ERROR" $msg Red     }
function Die     ([string]$msg) { Err $msg; exit 1 }

# ── Header ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Brain Tumour Detection — Deployment Script (Windows)" -ForegroundColor Cyan
Write-Host "  Environment : $Environment"                           -ForegroundColor Cyan
Write-Host "  Version     : $Version"                               -ForegroundColor Cyan
Write-Host "  Timestamp   : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') UTC" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Status mode ───────────────────────────────────────────────────────────────
if ($Status) {
    Info "Current container status:"
    docker compose -f $ComposeBase -f $ComposeProd ps
    exit 0
}

# ── Prerequisites ─────────────────────────────────────────────────────────────
function Test-Prerequisites {
    Info "Checking prerequisites..."
    $missing = @()
    foreach ($cmd in @("docker", "curl")) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            $missing += $cmd
        }
    }
    if ($missing.Count -gt 0) {
        Die "Missing required commands: $($missing -join ', ')"
    }
    & docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Docker daemon is not running" }
    Success "All prerequisites met"
}

# ── Environment file validation ───────────────────────────────────────────────
function Test-EnvFiles {
    Info "Validating environment files..."
    $missing = 0
    foreach ($f in @(
        (Join-Path $RepoRoot "ai-service\.env"),
        (Join-Path $RepoRoot "backend\.env")
    )) {
        if (-not (Test-Path $f)) {
            Err "Missing: $f — copy from .env.example and configure"
            $missing++
        }
    }
    if ($missing -gt 0) { Die "$missing environment file(s) missing." }

    if ($Environment -eq "production") {
        $aiEnv = Get-Content (Join-Path $RepoRoot "ai-service\.env") -Raw
        if ($aiEnv -match 'JWT_SECRET_KEY=change-me') {
            Die "JWT_SECRET_KEY is still the default value. Set a strong secret before production deployment."
        }
    }
    Success "Environment files OK"
}

# ── Backup ────────────────────────────────────────────────────────────────────
function New-Backup {
    Info "Creating pre-deployment backup..."
    $tag        = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $BackupDir "${Environment}_${tag}"
    New-Item -ItemType Directory -Force -Path $backupPath | Out-Null

    docker compose -f $ComposeBase -f $ComposeProd images --format json `
        > (Join-Path $backupPath "image_list.json") 2>$null

    $Version | Set-Content (Join-Path $backupPath "version.txt")
    Success "Backup saved to $backupPath"
}

# ── Build images ──────────────────────────────────────────────────────────────
function Invoke-Build {
    Info "Building Docker images (version: $Version)..."
    $gitHash = (& git rev-parse --short HEAD 2>$null) ?? "unknown"
    & docker compose -f $ComposeBase -f $ComposeProd build `
        --build-arg "VERSION=$Version" `
        --build-arg "BUILD_DATE=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" `
        --build-arg "GIT_COMMIT=$gitHash"
    if ($LASTEXITCODE -ne 0) { Die "Docker build failed" }
    Success "Images built"
}

# ── Pull images ───────────────────────────────────────────────────────────────
function Invoke-Pull {
    if ($NoPull) { Warn "Skipping image pull (-NoPull specified)"; return }
    Info "Pulling images (version: $Version)..."
    $env:APP_VERSION = $Version
    & docker compose -f $ComposeBase -f $ComposeProd pull
    if ($LASTEXITCODE -ne 0) { Warn "Pull failed — continuing with local images" }
}

# ── Deploy ────────────────────────────────────────────────────────────────────
function Invoke-Deploy {
    Info "Starting deployment..."
    $env:APP_VERSION = $Version
    & docker compose -f $ComposeBase -f $ComposeProd up `
        --detach `
        --no-build `
        --remove-orphans `
        --wait `
        --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { Die "docker compose up failed" }
    Success "Containers started"
}

# ── Smoke tests ───────────────────────────────────────────────────────────────
function Invoke-SmokeTests {
    Info "Running smoke tests..."
    $aiPort = $env:AI_SERVICE_PORT ?? "8000"
    $maxRetries = 12
    $waitSecs   = 5

    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $response = Invoke-RestMethod "http://localhost:${aiPort}/api/v1/health" -TimeoutSec 5
            if ($response.status -eq "ok") {
                Success "AI service health check passed"
                return
            }
        } catch { }
        if ($i -eq $maxRetries) {
            Err "AI service health check failed after $($maxRetries * $waitSecs)s"
            & docker compose -f $ComposeBase logs --tail=50 ai-service
            Die "Deployment smoke test failed"
        }
        Info "  Waiting for AI service... ($i/$maxRetries)"
        Start-Sleep -Seconds $waitSecs
    }
}

# ── Rollback ──────────────────────────────────────────────────────────────────
function Invoke-Rollback {
    Info "Rolling back deployment..."
    $backups = Get-ChildItem $BackupDir -Directory |
        Where-Object { $_.Name -like "${Environment}_*" } |
        Sort-Object LastWriteTime -Descending

    if ($backups.Count -eq 0) { Die "No backup found for environment '$Environment'" }
    $latest = $backups[0]

    $rollbackVersion = Get-Content (Join-Path $latest.FullName "version.txt") -ErrorAction SilentlyContinue
    $rollbackVersion = $rollbackVersion ?? "previous"

    Warn "Rolling back to version: $rollbackVersion"
    $env:APP_VERSION = $rollbackVersion

    & docker compose -f $ComposeBase -f $ComposeProd up --detach --no-build --remove-orphans
    if ($LASTEXITCODE -ne 0) { Die "Rollback failed" }
    Success "Rollback to $rollbackVersion complete"
}

# ── Cleanup ───────────────────────────────────────────────────────────────────
function Invoke-Cleanup {
    Info "Pruning old images..."
    & docker image prune -f --filter "until=72h" | Out-Null
}

# ── Main ─────────────────────────────────────────────────────────────────────
if ($Rollback) {
    Test-Prerequisites
    Invoke-Rollback
    Invoke-SmokeTests
    exit 0
}

Test-Prerequisites
Test-EnvFiles
New-Backup

if ($Build) { Invoke-Build } else { Invoke-Pull }

Invoke-Deploy
Invoke-SmokeTests
Invoke-Cleanup

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "  Version     : $Version" -ForegroundColor Green
Write-Host "  Environment : $Environment" -ForegroundColor Green
Write-Host "  Frontend    : http://localhost:$($env:FRONTEND_PORT ?? '3000')" -ForegroundColor Green
Write-Host "  Backend     : http://localhost:$($env:BACKEND_PORT ?? '5000')" -ForegroundColor Green
Write-Host "  AI Service  : http://localhost:$($env:AI_SERVICE_PORT ?? '8000')" -ForegroundColor Green
Write-Host "  Log file    : $LogFile" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
