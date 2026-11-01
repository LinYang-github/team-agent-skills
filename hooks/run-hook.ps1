param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('agent-command', 'session-start')]
    [string]$HookName
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $OutputEncoding

$candidates = @(
    'C:\Program Files\Git\bin\bash.exe'
    'C:\Program Files (x86)\Git\bin\bash.exe'
)
if ($env:LOCALAPPDATA) {
    $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe'
}
$blockedDirectories = @(
    (Join-Path $env:SystemRoot 'System32')
    (Join-Path $env:SystemRoot 'Sysnative')
)
if ($env:LOCALAPPDATA) {
    $blockedDirectories += Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
}
$candidates += @(Get-Command bash.exe -CommandType Application -All -ErrorAction SilentlyContinue |
    Where-Object { (Split-Path $_.Source -Parent) -notin $blockedDirectories } |
    Select-Object -ExpandProperty Source)

$bash = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $bash) {
    [Console]::Error.WriteLine('Git Bash was not found. Install Git for Windows and check the bash path.')
    exit 1
}

# Explicit UTF-8 streams also work in Windows PowerShell 5.1, whose native
# pipeline defaults to ASCII. Drain both outputs while the hook is running.
$process = New-Object System.Diagnostics.Process
$process.StartInfo.FileName = $bash
$process.StartInfo.Arguments = '"' + (Join-Path $PSScriptRoot $HookName) + '"'
$process.StartInfo.UseShellExecute = $false
$process.StartInfo.CreateNoWindow = $true
$process.StartInfo.RedirectStandardInput = $true
$process.StartInfo.RedirectStandardOutput = $true
$process.StartInfo.RedirectStandardError = $true
$process.StartInfo.StandardOutputEncoding = $OutputEncoding
$process.StartInfo.StandardErrorEncoding = $OutputEncoding
$started = $false
try {
    $started = $process.Start()
    if (-not $started) {
        throw 'Failed to start Git Bash.'
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $payload = $OutputEncoding.GetBytes([Console]::In.ReadToEnd())
    $process.StandardInput.BaseStream.Write($payload, 0, $payload.Length)
    $process.StandardInput.Close()
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $code = $process.ExitCode
} finally {
    if ($started -and -not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
    }
    $process.Dispose()
}

[Console]::Error.Write($stderr)
if ($HookName -eq 'agent-command' -and $code -eq 2) {
    # A pwsh -Command host maps native nonzero exits to 1. A structured deny
    # with exit 0 survives that mapping and remains a blocking hook decision.
    $decision = @{
        hookSpecificOutput = @{
            hookEventName = 'PreToolUse'
            permissionDecision = 'deny'
            permissionDecisionReason = $stderr.Trim()
        }
    }
    [Console]::Out.WriteLine(($decision | ConvertTo-Json -Depth 3 -Compress))
    exit 0
}
[Console]::Out.Write($stdout)
exit $code
