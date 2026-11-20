$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$settings = Get-Content -Raw -LiteralPath (Join-Path $project 'settings.local.json') -Encoding UTF8 | ConvertFrom-Json
$root = [string]$settings.gpt_root
$python = Join-Path $root 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '找不到 GPT-SoVITS 自带的 Python 解释器。' }
Set-Location -LiteralPath $project
Write-Host '网页服务运行中，本窗口请勿关闭。' -ForegroundColor Cyan
& $python (Join-Path $project 'server\gateway.py')
