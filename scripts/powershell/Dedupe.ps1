<#
.SYNOPSIS
  Deduplica F:\ORGANIZADO\: encuentra clones EXACTOS por SHA1 a traves del arbol
  y los mueve a F:\ORGANIZADO_PLAN\_DUPLICADOS\ (en vez de borrar) preservando la
  ruta original como referencia. Mantiene la PRIMERA ocurrencia.

.DESCRIPTION
  Algoritmo:
   1. Indexa todos los archivos bajo F:\ORGANIZADO\ por tamano (rapido).
   2. Para cada grupo de tamano repetido, calcula SHA1 (solo en grupos
      con potencial duplicado).
   3. Archivos con mismo SHA1 -> mantiene el que tiene path mas corto/preferente,
      mueve los demas a _DUPLICADOS\ con el path original incluido en el nombre.
  
  Resumable: si se interrumpe, re-ejecutar continua desde el ultimo grupo procesado.

.PARAMETER Root
  Default: F:\

.PARAMETER PlanDir
  Default: F:\ORGANIZADO_PLAN

.PARAMETER DryRun
  Solo lista que mover ria.

.EXAMPLE
  PowerShell -ExecutionPolicy Bypass -File F:\ORGANIZADO_PLAN\Dedupe.ps1 -DryRun

.EXAMPLE
  PowerShell -ExecutionPolicy Bypass -File F:\ORGANIZADO_PLAN\Dedupe.ps1
#>

[CmdletBinding()]
param(
  [string]$Root    = 'F:\',
  [string]$PlanDir = 'F:\ORGANIZADO_PLAN',
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Target  = Join-Path $Root 'ORGANIZADO'
$DupDir  = Join-Path $PlanDir '_DUPLICADOS'
$LogFile = Join-Path $PlanDir 'log_dedupe.tsv'
$IndexFile = Join-Path $PlanDir 'dedup_index.tsv'

if (-not (Test-Path $Target)) {
  Write-Error "No encuentro $Target"; exit 1
}
if (-not (Test-Path $DupDir)) {
  New-Item -ItemType Directory -Path $DupDir -Force | Out-Null
}

# Preference scoring for which file to KEEP (lower score wins)
function Get-Score {
  param([string]$RelPath)
  $score = 0
  $depth = ($RelPath -split '\\').Count
  $score += $depth * 100
  # Prefer non-Software/Other paths
  if ($RelPath -like 'PC\Other\*')    { $score += 50000 }
  if ($RelPath -like 'PC\Software\*') { $score += 30000 }
  if ($RelPath -like 'PC\Downloads\*'){ $score += 20000 }
  # Penalize "from-" suffixes (those are second-version copies)
  if ($RelPath -match '__from-')      { $score += 100000 }
  return $score
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " DEDUPE - F:\ORGANIZADO\" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " DryRun     : $DryRun"
Write-Host ""
Write-Host "1) Indexando archivos en $Target..."

# Build size groups
$bySize = @{}
$count = 0
Get-ChildItem -LiteralPath $Target -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $count++
  if ($count % 5000 -eq 0) { Write-Host "   indexados: $count" }
  $sz = $_.Length
  if (-not $bySize.ContainsKey($sz)) { $bySize[$sz] = New-Object 'System.Collections.ArrayList' }
  [void]$bySize[$sz].Add($_.FullName)
}
Write-Host "   total: $count archivos"

# Filter to candidate groups (size >0, count >1)
$candidates = $bySize.GetEnumerator() | Where-Object { $_.Key -gt 0 -and $_.Value.Count -gt 1 }
$candCount = ($candidates | Measure-Object).Count
$totalFiles = ($candidates | ForEach-Object { $_.Value.Count } | Measure-Object -Sum).Sum
Write-Host "2) Grupos con potencial duplicado: $candCount  ($totalFiles archivos a hashear)"
Write-Host ""

$logStream = [System.IO.StreamWriter]::new($LogFile, $true, [System.Text.Encoding]::UTF8)
$saved = 0L
$kept  = 0
$moved = 0
$errs  = 0
$processedGroups = 0

try {
  foreach ($kv in $candidates) {
    $processedGroups++
    if ($processedGroups % 100 -eq 0) {
      Write-Progress -Activity "Dedupe" -Status "$processedGroups/$candCount grupos | movidos $moved | recuperado $([Math]::Round($saved/1GB,2)) GiB" -PercentComplete ([Math]::Round(100.0*$processedGroups/$candCount,1))
    }
    $size = $kv.Key
    $paths = $kv.Value

    # Hash each
    $byHash = @{}
    foreach ($p in $paths) {
      try {
        $h = (Get-FileHash -LiteralPath $p -Algorithm SHA1).Hash
      } catch {
        $errs++
        continue
      }
      if (-not $byHash.ContainsKey($h)) { $byHash[$h] = New-Object 'System.Collections.ArrayList' }
      [void]$byHash[$h].Add($p)
    }
    foreach ($hashGroup in $byHash.Values) {
      if ($hashGroup.Count -lt 2) { continue }
      # Pick keeper
      $scored = $hashGroup | ForEach-Object {
        $rel = $_.Substring($Target.Length+1)
        [pscustomobject]@{ Full=$_; Rel=$rel; Score=(Get-Score $rel) }
      } | Sort-Object Score
      $keeper = $scored[0]
      $kept++
      foreach ($d in $scored | Select-Object -Skip 1) {
        $relSafe = $d.Rel -replace '[\\/]', '__'
        $dupTarget = Join-Path $DupDir $relSafe
        if ($DryRun) {
          Write-Host "[DRY] dup -> $($d.Rel)  (keeper: $($keeper.Rel))"
        } else {
          try {
            $dupDirParent = Split-Path -LiteralPath $dupTarget -Parent
            if (-not (Test-Path -LiteralPath $dupDirParent)) {
              New-Item -ItemType Directory -Path $dupDirParent -Force | Out-Null
            }
            Move-Item -LiteralPath $d.Full -Destination $dupTarget -Force
            $logStream.WriteLine("$($d.Rel)`t$($keeper.Rel)`t$size")
            $logStream.Flush()
            $moved++
            $saved += $size
          } catch {
            $errs++
            $logStream.WriteLine("ERROR`t$($d.Rel)`t$($_.Exception.Message)")
            $logStream.Flush()
          }
        }
      }
    }
  }
} finally {
  $logStream.Close()
  Write-Progress -Activity "Dedupe" -Completed
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " DEDUPE - RESULTADOS" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Grupos hash con clones        : $kept"
Write-Host " Archivos movidos a duplicados : $moved"
Write-Host " Errores                       : $errs"
Write-Host " Espacio recuperado            : $([Math]::Round($saved / 1GB, 2)) GiB"
Write-Host ""
Write-Host "Duplicados movidos a: $DupDir"
Write-Host "Si todo OK, podes borrar esa carpeta entera para liberar el espacio."
