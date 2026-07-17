#Requires -Version 5.1
<#
.SYNOPSIS
    Brain Tumour Detection — Release Packager (Windows PowerShell)

.DESCRIPTION
    Builds a distributable release archive containing all source code,
    documentation, scripts, and metadata. Generates a release_manifest.json
    describing the contents and checksums.

    This is the Windows equivalent of scripts/package_release.sh.

.PARAMETER Version
    Version string to use (e.g., "1.0.0"). Defaults to the content of the
    VERSION file in the repository root.

.PARAMETER OutputDir
    Directory where the archive and manifest will be written. Default: .\dist

.PARAMETER Format
    Archive format: "zip" or "tar.gz". Default: "zip"
    (zip is native on Windows; tar.gz requires tar.exe, available in Win 10+)

.PARAMETER SkipTests
    Skip test verification before packaging.

.PARAMETER SkipBuild
    Skip the frontend production build step.

.PARAMETER DryRun
    Print what would be done without making any changes.

.EXAMPLE
    .\scripts\package_release.ps1

.EXAMPLE
    .\scripts\package_release.ps1 -Version "1.2.0" -OutputDir ".\releases"

.EXAMPLE
    .\scripts\package_release.ps1 -Format "zip" -SkipTests -DryRun
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $Version    = "",
    [string] $OutputDir  = "",
    [ValidateSet("zip", "tar.gz")]
    [string] $Format     = "zip",
    [switch] $SkipTests,
    [switch] $SkipBuild,
    [switch] $DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ─────────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir    = Split-Path -Parent $ScriptDir
$VersionFile = Join-Path $RootDir "VERSION"

if ([string]::IsNullOrEmpty($OutputDir)) {
    $OutputDir = Join-Path $RootDir "dist"
}

