# Run the submitted examples without changing the current working directory.
param(
    [string]$PythonExe = 'python'
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
& $resolvedPython -X utf8 (Join-Path $projectRoot 'code/verify.py')
if ($LASTEXITCODE -ne 0) { throw 'BPE verification failed.' }
& $resolvedPython -X utf8 (Join-Path $projectRoot 'code/language_mix.py')
if ($LASTEXITCODE -ne 0) { throw 'Language quota checks failed.' }
Write-Output 'Done. Read the UTF-8 TXT and JSON files in the results folder.'
