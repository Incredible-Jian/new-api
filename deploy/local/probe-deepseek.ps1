# Run from Windows after setting up the local gateway and the DPAPI credential.
$ErrorActionPreference = 'Stop'
$compose = Join-Path $PSScriptRoot 'compose.yaml'
$protectedFile = Join-Path $env:LOCALAPPDATA 'ModelSupplyPlatform/deepseek-test.dpapi'
$encrypted = (Get-Content -Raw -LiteralPath $protectedFile).Trim()
$secret = [pscredential]::new('deepseek', (ConvertTo-SecureString $encrypted))
try {
    $secret.GetNetworkCredential().Password | docker compose -f $compose exec -T gateway sh -ec 'umask 077; cat > /run/pilot/deepseek'
    if ($LASTEXITCODE -ne 0) { throw 'Could not load the transient credential.' }
    python -B (Join-Path $PSScriptRoot 'deepseek_probe.py')
    if ($LASTEXITCODE -ne 0) { throw 'Live gateway probe failed.' }
} finally {
    docker compose -f $compose exec -T gateway sh -ec 'rm -f /run/pilot/deepseek'
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify transient credential cleanup.' }
}
