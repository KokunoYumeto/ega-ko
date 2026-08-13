$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $root 'source'
$out = Join-Path $root 'build\out'
$reader = Join-Path $root 'reader\00_EGA_ko_CUMULATIVE_READER.pdf'

New-Item -ItemType Directory -Force -Path $out | Out-Null
Get-Command xelatex -ErrorAction Stop | Out-Null

# Freeze PDF creation metadata so clean builds are byte-reproducible.
$previousEpoch = $env:SOURCE_DATE_EPOCH
$previousForce = $env:FORCE_SOURCE_DATE
$env:SOURCE_DATE_EPOCH = '1786633200'
$env:FORCE_SOURCE_DATE = '1'

Push-Location $src
try {
  1..3 | ForEach-Object {
    & xelatex -interaction=nonstopmode -halt-on-error "-output-directory=$out" 'main.tex' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $_ failed with exit code $LASTEXITCODE." }
  }
} finally {
  Pop-Location
  if ($null -eq $previousEpoch) { Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue } else { $env:SOURCE_DATE_EPOCH = $previousEpoch }
  if ($null -eq $previousForce) { Remove-Item Env:FORCE_SOURCE_DATE -ErrorAction SilentlyContinue } else { $env:FORCE_SOURCE_DATE = $previousForce }
}

$pdf = Join-Path $out 'main.pdf'
$log = Join-Path $out 'main.log'
if (-not (Test-Path -LiteralPath $pdf -PathType Leaf)) { throw 'Reader PDF was not produced.' }
if (-not (Test-Path -LiteralPath $log -PathType Leaf)) { throw 'Build log was not produced.' }

$logText = Get-Content -LiteralPath $log -Raw
$bad = @('Undefined control sequence', 'LaTeX Error', 'Missing character', 'Overfull \hbox', 'Underfull \hbox')
foreach ($pattern in $bad) {
  if ($logText.Contains($pattern)) { throw "Build diagnostic found: $pattern" }
}

Copy-Item -LiteralPath $pdf -Destination $reader -Force
$item = Get-Item -LiteralPath $reader
$hash = (Get-FileHash -LiteralPath $reader -Algorithm SHA256).Hash
Write-Output "PASS $($item.Length) bytes SHA-256 $hash"
