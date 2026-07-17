#Requires -Version 5.1
# ─── scripts/validate-env.ps1 ─────────────────────────────────────────────────
#
# Validates all environment files for completeness and security (Windows).
# Exit codes: 0 = pass, 1 = failure

[CmdletBinding()]
param(
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "development"
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Errors   = 0
$Warnings = 0

function Pass   ([string]$msg) { Write-Host "  ✓ $msg" -ForegroundColor Green  }
function Fail   ([string]$msg) { Write-Host "  ✗ $msg" -ForegroundColor Red; $script:Errors++ }
function Caution([string]$msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow; $script:Warnings++ }

function Test-FileExists ([string]$Path, [string]$Example = "") {
    if (Test-Path $Path) { Pass "File exists: $Path" }
    else { Fail "Missing: $Path$(if ($Example) { " (copy from $Example)" })" }
}

function Test-VarSet ([string]$File, [string]$Var, [bool]$Required = $true) {
    if (-not (Test-Path $File)) { return }
    $content = Get-Content $File -Raw
    if ($content -match "(?m)^${Var}=.+") { Pass "$Var is set" }
    elseif ($Required) { Fail "$Var is not set in $File" }
    else { Caution "$Var is not set (optional)" }
}

function Test-VarNotDefault ([string]$File, [string]$Var, [string]$Default) {
    if (-not (Test-Path $File)) { return }
    $content = Get-Content $File -Raw
    if ($content -match "(?m)^${Var}=${Default}") {
        Fail "$Var is still the default value — must be changed for $Environment"
    } else { Pass "$Var is not the default value" }
}

function Test-VarMinLength ([string]$File, [string]$Var, [int]$MinLen) {
    if (-not (Test-Path $File)) { return }
    $content = Get-Content $File -Raw
    if ($content -match "(?m)^${Var}=(.+)") {
        $val = $Matches[1].Trim()
        if ($val.Length -ge $MinLen) { Pass "$Var length OK ($($val.Length) chars)" }
        else { Fail "$Var is too short ($($val.Length) chars, minimum $MinLen)" }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Environment Validation — Brain Tumour Detection" -ForegroundColor Cyan
Write-Host "  Target: $Environment" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── AI Service ────────────────────────────────────────────────────────────────
Write-Host "── AI Service (.env) ────────────────────────────────────" -ForegroundColor Cyan
$AiEnv = Join-Path $RepoRoot "ai-service\.env"
Test-FileExists $AiEnv "ai-service/.env.example"

if (Test-Path $AiEnv) {
    foreach ($var in @("AI_SERVICE_HOST","AI_SERVICE_PORT","ACTIVE_MODEL","JWT_SECRET_KEY","CLASS_NAMES","LOG_LEVEL")) {
        Test-VarSet $AiEnv $var
    }
    if ($Environment -eq "production") {
        Test-VarNotDefault $AiEnv "JWT_SECRET_KEY" "change-me-in-production-use-a-long-random-secret"
        Test-VarMinLength  $AiEnv "JWT_SECRET_KEY" 32
        $aiContent = Get-Content $AiEnv -Raw
        if ($aiContent -match "(?m)^AI_SERVICE_DEBUG=true") { Fail "AI_SERVICE_DEBUG=true in production" }
        else { Pass "AI_SERVICE_DEBUG is not true" }
    }
}

Write-Host ""

# ── Backend ───────────────────────────────────────────────────────────────────
Write-Host "── Backend (.env) ────────────────────────────────────────" -ForegroundColor Cyan
$BeEnv = Join-Path $RepoRoot "backend\.env"
Test-FileExists $BeEnv "backend/.env.example"

if (Test-Path $BeEnv) {
    foreach ($var in @("PORT","NODE_ENV","AI_SERVICE_URL","FRONTEND_URL")) {
        Test-VarSet $BeEnv $var
    }
    if ($Environment -eq "production") {
        $beContent = Get-Content $BeEnv -Raw
        if ($beContent -match "(?m)^NODE_ENV=development") { Fail "NODE_ENV=development in production" }
        else { Pass "NODE_ENV is not development" }
    }
}

Write-Host ""

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($Errors -eq 0) {
    Write-Host "  ✓ Validation passed ($Warnings warning(s))" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  ✗ Validation FAILED: $Errors error(s), $Warnings warning(s)" -ForegroundColor Red
    exit 1
}
