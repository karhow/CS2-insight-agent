#Requires -Version 5.1
param(
  [Parameter(Mandatory = $true)]
  [string] $Version
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$out = Join-Path $root "backend\app\release_version.txt"
$v = $Version.Trim().TrimStart("v")
if (-not $v) { throw "Empty version" }
Set-Content -LiteralPath $out -Value $v -Encoding utf8 -NoNewline
Write-Host "Wrote $out <= $v"
