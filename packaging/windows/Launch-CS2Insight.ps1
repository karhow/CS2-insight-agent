#Requires -Version 5.1
# Launches the bundled backend; opens default browser once the web UI responds.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$appRoot = $PSScriptRoot
$Host.UI.RawUI.WindowTitle = "CS2 Insight Agent"
$py = Join-Path $appRoot "python\python.exe"
$wd = Join-Path $appRoot "backend"

$hostOnly = "127.0.0.1"
if ($env:CS2_INSIGHT_HOST) {
  $t = $env:CS2_INSIGHT_HOST.Trim()
  if ($t) { $hostOnly = $t }
}
$port = 8000
if ($env:CS2_INSIGHT_PORT) {
  $parsed = 0
  if ([int]::TryParse($env:CS2_INSIGHT_PORT, [ref]$parsed) -and $parsed -ge 1 -and $parsed -le 65535) {
    $port = $parsed
  }
}

$openUrl = "http://$($hostOnly):$port/"

if (-not (Test-Path $py)) {
  Write-Host "[CS2 Insight Agent] 未找到 python.exe: $py" -ForegroundColor Red
  Read-Host "按 Enter 退出"
  exit 1
}

$browserJob = Start-Job -ScriptBlock {
  param($Url)
  $ProgressPreference = "SilentlyContinue"
  $deadline = (Get-Date).AddSeconds(90)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    try {
      Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop | Out-Null
      Start-Process $Url
      break
    } catch {
    }
  }
} -ArgumentList $openUrl

try {
  Push-Location $wd
  & $py -m app.run_server
} finally {
  Pop-Location
  Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
  Get-Job -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
}
