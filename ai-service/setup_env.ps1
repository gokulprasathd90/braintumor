# setup_env.ps1 — Bootstrap the Python virtual environment for the AI service.
#
# Run from the ai-service/ directory:
#   .\setup_env.ps1
#
# What this script does:
#   1. Locates Python 3.12 (falls back to 3.10+)
#   2. Creates a .venv virtual environment if one does not exist
#   3. Upgrades pip, setuptools, and wheel inside the venv
#   4. Installs all pinned dependencies from requirements.txt
#   5. Copies .env.example → .env if no .env exists yet
#   6. Prints the commands to activate and run the server

$ErrorActionPreference = "Stop"

$VenvDir    = ".venv"
$ReqFile    = "requirements.txt"
$EnvExample = ".env.example"
$EnvFile    = ".env"

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "  → $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Fatal { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Brain Tumour Detection — AI Service Setup" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

# ── 1. Locate Python ──────────────────────────────────────────────────────────
Write-Step "Locating Python 3.12..."

$pythonExe = $null

# Try the py launcher first (Windows-standard)
if (Get-Command py -ErrorAction SilentlyContinue) {
    $versions = @("3.12", "3.13", "3.11", "3.10")
    foreach ($v in $versions) {
        $test = py "-$v" -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "py -$v"
            Write-Ok "Found Python $v via py launcher"
            break
        }
    }
}

# Fall back to python/python3 on PATH
if (-not $pythonExe) {
    foreach ($cmd in @("python", "python3")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $ver = & $cmd -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and [version]$ver -ge [version]"3.10") {
                $pythonExe = $cmd
                Write-Ok "Found Python $ver at '$cmd'"
                break
            }
        }
    }
}

if (-not $pythonExe) {
    Write-Fatal "Python 3.10+ not found. Install from https://www.python.org/downloads/ and ensure it is on PATH."
}

# ── 2. Create virtual environment ─────────────────────────────────────────────
Write-Step "Setting up virtual environment..."

if (Test-Path $VenvDir) {
    Write-Ok "Virtual environment '$VenvDir' already exists — skipping creation"
} else {
    Invoke-Expression "$pythonExe -m venv $VenvDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Fatal "Failed to create virtual environment."
    }
    Write-Ok "Virtual environment created at '$VenvDir'"
}

# Resolve the venv Python and pip executables
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$venvPip    = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Fatal "Virtual environment Python not found at '$venvPython'. Delete '$VenvDir' and re-run."
}

# ── 3. Upgrade pip, setuptools, wheel ─────────────────────────────────────────
Write-Step "Upgrading pip, setuptools, and wheel..."
& $venvPip install --quiet --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { Write-Fatal "pip upgrade failed." }
Write-Ok "pip upgraded"

# ── 4. Install dependencies ────────────────────────────────────────────────────
if (-not (Test-Path $ReqFile)) {
    Write-Fatal "'$ReqFile' not found. Run this script from the ai-service/ directory."
}

Write-Step "Installing dependencies from '$ReqFile' (this may take a few minutes)..."
& $venvPip install --quiet -r $ReqFile
if ($LASTEXITCODE -ne 0) { Write-Fatal "Dependency installation failed." }
Write-Ok "All dependencies installed"

# ── 5. Copy .env.example → .env ───────────────────────────────────────────────
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Ok "Created '$EnvFile' from '$EnvExample' — edit it before starting the server"
    } else {
        Write-Warn "'$EnvExample' not found — skipping .env creation"
    }
} else {
    Write-Ok "'$EnvFile' already exists — keeping existing configuration"
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Activate the environment:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  Run the development server:" -ForegroundColor Cyan
Write-Host "    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host ""
Write-Host "  Run tests:" -ForegroundColor Cyan
Write-Host "    pytest"
Write-Host ""
