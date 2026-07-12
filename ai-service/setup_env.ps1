# PowerShell — create and activate the Python virtual environment
# Run from the ai-service/ directory:
#   .\setup_env.ps1

$ErrorActionPreference = "Stop"

$VenvDir = ".venv"
$PythonVersion = "3.12"

Write-Host "Brain Tumour Detection — AI Service environment setup" -ForegroundColor Cyan
Write-Host ""

# Prefer py launcher for the pinned Python version
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyList = py -0p 2>&1 | Out-String
    if ($pyList -match "3\.12") {
        $pythonCmd = "py -3.12"
    } elseif ($pyList -match "3\.13") {
        Write-Warning "Python 3.12 not found. Falling back to Python 3.13 (requires TensorFlow >= 2.20)."
        $pythonCmd = "py -3.13"
    }
}

if (-not $pythonCmd) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } else {
        Write-Error "Python not found. Install Python 3.12+ from https://www.python.org/downloads/"
        exit 1
    }
}

if (Test-Path $VenvDir) {
    Write-Host "Virtual environment '$VenvDir' already exists — skipping creation." -ForegroundColor Yellow
} else {
    Write-Host "Creating virtual environment in '$VenvDir' using $pythonCmd ..."
    Invoke-Expression "$pythonCmd -m venv $VenvDir"
    Write-Host "Virtual environment created." -ForegroundColor Green
}

Write-Host ""
Write-Host "Activate the environment:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Then install dependencies:" -ForegroundColor Cyan
Write-Host "  pip install --upgrade pip"
Write-Host "  pip install -r requirements.txt"
Write-Host ""
Write-Host "Start the server:" -ForegroundColor Cyan
Write-Host "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
