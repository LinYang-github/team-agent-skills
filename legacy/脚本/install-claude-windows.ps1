param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RepoRoot  = Split-Path -Parent $PSScriptRoot
$SourceDir = Join-Path $RepoRoot "skills"
$TargetDir = (Join-Path $HOME ".claude\skills")

if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "skills directory not found: $SourceDir"
}

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Installed = 0
$Skipped   = 0

$SkillDirs = Get-ChildItem -LiteralPath $SourceDir -Directory | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") -PathType Leaf
}

foreach ($Skill in $SkillDirs) {
    $Name   = $Skill.Name
    $Target = Join-Path $TargetDir $Name

    if (Test-Path -LiteralPath $Target) {
        $Item = Get-Item -LiteralPath $Target -Force
        $ExistingTarget = $null

        if ($Item.LinkType -and $Item.Target) {
            $ExistingTarget = [string]($Item.Target | Select-Object -First 1)
        }

        if ($ExistingTarget) {
            try {
                $ResolvedExisting = [System.IO.Path]::GetFullPath($ExistingTarget)
                $ResolvedSource   = [System.IO.Path]::GetFullPath($Skill.FullName)
                if ($ResolvedExisting.TrimEnd('\\') -ieq $ResolvedSource.TrimEnd('\\')) {
                    Write-Host "[OK] $Name already linked"
                    $Skipped++
                    continue
                }
            } catch {}
        }

        if (-not $Force) {
            Write-Host "[SKIP] $Name already exists: $Target"
            Write-Host "       Re-run with -Force to back it up and replace it."
            $Skipped++
            continue
        }

        $Backup = "$Target.bak.$Timestamp"
        Move-Item -LiteralPath $Target -Destination $Backup
        Write-Host "[BACKUP] $Target -> $Backup"
    }

    New-Item -ItemType Junction -Path $Target -Target $Skill.FullName | Out-Null
    Write-Host "[LINK] $Name -> $Target"
    $Installed++
}

Write-Host ""
Write-Host "Claude Skill installation complete."
Write-Host "Source : $SourceDir"
Write-Host "Target : $TargetDir"
Write-Host "Linked : $Installed"
Write-Host "Skipped: $Skipped"
