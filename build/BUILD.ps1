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
if ($inputManifest.schema -cne 'ega-ko-cumulative-inputs-v2') {
  throw 'Unsupported cumulative input manifest schema.'
}
if ($inputManifest.entrypoint -cne 'main.tex') {
  throw 'Cumulative input manifest must bind source/main.tex.'
}
$coverageRows = @($inputManifest.coverage_matrix)
if ($coverageRows.Count -ne [int]$inputManifest.authority_driver.content_input_count) {
  throw 'Coverage matrix does not contain every canonical driver input.'
}
if (@($coverageRows.source_path | Sort-Object -Unique).Count -ne $coverageRows.Count) {
  throw 'Coverage matrix contains duplicate canonical source paths.'
}
if (@($coverageRows.driver_line | Sort-Object -Unique).Count -ne $coverageRows.Count) {
  throw 'Coverage matrix contains duplicate canonical driver lines.'
}
$allowedCoverageStates = @('complete', 'partial', 'not_translated')
foreach ($row in $coverageRows) {
  if ($allowedCoverageStates -cnotcontains [string]$row.status) {
    throw "Unsupported coverage state for $($row.source_path): $($row.status)"
  }
  if ($row.status -ceq 'not_translated') {
    if ($null -ne $row.target_path -or $null -ne $row.target_sha256) {
      throw "Untranslated driver row improperly claims a target: $($row.source_path)"
    }
    continue
  }
  if ([string]::IsNullOrWhiteSpace([string]$row.target_path)) {
    throw "Translated driver row lacks a target: $($row.source_path)"
  }
  $targetPath = Join-Path $src ([string]$row.target_path)
  if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    throw "Coverage target is missing: $($row.target_path)"
  }
  $targetItem = Get-Item -LiteralPath $targetPath
  if ($targetItem.Length -ne [int64]$row.target_bytes) {
    throw "Coverage target byte mismatch: $($row.target_path)"
  }
  $targetHash = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash
  if ($targetHash -cne [string]$row.target_sha256) {
    throw "Coverage target hash mismatch: $($row.target_path)"
  }
  $targetText = Get-Content -LiteralPath $targetPath -Raw
  $targetLfLines = ([regex]::Matches($targetText, "`n")).Count
  if ($targetLfLines -ne [int]$row.target_lf_lines) {
    throw "Coverage target LF-line mismatch: $($row.target_path)"
  }
  $targetMarkers = ([regex]::Matches($targetText, '\\oldpage')).Count
  if ($targetMarkers -ne [int]$row.historical_page_markers) {
    throw "Coverage target historical-page-marker mismatch: $($row.target_path)"
  }
}
$translatedTargets = @($coverageRows | Where-Object { $_.status -cne 'not_translated' } | ForEach-Object { [string]$_.target_path })
$declaredTargets = @($inputManifest.ordered_inputs | ForEach-Object { [string]$_.path })
if (($translatedTargets -join "`n") -cne ($declaredTargets -join "`n")) {
  throw 'Ordered reader inputs do not exactly equal the translated canonical coverage rows.'
}
$manifestMarkerCount = ($coverageRows | Measure-Object -Property historical_page_markers -Sum).Sum
if ($manifestMarkerCount -ne [int]$inputManifest.scope.historical_source_pages) {
  throw 'Historical source-page count does not equal the coverage-matrix marker sum.'
}

