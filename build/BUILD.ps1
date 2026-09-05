$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $root 'source'
$buildRoot = Join-Path $root 'build'
$out = Join-Path $buildRoot 'out'
$reader = Join-Path $root 'reader\00_EGA_ko_CUMULATIVE_READER.pdf'
$pdf = Join-Path $out 'main.pdf'
$log = Join-Path $out 'main.log'
$passTwoPdf = Join-Path $out 'main.pass2.pdf'
$passThreePdf = Join-Path $out 'main.pass3.pdf'
$cycleAPdf = Join-Path $buildRoot 'cycle-a.pdf'
$cycleALog = Join-Path $buildRoot 'cycle-a.log'
$cycleAPassTwoPdf = Join-Path $buildRoot 'cycle-a.pass2.pdf'
$cycleAPassThreePdf = Join-Path $buildRoot 'cycle-a.pass3.pdf'
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

$xelatexCommand = Get-Command xelatex -CommandType Application -ErrorAction Stop
$xelatexPath = $xelatexCommand.Path

$badDiagnostics = @(
  'Undefined control sequence',
  'LaTeX Error',
  'Fatal error',
  'Emergency stop',
  'undefined references',
  'Rerun to get',
  'Label(s) may have changed',
  'Missing character',
  'Overfull \hbox',
  'Underfull \hbox',
  'Overfull \vbox',
  'Underfull \vbox'
)

