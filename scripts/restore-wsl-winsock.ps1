$ErrorActionPreference = "Stop"

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
$administratorRole = [Security.Principal.WindowsBuiltInRole]::Administrator

if (-not $principal.IsInRole($administratorRole)) {
    throw "Run this script from an Administrator PowerShell window."
}

$registryBase = "HKLM\SYSTEM\CurrentControlSet\Services\WinSock2\Parameters\AppId_Catalog"

$entries = @(
    @("07761DD8", "C:\Program Files\WSL\wslg.exe"),
    @("1178A89F", "C:\Program Files\WSL\wsl.exe"),
    @("17C2AA53", "C:\Program Files\WSL\wslrelay.exe"),
    @("251585A4", "C:\Program Files\WSL\wslhost.exe"),
    @("34DD6A3A", "C:\Program Files\WSL\wslservice.exe")
)

foreach ($entry in $entries) {
    $entryName = $entry[0]
    $wslPath = $entry[1]
    $registryKey = "$registryBase\$entryName"

    if (-not (Test-Path -LiteralPath $wslPath)) {
        throw "WSL file not found: $wslPath"
    }

    & reg.exe ADD $registryKey /f | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create registry key: $registryKey"
    }

    & reg.exe ADD $registryKey /v AppFullPath /t REG_SZ /d $wslPath /f | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to write AppFullPath: $registryKey"
    }

    & reg.exe ADD $registryKey /v PermittedLspCategories /t REG_DWORD /d 0x80000000 /f | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to write PermittedLspCategories: $registryKey"
    }
}

Write-Host "WSL2 Winsock exclusions written. Readback follows." -ForegroundColor Green

foreach ($entry in $entries) {
    $registryKey = "$registryBase\$($entry[0])"
    Write-Host "[$($entry[0])]"
    & reg.exe QUERY $registryKey /v AppFullPath
    & reg.exe QUERY $registryKey /v PermittedLspCategories
}

Write-Host "Done. Restart Windows, then test WSL and Docker Desktop." -ForegroundColor Green