# A controlled release build can additionally bind the portable package to the
# live canonical driver and private Korean inventory.  Portable replays omit
# these environment variables but still enforce every internal target byte.
$canonicalRoot = $env:AGKO_CANONICAL_ROOT
$privateRoot = $env:AGKO_PRIVATE_ROOT
$requireLiveCoverage = ($env:AGKO_REQUIRE_LIVE_COVERAGE -ceq '1')
if (-not [string]::IsNullOrWhiteSpace($canonicalRoot)) {
  $driverPath = Join-Path $canonicalRoot ([string]$inputManifest.authority_driver.path)
  if (-not (Test-Path -LiteralPath $driverPath -PathType Leaf)) { throw 'Live canonical EGA driver is missing.' }
  $driverItem = Get-Item -LiteralPath $driverPath
  $driverHash = (Get-FileHash -LiteralPath $driverPath -Algorithm SHA256).Hash
  if ($driverItem.Length -ne [int64]$inputManifest.authority_driver.bytes -or
      $driverHash -cne [string]$inputManifest.authority_driver.sha256) {
    throw 'Live canonical EGA driver identity drifted from the coverage matrix.'
  }
  $driverLines = @(Get-Content -LiteralPath $driverPath)
  $liveRows = @()
  for ($lineIndex = 60; $lineIndex -lt $driverLines.Count; $lineIndex++) {
    $line = $driverLines[$lineIndex]
    if ($line.StartsWith('\input{')) {
      $liveRows += [pscustomobject]@{
        driver_line = $lineIndex + 1
        source_path = $line.Substring(7, $line.Length - 8)
      }
    }
  }
  if ($liveRows.Count -ne $coverageRows.Count) { throw 'Live canonical driver input count drifted.' }
  for ($i = 0; $i -lt $coverageRows.Count; $i++) {
    $row = $coverageRows[$i]
    if ($liveRows[$i].driver_line -ne [int]$row.driver_line -or
        $liveRows[$i].source_path -cne [string]$row.source_path) {
      throw "Live canonical driver order drifted at coverage row $i."
    }
    $authorityPath = Join-Path (Split-Path -Parent $driverPath) ([string]$row.source_path)
    if (-not (Test-Path -LiteralPath $authorityPath -PathType Leaf)) {
      throw "Live canonical input is missing: $($row.source_path)"
    }
    $authorityItem = Get-Item -LiteralPath $authorityPath
    $authorityHash = (Get-FileHash -LiteralPath $authorityPath -Algorithm SHA256).Hash
    if ($authorityItem.Length -ne [int64]$row.source_bytes -or
        $authorityHash -cne [string]$row.source_sha256) {
      throw "Live canonical input identity drifted: $($row.source_path)"
    }
  }
} elseif ($requireLiveCoverage) {
  throw 'Strict release build requires AGKO_CANONICAL_ROOT.'
}
if (-not [string]::IsNullOrWhiteSpace($privateRoot)) {
  foreach ($row in $coverageRows | Where-Object { $_.status -cne 'not_translated' -and $_.target_path -cne 'front.tex' }) {
    $workingPath = Join-Path $privateRoot ([string]$row.working_path)
    if (-not (Test-Path -LiteralPath $workingPath -PathType Leaf)) {
      throw "Private Korean working target is missing: $($row.working_path)"
    }
    $workingItem = Get-Item -LiteralPath $workingPath
    $workingHash = (Get-FileHash -LiteralPath $workingPath -Algorithm SHA256).Hash
    if ($workingItem.Length -ne [int64]$row.target_bytes -or
        $workingHash -cne [string]$row.target_sha256) {
      throw "Public/private Korean target drift: $($row.target_path)"
    }
  }
  $unitIndexPath = Join-Path $privateRoot ([string]$inputManifest.reconciliation.private_inventory)
  if (-not (Test-Path -LiteralPath $unitIndexPath -PathType Leaf)) { throw 'Private Korean unit index is missing.' }
  $unitIds = @{}
  foreach ($line in Get-Content -LiteralPath $unitIndexPath) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $record = $line | ConvertFrom-Json
    $unitIds[[string]$record.id] = $true
  }
  foreach ($requiredId in @($inputManifest.reconciliation.required_latest_records)) {
    if (-not $unitIds.ContainsKey([string]$requiredId)) {
      throw "Required private coverage record is missing: $requiredId"
    }
  }
} elseif ($requireLiveCoverage) {
  throw 'Strict release build requires AGKO_PRIVATE_ROOT.'
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
$normalizedSrc = [IO.Path]::GetFullPath($src).TrimEnd([char[]]@('\', '/'))
$presentTex = @(Get-ChildItem -LiteralPath $src -Recurse -File -Filter '*.tex' | ForEach-Object {
  $fullName = [IO.Path]::GetFullPath($_.FullName)
  if (-not $fullName.StartsWith($normalizedSrc + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "TeX input escaped the source tree: $fullName"
  }
  $fullName.Substring($normalizedSrc.Length + 1).Replace('\\', '/')
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
