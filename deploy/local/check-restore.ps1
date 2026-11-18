# Restore the local pilot dump into a new disposable database and compare row counts.
$ErrorActionPreference = 'Stop'
$compose = Join-Path $PSScriptRoot 'compose.yaml'
$name = 'restore_' + [guid]::NewGuid().ToString('N')
$archive = "/tmp/$name.dump"
function Db([string[]]$Arguments) {
    $result = docker compose -f $compose exec -T db @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Database recovery check failed at $($Arguments[0])." }
    return $result
}
$created = $false
try {
    Db @('pg_dump','-U','platform','-Fc','--file',$archive,'platform')
    Db @('createdb','-U','platform',$name)
    $created = $true
    Db @('pg_restore','--exit-on-error','--no-owner','-U','platform','-d',$name,$archive)
    $check = 'SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM channels), (SELECT count(*) FROM setups)'
    $source = Db @('psql','-At','-U','platform','-d','platform','-c',$check)
    $copy = Db @('psql','-At','-U','platform','-d',$name,'-c',$check)
    if ($source -ne $copy) { throw 'Restored database counts differ.' }
    Write-Output "Restored users, channels and setup records: $copy"
} finally {
    if ($created) { Db @('dropdb','-U','platform',$name) }
    Db @('rm','-f',$archive)
}
