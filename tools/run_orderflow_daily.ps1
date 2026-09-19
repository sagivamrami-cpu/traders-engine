param(
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$logRoot = Join-Path $DataRoot 'logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$logPath = Join-Path $logRoot "$stamp.log"
& py -3 (Join-Path $PSScriptRoot 'collect_databento_orderflow.py') --data-root $DataRoot *>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE
