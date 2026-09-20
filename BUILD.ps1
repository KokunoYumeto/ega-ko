param([switch]$Direct)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Join-Path $repoRoot 'source'
$inputPath = if ($Direct) { Join-Path $repoRoot '01_EGA_ko_CUMULATIVE.tex' } else { Join-Path $sourceRoot 'main.tex' }
$workingRoot = if ($Direct) { $repoRoot } else { $sourceRoot }
$jobName = if ($Direct) { 'EGA_ko_CUMULATIVE' } else { 'main' }
$outRoot = Join-Path $repoRoot 'build\out'
$mutex = [Threading.Mutex]::new($false, 'Global\InterlanguageTeXSlotV1')
$acquired = $false
$oldEpoch = $env:SOURCE_DATE_EPOCH
$oldForce = $env:FORCE_SOURCE_DATE
$oldTz = $env:TZ
try {
  $acquired = $mutex.WaitOne(300000)
  if (-not $acquired) { throw 'Timed out waiting for Global\InterlanguageTeXSlotV1.' }
  New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
  $env:SOURCE_DATE_EPOCH = '1789862400'
  $env:FORCE_SOURCE_DATE = '1'
  $env:TZ = 'UTC'
  foreach ($pass in 1..4) {
    & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory=$outRoot -jobname=$jobName $inputPath
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed on pass $pass." }
    Copy-Item -LiteralPath (Join-Path $outRoot "$jobName.pdf") -Destination (Join-Path $outRoot "$jobName.pass$pass.pdf") -Force
  }
  $p3 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $outRoot "$jobName.pass3.pdf")).Hash
  $p4 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $outRoot "$jobName.pass4.pdf")).Hash
  if ($p3 -cne $p4) { throw 'Passes 3 and 4 are not byte-identical.' }
} finally {
  if ($null -eq $oldEpoch) { Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue } else { $env:SOURCE_DATE_EPOCH = $oldEpoch }
  if ($null -eq $oldForce) { Remove-Item Env:FORCE_SOURCE_DATE -ErrorAction SilentlyContinue } else { $env:FORCE_SOURCE_DATE = $oldForce }
  if ($null -eq $oldTz) { Remove-Item Env:TZ -ErrorAction SilentlyContinue } else { $env:TZ = $oldTz }
  if ($acquired) { $mutex.ReleaseMutex() }
  $mutex.Dispose()
}
