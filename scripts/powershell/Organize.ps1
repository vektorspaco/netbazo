<#
.SYNOPSIS
  Organiza F:\ en F:\ORGANIZADO\. Originales NO se tocan.
  En colision: hash SHA1 -> si igual skip, si distinto sufijo.
  Implementado con APIs .NET para evitar problemas de parameter set en PS.
#>

[CmdletBinding()]
param(
  [string]$Root    = 'F:\',
  [string]$PlanDir = 'F:\ORGANIZADO_PLAN',
  [int]$Limit      = 0,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$RootDst   = Join-Path $Root 'ORGANIZADO'
$Csv       = Join-Path $PlanDir 'classification.csv'
$StateFile = Join-Path $PlanDir 'state.json'
$DoneFile  = Join-Path $PlanDir 'done.txt'
$SkipLog   = Join-Path $PlanDir 'log_skipped.tsv'
$RenameLog = Join-Path $PlanDir 'log_renamed.tsv'
$ErrorLog  = Join-Path $PlanDir 'log_errors.tsv'

if (-not [System.IO.File]::Exists($Csv)) {
  Write-Error "No encuentro $Csv"; exit 1
}

# .NET helpers -----------------------------------------------------------
$sha1 = [System.Security.Cryptography.SHA1]::Create()
function Get-Sha1Hex {
  param([string]$Path)
  try {
    $fs = [System.IO.File]::OpenRead($Path)
    try {
      $hashBytes = $sha1.ComputeHash($fs)
      return -join ($hashBytes | ForEach-Object { $_.ToString('x2') })
    } finally { $fs.Dispose() }
  } catch {
    return $null
  }
}

function Get-OriginTag {
  param([string]$Source)
  $top = ($Source -split '\\')[0]
  switch ($top) {
    '80gb sata'                 { return '80gb' }
    'ORDENAR'                   { return 'ord' }
    'Pixel 7 Stock (julio 24)'  { return 'pix' }
    'Takeout'                   { return 'tk' }
    'Nueva Carpeta (C)' {
      $parts = $Source -split '\\'
      if ($parts.Count -ge 2) {
        switch ($parts[1]) {
          'Nueva carpeta'      { return 'nc1' }
          'Nueva carpeta (2)'  { return 'nc2' }
          '(backup celu)'      { return 'celu' }
          default              { return 'nc' }
        }
      }
      return 'nc'
    }
    default { return 'src' }
  }
}

# Load done set ----------------------------------------------------------
$done = New-Object 'System.Collections.Generic.HashSet[string]'
if ([System.IO.File]::Exists($DoneFile)) {
  foreach ($line in [System.IO.File]::ReadAllLines($DoneFile)) {
    if ($line) { [void]$done.Add($line) }
  }
}

# Load state -------------------------------------------------------------
$state = [ordered]@{
  copied = 0; skipped = 0; renamed = 0; errors = 0; bytes = [int64]0
  started = (Get-Date).ToString('o')
}
if ([System.IO.File]::Exists($StateFile)) {
  try {
    $loaded = [System.IO.File]::ReadAllText($StateFile) | ConvertFrom-Json
    foreach ($p in 'copied','skipped','renamed','errors','bytes') {
      if ($null -ne $loaded.$p) { $state.$p = [int64]$loaded.$p }
    }
  } catch { }
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " ORGANIZADO - Cowork file organizer" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " Root        : $Root"
Write-Host " Destino     : $RootDst"
Write-Host " Plan        : $PlanDir"
Write-Host " Done previo : $($done.Count) archivos"
Write-Host " DryRun      : $DryRun"
if ($Limit -gt 0) { Write-Host " Limit       : $Limit filas en esta corrida" }
Write-Host ""

# Read CSV ---------------------------------------------------------------
Write-Host "Leyendo classification.csv..."
$rows = Import-Csv -Path $Csv -Encoding UTF8
$total = $rows.Count
Write-Host "Total filas: $total. Pendientes: $($total - $done.Count)"

# Append-only streams ----------------------------------------------------
$utf8 = [System.Text.Encoding]::UTF8
$skipStream   = [System.IO.StreamWriter]::new($SkipLog,   $true, $utf8)
$renameStream = [System.IO.StreamWriter]::new($RenameLog, $true, $utf8)
$errorStream  = [System.IO.StreamWriter]::new($ErrorLog,  $true, $utf8)
$doneStream   = [System.IO.StreamWriter]::new($DoneFile,  $true, $utf8)

$processed = 0
$lastSave = Get-Date
$startTime = Get-Date

try {
  foreach ($row in $rows) {
    $src = $row.Source
    if ($done.Contains($src)) { continue }
    $size = [int64]$row.Size
    $dst  = $row.Dest
    $srcAbs = Join-Path $Root $src
    $dstAbs = Join-Path $RootDst $dst

    if ($Limit -gt 0 -and $processed -ge $Limit) { break }
    $processed++

    if (-not [System.IO.File]::Exists($srcAbs)) {
      $errorStream.WriteLine("$src`t$dst`tsource missing"); $errorStream.Flush()
      $state.errors++
      $doneStream.WriteLine($src); $doneStream.Flush()
      [void]$done.Add($src)
      continue
    }

    if ($DryRun) {
      Write-Host "[DRY] $src -> $dst"
      continue
    }

    try {
      $dstDir = [System.IO.Path]::GetDirectoryName($dstAbs)
      if (-not [System.IO.Directory]::Exists($dstDir)) {
        [void][System.IO.Directory]::CreateDirectory($dstDir)
      }

      if ([System.IO.File]::Exists($dstAbs)) {
        $srcFi = [System.IO.FileInfo]::new($srcAbs)
        $dstFi = [System.IO.FileInfo]::new($dstAbs)
        $sameContent = $false
        if ($srcFi.Length -eq $dstFi.Length) {
          $hSrc = Get-Sha1Hex $srcAbs
          $hDst = Get-Sha1Hex $dstAbs
          if ($hSrc -and $hSrc -eq $hDst) { $sameContent = $true }
        }
        if ($sameContent) {
          $skipStream.WriteLine("$src`t$dst`t$hSrc"); $skipStream.Flush()
          $state.skipped++
          $doneStream.WriteLine($src); $doneStream.Flush()
          [void]$done.Add($src)
          continue
        }
        # Different content: suffix
        $tag = Get-OriginTag $src
        $base = [System.IO.Path]::GetFileNameWithoutExtension($dstAbs)
        $ext  = [System.IO.Path]::GetExtension($dstAbs)
        $parent = [System.IO.Path]::GetDirectoryName($dstAbs)
        $newDst = [System.IO.Path]::Combine($parent, ('{0}__from-{1}{2}' -f $base, $tag, $ext))
        $k = 1
        while ([System.IO.File]::Exists($newDst)) {
          $newDst = [System.IO.Path]::Combine($parent, ('{0}__from-{1}-{2}{3}' -f $base, $tag, $k, $ext))
          $k++
        }
        [System.IO.File]::Copy($srcAbs, $newDst, $false)
        $relNew = $newDst.Substring($RootDst.Length+1)
        $renameStream.WriteLine("$src`t$dst`t$relNew"); $renameStream.Flush()
        $state.renamed++
        $state.bytes += $size
      } else {
        [System.IO.File]::Copy($srcAbs, $dstAbs, $false)
        $state.copied++
        $state.bytes += $size
      }

      $doneStream.WriteLine($src); $doneStream.Flush()
      [void]$done.Add($src)
    } catch {
      $msg = $_.Exception.Message
      $errorStream.WriteLine("$src`t$dst`t$msg"); $errorStream.Flush()
      $state.errors++
    }

    if ($processed % 50 -eq 0) {
      $pct = [Math]::Round(100.0 * $done.Count / $total, 2)
      $gib = [Math]::Round($state.bytes / 1GB, 2)
      $elapsed = ((Get-Date) - $startTime).TotalSeconds
      $rate = if ($elapsed -gt 0) { [Math]::Round($processed / $elapsed, 1) } else { 0 }
      Write-Progress -Activity "Organizando F:\" -Status "$($done.Count)/$total ($pct%) cp=$($state.copied) sk=$($state.skipped) rn=$($state.renamed) er=$($state.errors) $gib GiB rate=$rate/s" -PercentComplete $pct
    }

    if (((Get-Date) - $lastSave).TotalSeconds -gt 10) {
      $state | ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8
      $lastSave = Get-Date
    }
  }
} finally {
  $state | ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8
  $skipStream.Close()
  $renameStream.Close()
  $errorStream.Close()
  $doneStream.Close()
  Write-Progress -Activity "Organizando F:\" -Completed
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " RESULTADOS" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Procesados en esta corrida : $processed"
Write-Host " Total done                  : $($done.Count) / $total"
Write-Host " Copiados                    : $($state.copied)"
Write-Host " Skipped (clones exactos)    : $($state.skipped)"
Write-Host " Renombrados (colisiones)    : $($state.renamed)"
Write-Host " Errores                     : $($state.errors)"
Write-Host " Bytes copiados              : $([Math]::Round($state.bytes / 1GB, 2)) GiB"
Write-Host ""
if ($done.Count -lt $total) {
  Write-Host "Aun quedan $($total - $done.Count) filas. Re-ejecuta el script para continuar." -ForegroundColor Yellow
} else {
  Write-Host "[OK] Copia completa." -ForegroundColor Green
  Write-Host "Para deduplicar clones cruzados ejecuta: Dedupe.ps1"
}
