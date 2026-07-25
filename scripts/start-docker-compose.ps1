$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $projectRoot "docker-compose.yml"

Set-Location $projectRoot

Write-Host "正在检查 Docker Desktop..."

$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$dockerPath = $null

if ($null -ne $dockerCommand) {
    $dockerPath = $dockerCommand.Source
}
elseif (Test-Path -LiteralPath "C:\Program Files\Docker\Docker\resources\bin\docker.exe") {
    $dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}

if ($null -eq $dockerPath) {
    throw "未找到 docker.exe，请先安装并启动 Docker Desktop。"
}

& $dockerPath info | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop 当前未正常运行。"
}

if (-not (Test-Path -LiteralPath $composeFile)) {
    throw "未找到 docker-compose.yml：$composeFile"
}

Write-Host "正在检查 Compose 配置..."
& $dockerPath compose -f $composeFile config -q

if ($LASTEXITCODE -ne 0) {
    throw "docker-compose.yml 配置检查失败。"
}

Write-Host "正在启动前后端容器..."
& $dockerPath compose -f $composeFile up -d --build

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose 启动失败。"
}

Write-Host "正在等待后端接口..."
$backendReady = $false

for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $response = Invoke-RestMethod `
            "http://127.0.0.1:8000/health" `
            -TimeoutSec 2

        if ($response.success) {
            $backendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    & $dockerPath compose -f $composeFile ps
    throw "后端接口未能在规定时间内启动。"
}

$frontend = Invoke-WebRequest `
    "http://127.0.0.1:5173/" `
    -UseBasicParsing `
    -TimeoutSec 5

if ($frontend.StatusCode -ne 200) {
    throw "前端页面访问失败。"
}

Write-Host ""
Write-Host "课程 Agent Docker 环境启动成功。" -ForegroundColor Green
Write-Host "前端：http://127.0.0.1:5173/"
Write-Host "后端文档：http://127.0.0.1:8000/docs"
Write-Host ""

& $dockerPath compose -f $composeFile ps
