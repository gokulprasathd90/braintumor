$files = @(
    "d:\PROJECT\braintumor\check_deps.ps1",
    "d:\PROJECT\braintumor\setup_env.ps1",
    "d:\PROJECT\braintumor\health_check.ps1",
    "d:\PROJECT\braintumor\run_backend_tests.ps1",
    "d:\PROJECT\braintumor\run_all_tests.ps1",
    "d:\PROJECT\braintumor\run_ai_tests.ps1"
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Remove-Item -Path $f -Force
        Write-Host "Removed: $f"
    }
}
Write-Host "Cleanup done."
