$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $root 'source'
$out = Join-Path $root 'build\out'
$reader = Join-Path $root 'reader\00_EGA_ko_CUMULATIVE_READER.pdf'
$pdf = Join-Path $out 'main.pdf'
$log = Join-Path $out 'main.log'
$reference = Join-Path $out 'main.reference.pdf'
$inputManifestPath = Join-Path $src 'CUMULATIVE_INPUTS.json'

if (-not (Test-Path -LiteralPath $inputManifestPath -PathType Leaf)) {
  throw 'Cumulative input manifest is missing.'
}
$inputManifest = Get-Content -LiteralPath $inputManifestPath -Raw | ConvertFrom-Json
if ($inputManifest.schema -cne 'ega-ko-cumulative-inputs-v1') {
  throw 'Unsupported cumulative input manifest schema.'
}
if ($inputManifest.entrypoint -cne 'main.tex') {
  throw 'Cumulative input manifest must bind source/main.tex.'
}
$declaredInputs = @($inputManifest.ordered_inputs | ForEach-Object { [string]$_.path })
if ($declaredInputs.Count -eq 0) { throw 'Cumulative input manifest declares no reader inputs.' }
if (@($declaredInputs | Sort-Object -Unique).Count -ne $declaredInputs.Count) {
  throw 'Cumulative input manifest contains duplicate paths.'
}
foreach ($relativePath in $declaredInputs) {
  if ([IO.Path]::IsPathRooted($relativePath) -or $relativePath -match '(^|[\\/])\.\.([\\/]|$)') {
    throw "Unsafe cumulative input path: $relativePath"
  }
  if (-not (Test-Path -LiteralPath (Join-Path $src $relativePath) -PathType Leaf)) {
    throw "Declared cumulative input is missing: $relativePath"
  }
}
$mainPath = Join-Path $src 'main.tex'
if (-not (Test-Path -LiteralPath $mainPath -PathType Leaf)) { throw 'source/main.tex is missing.' }
$mainText = Get-Content -LiteralPath $mainPath -Raw
$compiledInputs = @([regex]::Matches($mainText, '\\input\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value })
if (($compiledInputs -join "`n") -cne ($declaredInputs -join "`n")) {
  throw 'source/main.tex input order does not exactly match CUMULATIVE_INPUTS.json.'
}
$knownTex = @('main.tex') + $declaredInputs
$presentTex = @(Get-ChildItem -LiteralPath $src -Recurse -File -Filter '*.tex' | ForEach-Object {
  [IO.Path]::GetRelativePath($src, $_.FullName).Replace('\\', '/')
} | Sort-Object)
$knownTex = @($knownTex | ForEach-Object { $_.Replace('\\', '/') } | Sort-Object)
if (($presentTex -join "`n") -cne ($knownTex -join "`n")) {
  throw 'The source tree contains undeclared or absent TeX files; cumulative inclusion is not proven.'
}

New-Item -ItemType Directory -Force -Path $out | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reader) | Out-Null
Get-Command xelatex -ErrorAction Stop | Out-Null

# Freeze PDF creation metadata so clean builds are byte-reproducible.
$previousEpoch = $env:SOURCE_DATE_EPOCH
$previousForce = $env:FORCE_SOURCE_DATE
$previousTz = $env:TZ
$env:SOURCE_DATE_EPOCH = '1786633200'
$env:FORCE_SOURCE_DATE = '1'
$env:TZ = 'UTC'

Push-Location $src
try {
  1..3 | ForEach-Object {
    & xelatex -interaction=nonstopmode -halt-on-error -output-directory $out 'main.tex' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $_ failed with exit code $LASTEXITCODE." }
  }
  Copy-Item -LiteralPath $pdf -Destination $reference -Force
  1..3 | ForEach-Object {
    & xelatex -interaction=nonstopmode -halt-on-error -output-directory $out 'main.tex' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX repeat pass $_ failed with exit code $LASTEXITCODE." }
  }
  $referenceHash = (Get-FileHash -LiteralPath $reference -Algorithm SHA256).Hash
  $repeatHash = (Get-FileHash -LiteralPath $pdf -Algorithm SHA256).Hash
  if ($referenceHash -ne $repeatHash) { throw 'Repeated fixed-metadata build is not byte-identical.' }
  Remove-Item -LiteralPath $reference
} finally {
  Pop-Location
  if ($null -eq $previousEpoch) { Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue } else { $env:SOURCE_DATE_EPOCH = $previousEpoch }
  if ($null -eq $previousForce) { Remove-Item Env:FORCE_SOURCE_DATE -ErrorAction SilentlyContinue } else { $env:FORCE_SOURCE_DATE = $previousForce }
  if ($null -eq $previousTz) { Remove-Item Env:TZ -ErrorAction SilentlyContinue } else { $env:TZ = $previousTz }
}

if (-not (Test-Path -LiteralPath $pdf -PathType Leaf)) { throw 'Reader PDF was not produced.' }
if (-not (Test-Path -LiteralPath $log -PathType Leaf)) { throw 'Build log was not produced.' }

$logText = Get-Content -LiteralPath $log -Raw
$bad = @('Undefined control sequence', 'LaTeX Error', 'Fatal error', 'Emergency stop', 'undefined references', 'Rerun to get', 'Label(s) may have changed', 'Missing character', 'Overfull \hbox', 'Underfull \hbox', 'Overfull \vbox', 'Underfull \vbox')
foreach ($pattern in $bad) {
  if ($logText.Contains($pattern)) { throw "Build diagnostic found: $pattern" }
}

Copy-Item -LiteralPath $pdf -Destination $reader -Force
$item = Get-Item -LiteralPath $reader
$hash = (Get-FileHash -LiteralPath $reader -Algorithm SHA256).Hash
Write-Output "PASS $($item.Length) bytes SHA-256 $hash"
