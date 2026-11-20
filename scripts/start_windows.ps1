$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$config = Join-Path $root 'settings.local.json'
Write-Host ''
Write-Host '===== Xiaoyu Loves Keke / GPT-SoVITS =====' -ForegroundColor Green
Write-Host 'This package contains website + gateway, but not GPT-SoVITS model/weights.'

if (-not (Test-Path -LiteralPath $config)) {
  while ($true) {
    $gpt = (Read-Host 'Enter GPT-SoVITS integrated package directory, e.g. D:\GPT-SoVITS').Trim().Trim('"')
    if ((Test-Path -LiteralPath (Join-Path $gpt 'runtime\python.exe')) -and (Test-Path -LiteralPath (Join-Path $gpt 'api_v2.py'))) { break }
    Write-Host 'Incorrect directory. It needs runtime\python.exe and api_v2.py' -ForegroundColor Yellow
  }
  $arr = New-Object byte[] 24
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($arr) } finally { $rng.Dispose() }
  $admin = -join ($arr | ForEach-Object { $_.ToString('x2') })
  $arr2 = New-Object byte[] 24
  $rng2 = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng2.GetBytes($arr2) } finally { $rng2.Dispose() }
  $listener = -join ($arr2 | ForEach-Object { $_.ToString('x2') })
  $settings = [ordered]@{
    gpt_root = $gpt
    admin_key = $admin
    listener_key = $listener
    sovits_url = 'http://127.0.0.1:9880'
    allowed_origins = @('http://127.0.0.1:7865', 'http://localhost:7865', 'https://yakidle.github.io')
  }
  $settings | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $config -Encoding UTF8
  Write-Host 'Created private settings.local.json. NEVER upload to GitHub.' -ForegroundColor Green
}

$s = Get-Content -Raw -LiteralPath $config -Encoding UTF8 | ConvertFrom-Json
$python = Join-Path ([string]$s.gpt_root) 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'GPT runtime\python.exe not found. Edit settings.local.json.' }
Write-Host ''
Write-Host 'ADMIN key: use only at /admin/; never share it:' -ForegroundColor Yellow
Write-Host ([string]$s.admin_key) -ForegroundColor Green
Write-Host ''
Write-Host 'LISTENER code: only share with Keke (for generating new audio):' -ForegroundColor Yellow
Write-Host ([string]$s.listener_key) -ForegroundColor Green
Write-Host ''

foreach ($pair in @(@(9880,'run_model.ps1'), @(7865,'run_web.ps1'))) {
  $port = [int]$pair[0]
  $scriptName = [string]$pair[1]
  $client = $null
  try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1',$port) } catch {}
  if ($client) {
    $client.Close()
    if ($port -eq 7865) {
      try {
        $check = Invoke-RestMethod -Uri 'http://127.0.0.1:7865/api/status' -TimeoutSec 3
        if ($check.app -ne 'xiaoyu-keke') { throw 'Wrong service' }
      } catch {
        throw 'Port 7865 is in use by another program (possibly the previous VoiceStudio). Close it, then run this script again.'
      }
    }
    Write-Host "Port $port is already in use. Reusing the existing service." -ForegroundColor Yellow
  } else {
    $scriptPath = Join-Path $PSScriptRoot $scriptName
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $scriptPath + '"')) -WorkingDirectory $root | Out-Null
    Write-Host "Started service port $port" -ForegroundColor Cyan
  }
}
Write-Host ''
Write-Host 'Local site: http://127.0.0.1:7865' -ForegroundColor Green
Write-Host 'Management: http://127.0.0.1:7865/admin/' -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:7865'
Write-Host 'For external users run START_TUNNEL.bat or a named Cloudflare Tunnel.'
