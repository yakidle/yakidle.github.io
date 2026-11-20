$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$settings = Get-Content -Raw -LiteralPath (Join-Path $project 'settings.local.json') -Encoding UTF8 | ConvertFrom-Json
$root = [string]$settings.gpt_root
$python = Join-Path $root 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '无法找到 GPT-SoVITS 自带的 runtime\python.exe' }
Set-Location -LiteralPath $root
Write-Host 'GPT-SoVITS 模型 API 运行中，本窗口请勿关闭。' -ForegroundColor Cyan
Write-Host 'API 地址: http://127.0.0.1:9880' -ForegroundColor Green
& $python -I api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
if ($LASTEXITCODE -ne 0) { Write-Host '模型服务退出。检查预训练模型和权重是否安装完整。' -ForegroundColor Red }
