#Requires -Version 5.1
param(
  [Parameter(Mandatory = $true)]
  [string] $AppRoot
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$VerbosePreference = "SilentlyContinue"
$InformationPreference = "SilentlyContinue"
$AppRoot = (Resolve-Path $AppRoot).Path
$metaPath = Join-Path $PSScriptRoot "ffmpeg-redist.json"
if (-not (Test-Path $metaPath)) {
  $metaPath = Join-Path $AppRoot "scripts\ffmpeg-redist.json"
}
$meta = Get-Content $metaPath -Raw | ConvertFrom-Json
$tmp = Join-Path $env:TEMP ("cs2insight-ff-" + [Guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$zipPath = Join-Path $tmp "ffmpeg.zip"

function Download-FileQuiet([string]$Uri, [string]$DestPath) {
  $curl = Join-Path $env:SystemRoot "System32\curl.exe"
  if (Test-Path -LiteralPath $curl) {
    # -s: no progress meter (avoids extra console output during Inno [Run])
    & $curl -fsSL --connect-timeout 30 --max-time 0 --retry 2 --retry-delay 1 -o $DestPath $Uri
    if ($LASTEXITCODE -ne 0) { throw "curl 下载失败，退出码: $LASTEXITCODE" }
    return
  }
  $wc = New-Object System.Net.WebClient
  try {
    $wc.Headers.Add("User-Agent", "CS2-Insight-Agent-FFmpeg-Installer/1.0")
    $wc.DownloadFile($Uri, $DestPath)
  } finally {
    $wc.Dispose()
  }
}

function Expand-ZipQuiet([string]$ZipPath, [string]$DestDir) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $DestDir)
}

try {
  Write-Host "[CS2 Insight Agent] 正在下载 FFmpeg（可选组件），请稍候…"
  Download-FileQuiet -Uri $meta.zip_url -DestPath $zipPath
  Write-Host "[CS2 Insight Agent] 正在校验文件完整性…"
  $hash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($hash -ne $meta.sha256.ToLowerInvariant()) {
    throw "FFmpeg zip SHA256 mismatch: expected $($meta.sha256) got $hash"
  }
  Write-Host "[CS2 Insight Agent] 正在解压并安装到程序目录…"
  $extractRoot = Join-Path $tmp "extract"
  New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
  Expand-ZipQuiet -ZipPath $zipPath -DestDir $extractRoot
  $srcFf = Join-Path $extractRoot ($meta.zip_relative_ffmpeg -replace "/", "\")
  $srcFb = Join-Path $extractRoot ($meta.zip_relative_ffprobe -replace "/", "\")
  if (-not (Test-Path $srcFf)) { throw "ffmpeg.exe not found at $srcFf" }
  if (-not (Test-Path $srcFb)) { throw "ffprobe.exe not found at $srcFb" }
  $outDir = Join-Path $AppRoot "third_party\ffmpeg"
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
  Copy-Item $srcFf (Join-Path $outDir "ffmpeg.exe") -Force
  Copy-Item $srcFb (Join-Path $outDir "ffprobe.exe") -Force
} finally {
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
Write-Host "[CS2 Insight Agent] FFmpeg 已安装到: $outDir"
