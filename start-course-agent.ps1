$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "web"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot
$env:PYTHONUTF8 = "1"
$env:OPENAI_AGENTS_DISABLE_TRACING = "1"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "错误：未找到虚拟环境：$pythonExe" -ForegroundColor Red
    Write-Host "请先运行 .\run-agent.ps1 创建虚拟环境并安装后端依赖。"
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "package.json"))) {
    Write-Host "错误：未找到前端项目：$frontendRoot" -ForegroundColor Red
    exit 1
}

if ($null -eq (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Write-Host "错误：未找到 npm.cmd，请先安装 Node.js。" -ForegroundColor Red
    exit 1
}

 $backendCommand = 'cd /d "' + $projectRoot + '" && "' + $pythonExe + '" -m uvicorn server:app --host 127.0.0.1 --port 8000'
 $frontendCommand = 'cd /d "' + $frontendRoot + '" && npm.cmd run dev -- --host 127.0.0.1'

Write-Host "正在启动后端：http://127.0.0.1:8000" -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" `
    -WorkingDirectory $projectRoot `
    -ArgumentList @(
        "/k",
        $backendCommand
    )

Write-Host "正在启动前端：Vite 将自动选择可用端口" -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" `
    -WorkingDirectory $frontendRoot `
    -ArgumentList @(
        "/k",
        $frontendCommand
    )

Write-Host ""
Write-Host "前后端已分别启动。请查看新窗口中的 Vite 地址，再用浏览器打开。" -ForegroundColor Green
Write-Host "后端 API： http://127.0.0.1:8000/docs"
