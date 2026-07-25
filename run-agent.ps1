$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot

$env:PYTHONUTF8 = "1"
$env:OPENAI_AGENTS_DISABLE_TRACING = "1"

# 当前进程没有密钥时，主动读取用户级环境变量
if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    $env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable(
        "DEEPSEEK_API_KEY",
        "User"
    )
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "未找到虚拟环境，正在创建……"
    py -m venv .venv

    Write-Host "正在安装项目依赖……"
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
}

if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    Write-Host ""
    Write-Host "错误：尚未设置 DEEPSEEK_API_KEY。"
    Write-Host "请在 PowerShell 中执行以下命令："
    Write-Host '[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "你的DeepSeek API Key", "User")'
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "正在启动课程与项目管理 Agent……"
Write-Host ""

& ".venv\Scripts\python.exe" app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Agent 异常退出，退出代码：$LASTEXITCODE"
    Read-Host "按回车键退出"
}