# ── Logging helpers ───────────────────────────────────────────────────────────
function Write-Info    { param($Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-Success { param($Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn    { param($Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-Step    { param($Msg) Write-Host "`n>> $Msg" -ForegroundColor Cyan }
function Write-DryRun  { param($Msg) Write-Host "[DRY-RUN] Would run: $Msg" -ForegroundColor Yellow }

# ── Resolve version ───────────────────────────────────────────────────────────
if ([string]::IsNullOrEmpty($Version)) {
    if (Test-Path $VersionFile) {
        $Version = (Get-Content $VersionFile -Raw).Trim()
    } else {
        Write-Err "VERSION file not found at $VersionFile. Use -Version to specify."
        exit 1
    }
}

if ($Version -notmatch '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
    Write-Err "Invalid version format: '$Version'. Expected semver (e.g., 1.0.0)."
    exit 1
}

# ── Derived names ─────────────────────────────────────────────────────────────
$PackageName  = "brain-tumor-detection-v$Version"
$StagingDir   = Join-Path $OutputDir $PackageName
$BuildDate    = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$ReleaseDate  = (Get-Date -Format "yyyy-MM-dd")

try {
    $GitCommit = (git -C $RootDir rev-parse --short HEAD 2>$null)
    $GitBranch = (git -C $RootDir rev-parse --abbrev-ref HEAD 2>$null)
} catch {
    $GitCommit = "unknown"
    $GitBranch = "unknown"
}

# ── Header ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        Brain Tumour Detection — Release Packager         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Info "Version    : $Version"
Write-Info "Package    : $PackageName"
Write-Info "Format     : $Format"
Write-Info "Output dir : $OutputDir"
Write-Info "Git commit : $GitCommit ($GitBranch)"
Write-Info "Build date : $BuildDate"
if ($DryRun) { Write-Warn "DRY-RUN mode — no files will be modified" }
Write-Host ""

# ── Step 1: Run tests ─────────────────────────────────────────────────────────
Write-Step "Step 1/7 — Test verification"

if ($SkipTests) {
    Write-Warn "Tests skipped (-SkipTests)"
} else {
    Write-Info "Running AI service tests..."
    $VenvActivate = Join-Path $RootDir "ai-service\.venv\Scripts\Activate.ps1"
    if ($DryRun) {
        Write-DryRun "cd ai-service; .venv\Scripts\Activate.ps1; pytest -v --tb=short -q"
    } elseif (Test-Path $VenvActivate) {
        Push-Location (Join-Path $RootDir "ai-service")
        try {
            & $VenvActivate
            $result = & python -m pytest -v --tb=short -q 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Err "AI service tests failed. Fix failures before packaging."
                exit 1
            }
            Write-Success "AI service tests passed"
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "AI service venv not found — skipping Python tests"
    }

    Write-Info "Running backend tests..."
    $BackendModules = Join-Path $RootDir "backend\node_modules"
    if ($DryRun) {
        Write-DryRun "cd backend; npm test -- --runInBand"
    } elseif (Test-Path $BackendModules) {
        Push-Location (Join-Path $RootDir "backend")
        try {
            npm test -- --runInBand --passWithNoTests
            if ($LASTEXITCODE -ne 0) {
                Write-Err "Backend tests failed. Fix failures before packaging."
                exit 1
            }
            Write-Success "Backend tests passed"
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "backend\node_modules not found — skipping backend tests"
    }
}

# ── Step 2: Build frontend ────────────────────────────────────────────────────
Write-Step "Step 2/7 — Frontend production build"

if ($SkipBuild) {
    Write-Warn "Frontend build skipped (-SkipBuild)"
} else {
    $FrontendModules = Join-Path $RootDir "frontend\node_modules"
    if ($DryRun) {
        Write-DryRun "cd frontend; npm run build"
    } elseif (Test-Path $FrontendModules) {
        Write-Info "Building React application..."
        Push-Location (Join-Path $RootDir "frontend")
        try {
            npm run build
            if ($LASTEXITCODE -ne 0) {
                Write-Err "Frontend build failed."
                exit 1
            }
            Write-Success "Frontend built → frontend\dist\"
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "frontend\node_modules not found — skipping frontend build"
    }
}

# ── Step 3: Prepare staging directory ────────────────────────────────────────
Write-Step "Step 3/7 — Staging release files"

# Items to include in the release package
$IncludeItems = @(
    "ai-service\app",
    "ai-service\tests",
    "ai-service\requirements.txt",
    "ai-service\Dockerfile",
    "ai-service\.env.example",
    "ai-service\.env.production",
    "ai-service\.python-version",
    "backend\api",
    "backend\database",
    "backend\middleware",
    "backend\pipeline",
    "backend\server.js",
    "backend\package.json",
    "backend\package-lock.json",
    "backend\.env.example",
    "backend\Dockerfile",
    "frontend\src",
    "frontend\public",
    "frontend\package.json",
    "frontend\package-lock.json",
    "frontend\vite.config.ts",
    "frontend\tsconfig.json",
    "frontend\.env.example",
    "frontend\Dockerfile",
    "docker",
    "docs",
    "scripts",
    ".github",
    "Makefile",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "RELEASE_CHECKLIST.md",
    "LICENSE",
    "VERSION",
    ".pre-commit-config.yaml",
    ".gitignore"
)

# Also include frontend/dist if it exists
$FrontendDist = Join-Path $RootDir "frontend\dist"
if (Test-Path $FrontendDist) {
    $IncludeItems += "frontend\dist"
}

if ($DryRun) {
    Write-DryRun "mkdir $StagingDir"
    Write-DryRun "Copy $($IncludeItems.Count) items to staging"
} else {
    if (Test-Path $StagingDir) { Remove-Item $StagingDir -Recurse -Force }
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

    foreach ($item in $IncludeItems) {
        $src = Join-Path $RootDir $item
        $dst = Join-Path $StagingDir $item
        if (Test-Path $src) {
            $dstParent = Split-Path -Parent $dst
            if (-not (Test-Path $dstParent)) {
                New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
            }
            Copy-Item $src $dst -Recurse -Force
        } else {
            Write-Warn "Skipping missing item: $item"
        }
    }

    $totalFiles = (Get-ChildItem $StagingDir -Recurse -File).Count
    Write-Success "Staged $totalFiles files to $StagingDir"
}

# ── Step 4: Generate release manifest ────────────────────────────────────────
Write-Step "Step 4/7 — Generating release manifest"

$ManifestFile = Join-Path $RootDir "release_manifest.json"

if ($DryRun) {
    Write-DryRun "Generate $ManifestFile"
} else {
    $aiFiles  = if (Test-Path (Join-Path $StagingDir "ai-service")) { (Get-ChildItem (Join-Path $StagingDir "ai-service") -Recurse -File).Count } else { 0 }
    $beFiles  = if (Test-Path (Join-Path $StagingDir "backend"))    { (Get-ChildItem (Join-Path $StagingDir "backend")    -Recurse -File).Count } else { 0 }
    $feFiles  = if (Test-Path (Join-Path $StagingDir "frontend"))   { (Get-ChildItem (Join-Path $StagingDir "frontend")   -Recurse -File).Count } else { 0 }
    $docFiles = if (Test-Path (Join-Path $StagingDir "docs"))       { (Get-ChildItem (Join-Path $StagingDir "docs")       -Recurse -File).Count } else { 0 }
    $totalFilesManifest = (Get-ChildItem $StagingDir -Recurse -File).Count

    $manifest = [ordered]@{
        project         = "Brain Tumour Detection"
        version         = $Version
        release_date    = $ReleaseDate
        build_timestamp = $BuildDate
        git_commit      = $GitCommit
        git_branch      = $GitBranch
        package_name    = $PackageName
        archive_format  = $Format
        components      = [ordered]@{
            ai_service  = [ordered]@{ language = "Python";     framework = "FastAPI + TensorFlow"; python_version = "3.12";    files = $aiFiles  }
            backend     = [ordered]@{ language = "JavaScript"; framework = "Node.js + Express";    node_version   = "20 LTS";  files = $beFiles  }
            frontend    = [ordered]@{ language = "TypeScript"; framework = "React 18 + Vite 5";    files = $feFiles }
            documentation = [ordered]@{ files = $docFiles }
        }
        total_files     = $totalFilesManifest
        checksums       = @{}
        release_type    = "stable"
        license         = "MIT"
        repository      = "https://github.com/your-org/brain-tumor-detection"
        docker_images   = @(
            "ghcr.io/your-org/brain-tumor-detection/ai-service:$Version",
            "ghcr.io/your-org/brain-tumor-detection/backend:$Version",
            "ghcr.io/your-org/brain-tumor-detection/frontend:$Version"
        )
    }

    $manifest | ConvertTo-Json -Depth 10 | Set-Content $ManifestFile -Encoding UTF8
    Copy-Item $ManifestFile (Join-Path $StagingDir "release_manifest.json") -Force
    Write-Success "Manifest written to $ManifestFile"
}

# ── Step 5: Create archive ────────────────────────────────────────────────────
Write-Step "Step 5/7 — Creating release archive"

$ArchiveBase = Join-Path $OutputDir $PackageName

if ($DryRun) {
    Write-DryRun "Create $ArchiveBase.$Format"
} else {
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    if ($Format -eq "zip") {
        $ArchiveFile = "$ArchiveBase.zip"
        Push-Location $OutputDir
        Compress-Archive -Path $PackageName -DestinationPath $ArchiveFile -Force
        Pop-Location
    } else {
        # tar.gz — requires tar.exe (available in Windows 10 1803+)
        $ArchiveFile = "$ArchiveBase.tar.gz"
        Push-Location $OutputDir
        tar -czf $ArchiveFile $PackageName
        if ($LASTEXITCODE -ne 0) {
            Write-Err "tar.exe failed. Ensure Windows 10 build 17063+ or install tar."
            exit 1
        }
        Pop-Location
    }

    $archiveSize = [math]::Round((Get-Item $ArchiveFile).Length / 1MB, 2)
    Write-Success "Archive created: $(Split-Path -Leaf $ArchiveFile) (${archiveSize} MB)"
}

# ── Step 6: Compute checksum ──────────────────────────────────────────────────
Write-Step "Step 6/7 — Computing checksums"

$ChecksumFile = "$ArchiveBase.sha256"

if ($DryRun) {
    Write-DryRun "Get-FileHash $ArchiveFile -Algorithm SHA256 > $ChecksumFile"
} else {
    $hash = (Get-FileHash $ArchiveFile -Algorithm SHA256).Hash.ToLower()
    "$hash  $(Split-Path -Leaf $ArchiveFile)" | Set-Content $ChecksumFile -Encoding UTF8

    Write-Success "SHA-256: $hash"

    # Embed checksum back into manifest
    $manifestData = Get-Content $ManifestFile -Raw | ConvertFrom-Json
    $manifestData.checksums | Add-Member -MemberType NoteProperty -Name "sha256" -Value $hash -Force
    $manifestData | ConvertTo-Json -Depth 10 | Set-Content $ManifestFile -Encoding UTF8
}

# ── Step 7: Cleanup staging ───────────────────────────────────────────────────
Write-Step "Step 7/7 — Cleanup"

if ($DryRun) {
    Write-DryRun "Remove-Item $StagingDir -Recurse -Force"
} else {
    Remove-Item $StagingDir -Recurse -Force
    Write-Success "Staging directory removed"
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                Release Package Complete                 ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

if (-not $DryRun) {
    Write-Info "Archive  : $ArchiveFile"
    if (Test-Path $ChecksumFile) { Write-Info "Checksum : $ChecksumFile" }
    Write-Info "Manifest : $ManifestFile"
}

Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Verify archive contents"
Write-Host "  2. Create a GitHub release and attach the archive and manifest"
Write-Host "  3. Push the version tag:"
Write-Host "       git tag -a v$Version -m `"Release v$Version`""
Write-Host "       git push origin v$Version"
Write-Host ""