function Reset-TaskOwnedBuildDirectory {
  param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][string]$ExpectedLeaf
  )

  $fullBuildRoot = [IO.Path]::GetFullPath($buildRoot).TrimEnd([char[]]@('\', '/'))
  $fullPath = [IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\', '/'))
  $actualParent = [IO.Path]::GetDirectoryName($fullPath).TrimEnd([char[]]@('\', '/'))
  $actualLeaf = [IO.Path]::GetFileName($fullPath)
  $buildItem = Get-Item -LiteralPath $fullBuildRoot -Force

  if (-not $buildItem.PSIsContainer -or
      (($buildItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
    throw 'The task build root is not an ordinary directory.'
  }
  if (-not [string]::Equals($actualParent, $fullBuildRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean a path outside the exact task build root: $fullPath"
  }
  if (-not [string]::Equals($actualLeaf, $ExpectedLeaf, [StringComparison]::Ordinal)) {
    throw "Refusing to clean an unexpected task build directory: $fullPath"
  }
  if (Test-Path -LiteralPath $fullPath) {
    $item = Get-Item -LiteralPath $fullPath -Force
    if (-not $item.PSIsContainer -or
        (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
      throw "Refusing to remove a non-directory or reparse point: $fullPath"
    }
    Remove-Item -LiteralPath $fullPath -Recurse -Force
  }
  New-Item -ItemType Directory -Path $fullPath | Out-Null
}

function Test-FilesByteIdentical {
  param(
    [Parameter(Mandatory)][string]$Left,
    [Parameter(Mandatory)][string]$Right
  )

  $leftStream = $null
  $rightStream = $null
  try {
    $leftStream = [IO.File]::OpenRead($Left)
    $rightStream = [IO.File]::OpenRead($Right)
    if ($leftStream.Length -ne $rightStream.Length) { return $false }
    $leftBuffer = New-Object byte[] 1048576
    $rightBuffer = New-Object byte[] 1048576
    while ($true) {
      $leftRead = $leftStream.Read($leftBuffer, 0, $leftBuffer.Length)
      $rightRead = $rightStream.Read($rightBuffer, 0, $rightBuffer.Length)
      if ($leftRead -ne $rightRead) { return $false }
      if ($leftRead -eq 0) { return $true }
      for ($i = 0; $i -lt $leftRead; $i++) {
        if ($leftBuffer[$i] -ne $rightBuffer[$i]) { return $false }
      }
    }
  } finally {
    if ($null -ne $rightStream) { $rightStream.Dispose() }
    if ($null -ne $leftStream) { $leftStream.Dispose() }
  }
}

function Invoke-XeLaTeXCycle {
  param(
    [Parameter(Mandatory)][string]$Cycle,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][string]$PassTwoPdfPath,
    [Parameter(Mandatory)][string]$PassThreePdfPath
  )

  for ($pass = 1; $pass -le 4; $pass++) {
    $stdoutPath = Join-Path $OutputDirectory "main.pass-$pass.stdout.txt"
    $stderrPath = Join-Path $OutputDirectory "main.pass-$pass.stderr.txt"
    $arguments = @(
      '-no-shell-escape',
      '-interaction=nonstopmode',
      '-halt-on-error',
      ('-output-directory="{0}"' -f $OutputDirectory),
      'main.tex'
    )
    $process = $null
    $exitCode = $null
    try {
      $process = Start-Process -FilePath $xelatexPath -ArgumentList $arguments `
        -WorkingDirectory $src -NoNewWindow `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath `
        -Wait -PassThru
      $exitCode = $process.ExitCode
    } finally {
      if ($null -ne $process) { $process.Dispose() }
    }
    if ($exitCode -ne 0) {
      throw "$Cycle XeLaTeX pass $pass failed with exit code $exitCode."
    }
    if ($pass -eq 2) {
      $currentPdf = Join-Path $OutputDirectory 'main.pdf'
      if (-not (Test-Path -LiteralPath $currentPdf -PathType Leaf)) {
        throw "$Cycle did not produce a pass-2 PDF."
      }
      Copy-Item -LiteralPath $currentPdf -Destination $PassTwoPdfPath -Force
    }
    if ($pass -eq 3) {
      $currentPdf = Join-Path $OutputDirectory 'main.pdf'
      if (-not (Test-Path -LiteralPath $currentPdf -PathType Leaf)) {
        throw "$Cycle did not produce a pass-3 PDF."
      }
      Copy-Item -LiteralPath $currentPdf -Destination $PassThreePdfPath -Force
    }
  }
}

function Get-ValidatedCycleResult {
  param(
    [Parameter(Mandatory)][string]$Cycle,
    [Parameter(Mandatory)][string]$FinalPdfPath,
    [Parameter(Mandatory)][string]$PassTwoPdfPath,
    [Parameter(Mandatory)][string]$PassThreePdfPath,
    [Parameter(Mandatory)][string]$LogPath
  )

  foreach ($requiredPath in @($FinalPdfPath, $PassTwoPdfPath, $PassThreePdfPath, $LogPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
      throw "$Cycle output is missing: $requiredPath"
    }
  }
  $logText = Get-Content -LiteralPath $LogPath -Raw
  foreach ($pattern in $badDiagnostics) {
    if ($logText.Contains($pattern)) { throw "$Cycle build diagnostic found: $pattern" }
  }
  $passTwoItem = Get-Item -LiteralPath $PassTwoPdfPath
  $passThreeItem = Get-Item -LiteralPath $PassThreePdfPath
  $finalItem = Get-Item -LiteralPath $FinalPdfPath
  $passTwoHash = (Get-FileHash -LiteralPath $PassTwoPdfPath -Algorithm SHA256).Hash
  $passThreeHash = (Get-FileHash -LiteralPath $PassThreePdfPath -Algorithm SHA256).Hash
  $finalHash = (Get-FileHash -LiteralPath $FinalPdfPath -Algorithm SHA256).Hash
  $passTwoFinalIdentical = Test-FilesByteIdentical -Left $PassTwoPdfPath -Right $FinalPdfPath
  $passThreeFinalIdentical = Test-FilesByteIdentical -Left $PassThreePdfPath -Right $FinalPdfPath
  if (-not $passThreeFinalIdentical) {
    throw "$Cycle did not converge byte-exactly between passes 3 and 4."
  }
  [pscustomobject]@{
    bytes = $finalItem.Length
    sha256 = $finalHash
    pass_two_bytes = $passTwoItem.Length
    pass_two_sha256 = $passTwoHash
    pass_two_final_identical = $passTwoFinalIdentical
    pass_three_bytes = $passThreeItem.Length
    pass_three_sha256 = $passThreeHash
    pass_three_final_identical = $passThreeFinalIdentical
  }
}

$mutexName = 'Global\InterlanguageTeXSlotV1'
$mutexTimeoutMilliseconds = 300000
$mutex = $null
$mutexAcquired = $false
$abandonedMutexRecovered = $false
$buildResult = $null

try {
  $mutex = [Threading.Mutex]::new($false, $mutexName)
  try {
    $mutexAcquired = $mutex.WaitOne($mutexTimeoutMilliseconds)
  } catch [Threading.AbandonedMutexException] {
    $mutexAcquired = $true
    $abandonedMutexRecovered = $true
  }
  if (-not $mutexAcquired) {
    throw "Timed out after $mutexTimeoutMilliseconds ms acquiring $mutexName."
  }

  $previousEpoch = $env:SOURCE_DATE_EPOCH
  $previousForce = $env:FORCE_SOURCE_DATE
  $previousTz = $env:TZ
  try {
    $env:SOURCE_DATE_EPOCH = '1786633200'
    $env:FORCE_SOURCE_DATE = '1'
    $env:TZ = 'UTC'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reader) | Out-Null

    Reset-TaskOwnedBuildDirectory -Path $out -ExpectedLeaf 'out'
    Invoke-XeLaTeXCycle -Cycle 'clean cycle A' -OutputDirectory $out -PassTwoPdfPath $passTwoPdf -PassThreePdfPath $passThreePdf
    $cycleA = Get-ValidatedCycleResult -Cycle 'clean cycle A' -FinalPdfPath $pdf -PassTwoPdfPath $passTwoPdf -PassThreePdfPath $passThreePdf -LogPath $log
    Copy-Item -LiteralPath $pdf -Destination $cycleAPdf -Force
    Copy-Item -LiteralPath $log -Destination $cycleALog -Force
    Copy-Item -LiteralPath $passTwoPdf -Destination $cycleAPassTwoPdf -Force
    Copy-Item -LiteralPath $passThreePdf -Destination $cycleAPassThreePdf -Force

    Reset-TaskOwnedBuildDirectory -Path $out -ExpectedLeaf 'out'
    Invoke-XeLaTeXCycle -Cycle 'clean cycle B' -OutputDirectory $out -PassTwoPdfPath $passTwoPdf -PassThreePdfPath $passThreePdf
    $cycleB = Get-ValidatedCycleResult -Cycle 'clean cycle B' -FinalPdfPath $pdf -PassTwoPdfPath $passTwoPdf -PassThreePdfPath $passThreePdf -LogPath $log

    $cleanCyclesMatch = Test-FilesByteIdentical -Left $cycleAPdf -Right $pdf
    if ($cycleA.bytes -ne $cycleB.bytes -or
        $cycleA.sha256 -cne $cycleB.sha256 -or
        -not $cleanCyclesMatch) {
      throw 'The two independent clean builds are not byte-identical.'
    }

    Copy-Item -LiteralPath $pdf -Destination $reader -Force
    $readerItem = Get-Item -LiteralPath $reader
    $readerHash = (Get-FileHash -LiteralPath $reader -Algorithm SHA256).Hash
    $promotionMatches = Test-FilesByteIdentical -Left $pdf -Right $reader
    if ($readerItem.Length -ne $cycleB.bytes -or
        $readerHash -cne $cycleB.sha256 -or
        -not $promotionMatches) {
      throw 'Reader promotion did not preserve the validated PDF bytes.'
    }

    $abandonedText = $abandonedMutexRecovered.ToString().ToLowerInvariant()
    $buildResult = "PASS $($readerItem.Length) bytes SHA-256 $readerHash; " +
      "cycle_a_sha256=$($cycleA.sha256); cycle_b_sha256=$($cycleB.sha256); " +
      "cycle_a_pass2_sha256=$($cycleA.pass_two_sha256); " +
      "cycle_b_pass2_sha256=$($cycleB.pass_two_sha256); " +
      "cycle_a_pass3_sha256=$($cycleA.pass_three_sha256); " +
      "cycle_b_pass3_sha256=$($cycleB.pass_three_sha256); " +
      "cycle_a_pass2_final_identical=$($cycleA.pass_two_final_identical.ToString().ToLowerInvariant()); " +
      "cycle_b_pass2_final_identical=$($cycleB.pass_two_final_identical.ToString().ToLowerInvariant()); " +
      "cycle_a_pass3_final_identical=$($cycleA.pass_three_final_identical.ToString().ToLowerInvariant()); " +
      "cycle_b_pass3_final_identical=$($cycleB.pass_three_final_identical.ToString().ToLowerInvariant()); " +
      "mutex=$mutexName; timeout_ms=$mutexTimeoutMilliseconds; " +
      "abandoned_recovery=$abandonedText"
  } finally {
    if ($null -eq $previousEpoch) { Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue } else { $env:SOURCE_DATE_EPOCH = $previousEpoch }
    if ($null -eq $previousForce) { Remove-Item Env:FORCE_SOURCE_DATE -ErrorAction SilentlyContinue } else { $env:FORCE_SOURCE_DATE = $previousForce }
    if ($null -eq $previousTz) { Remove-Item Env:TZ -ErrorAction SilentlyContinue } else { $env:TZ = $previousTz }
  }
} finally {
  try {
    if ($mutexAcquired) { $mutex.ReleaseMutex() }
  } finally {
    if ($null -ne $mutex) { $mutex.Dispose() }
  }
}

Write-Output $buildResult
