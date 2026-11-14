# Pull the newest verified FlareLedger snapshot from the VPS to this computer.
# Run from any folder: powershell -File scripts\pull-backup.ps1
param(
    [string]$SshTarget = 'tymofii@57.129.163.115',
    [string]$RemoteRoot = '/var/backups/flareledger/snapshots',
    [ValidateSet('daily', 'pre-update')]
    [string]$Kind = 'daily',
    [int]$Keep = 7,
    [string]$Destination = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'FlareLedger-backups')
)
$ErrorActionPreference = 'Stop'
$namePattern = '^flareledger-(daily|pre-update)-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$'

function Assert-Snapshot([string]$Directory) {
    foreach ($name in @('flareledger.sqlite3', 'manifest.json', 'seed-reference.json', 'SHA256SUMS')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Directory $name) -PathType Leaf)) {
            throw "Snapshot is incomplete: $name is missing"
        }
    }
    $listed = @{}
    foreach ($line in (Get-Content -LiteralPath (Join-Path $Directory 'SHA256SUMS'))) {
        if ($line -notmatch '^([a-f0-9]{64}) [ *]([^/\\]+)$') { throw 'Invalid SHA256SUMS entry' }
        $listed[$Matches[2]] = $Matches[1]
    }
    foreach ($name in @('flareledger.sqlite3', 'manifest.json', 'seed-reference.json')) {
        if (-not $listed.ContainsKey($name)) { throw "SHA256SUMS does not cover $name" }
    }
    foreach ($name in $listed.Keys) {
        $path = Join-Path $Directory $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $listed[$name]) {
            throw "Checksum mismatch: $name"
        }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $Directory 'manifest.json') -Raw | ConvertFrom-Json
    if ($manifest.format -ne 'flareledger.backup.v1' -or $manifest.project -ne 'flareledger') {
        throw 'Unsupported snapshot manifest'
    }
    # Optional deeper check (SQLite integrity, corpus counts) when Python is installed.
    $verifier = Join-Path $PSScriptRoot 'snapshot_tools.py'
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and (Test-Path -LiteralPath $verifier)) {
        & $python.Source -I $verifier verify $Directory
        if ($LASTEXITCODE -ne 0) { throw 'Offline snapshot verification failed' }
    } else {
        Write-Host 'NOTE: Python not found; SQLite integrity was verified on the VPS only.'
    }
}

try {
    if ($SshTarget -notmatch '^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$') { throw 'Invalid SSH target' }
    if ($RemoteRoot -notmatch '^/[a-zA-Z0-9._/-]+$') { throw 'Invalid remote directory' }
    if ($Keep -lt 1) { throw 'Keep must be at least 1' }
    $command = "find '$RemoteRoot' -mindepth 1 -maxdepth 1 -type d -name 'flareledger-$Kind-*' -printf '%f\n' | sort -r | head -n 1"
    $lines = @(ssh $SshTarget $command)
    if ($LASTEXITCODE -ne 0) { throw 'Remote snapshot listing failed' }
    $snapshotName = ($lines -join '').Trim()
    if ($snapshotName -notmatch $namePattern) { throw "No valid $Kind snapshot found on the VPS" }
    $root = [System.IO.Path]::GetFullPath($Destination)
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    if ((Get-Item -LiteralPath $root).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Backup destination must not be a reparse point'
    }
    $final = Join-Path $root $snapshotName
    if (-not (Test-Path -LiteralPath $final)) {
        $pending = Join-Path $root ('.pending-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $pending | Out-Null
        scp -r "${SshTarget}:$RemoteRoot/$snapshotName" $pending
        if ($LASTEXITCODE -ne 0) { throw 'Snapshot transfer failed; pending directory preserved' }
        $download = Join-Path $pending $snapshotName
        Assert-Snapshot $download
        Move-Item -LiteralPath $download -Destination $final
        Remove-Item -LiteralPath $pending
    }
    Assert-Snapshot $final
    $all = @(Get-ChildItem -LiteralPath $root -Directory |
        Where-Object { $_.Name -match $namePattern -and $_.Name -like "flareledger-$Kind-*" } |
        Sort-Object Name -Descending)
    foreach ($old in @($all | Select-Object -Skip $Keep)) {
        $resolved = [System.IO.Path]::GetFullPath($old.FullName)
        $prefix = $root.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            ($old.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw 'Unsafe retention target'
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    Write-Host "FLARELEDGER_BACKUP_PULLED | kind=$Kind | snapshot=$snapshotName | keep=$Keep | exit=0"
}
catch {
    Write-Host 'FLARELEDGER_BACKUP_PULL_FAILED | exit=1'
    Write-Error $_
    exit 1
}
