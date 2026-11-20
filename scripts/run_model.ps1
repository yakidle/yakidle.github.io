$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$settings = Get-Content -Raw -LiteralPath (Join-Path $project 'settings.local.json') -Encoding UTF8 | ConvertFrom-Json
$root = [string]$settings.gpt_root
$python = Join-Path $root 'runtime\python.exe'
$api = Join-Path $root 'api_v2.py'
$official = Join-Path $root 'GPT_SoVITS\configs\tts_infer.yaml'
if (-not (Test-Path -LiteralPath $python)) { throw 'runtime\python.exe not found' }
if (-not (Test-Path -LiteralPath $api)) { throw 'api_v2.py not found' }
if (-not (Test-Path -LiteralPath $official)) { throw 'GPT_SoVITS/configs/tts_infer.yaml not found' }
$version = 'v2ProPlus'
if ($settings.model_version) { $version = [string]$settings.model_version }
if (@('v2ProPlus','v2Pro','v3','v4','v2') -notcontains $version) { throw 'Unsupported model_version. Choose v2ProPlus, v2Pro, v3, v4 or v2.' }
$yaml = [System.IO.File]::ReadAllText($official)
$pattern = '(?m)^' + [regex]::Escape($version) + ':\s*\r?\n(?<props>(?:^[ \t]+[^\r\n]*\r?\n?)*)'
$match = [regex]::Match($yaml, $pattern)
if (-not $match.Success) { throw "The official YAML does not contain preset $version. Check your installed GPT-SoVITS version." }
$props = $match.Groups['props'].Value
$props = [regex]::Replace($props, '(?m)^(\s+)device:\s*[^\r\n]+', '${1}device: cuda')
$props = [regex]::Replace($props, '(?m)^(\s+)is_half:\s*[^\r\n]+', '${1}is_half: true')
foreach ($field in @('t2s_weights_path','vits_weights_path')) {
  $pathMatch = [regex]::Match($props, '(?m)^\s+' + $field + ':\s*(?<p>[^\r\n#]+)')
  if (-not $pathMatch.Success) { throw "Model preset $version lacks $field" }
  $relative = $pathMatch.Groups['p'].Value.Trim().Trim('"').Trim("'") -replace '/', '\'
  $weight = Join-Path $root $relative
  if (-not (Test-Path -LiteralPath $weight)) { throw "Missing weight file: $weight" }
}
$private = Join-Path $project 'data\keke_tts_infer.yaml'
New-Item -ItemType Directory -Path (Split-Path -Parent $private) -Force | Out-Null
$content = "custom:`n" + $props.TrimEnd() + "`n"
[System.IO.File]::WriteAllText($private, $content, (New-Object System.Text.UTF8Encoding($false)))
Set-Location -LiteralPath $root
Write-Host "Xiaoyu voice model API starting: $version" -ForegroundColor Cyan
Write-Host 'API URL: http://127.0.0.1:9880' -ForegroundColor Green
Write-Host "Private model YAML: $private"
Write-Host 'Keep this window open. The model requires GPU memory.'
& $python -I api_v2.py -a 127.0.0.1 -p 9880 -c $private
if ($LASTEXITCODE -ne 0) { Write-Host 'Model API stopped or failed. Check the logs above.' -ForegroundColor Red; Read-Host 'Press Enter to close' }
