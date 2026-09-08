param(
    [switch]$Force,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw "Current directory is not inside a Git repository."
}

Push-Location $repoRoot
try {
    $current = (& git config --local --get core.hooksPath 2>$null)
    if ($LASTEXITCODE -ne 0) {
        $current = $null
    }

    if ($Uninstall) {
        if ([string]::IsNullOrWhiteSpace($current)) {
            Write-Host "Local Git hooks are not configured."
            exit 0
        }
        if ($current -ne ".githooks" -and -not $Force) {
            throw "core.hooksPath is '$current', not '.githooks'. Use -Force only after confirming it may be removed."
        }
        & git config --local --unset core.hooksPath
        Write-Host "Local Git hook configuration removed."
        exit 0
    }

    if (-not (Test-Path ".githooks") -or -not (Test-Path "quality-gates.json")) {
        throw ".githooks or quality-gates.json is missing from repository root."
    }
    if (-not [string]::IsNullOrWhiteSpace($current) -and $current -ne ".githooks" -and -not $Force) {
        throw "core.hooksPath is already set to '$current'. Use -Force only after confirming it may be replaced."
    }

    & git config --local core.hooksPath .githooks
    Write-Host "Local Git hooks enabled:"
    Write-Host "  pre-commit  -> staged file checks"
    Write-Host "  commit-msg  -> commit message checks"
    Write-Host "  pre-push    -> branch and full local checks"
}
finally {
    Pop-Location
}
