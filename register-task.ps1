# Register the headless Remote Controller agent to start before user logon.
# Run this script once from an elevated PowerShell prompt, or let it request elevation.

$ErrorActionPreference = "Stop"

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe `
        -Verb RunAs `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$PSCommandPath`""
        )
    exit
}

$AgentRepo = $PSScriptRoot
$AgentFile = Join-Path $AgentRepo "agent.py"
if (-not (Test-Path -LiteralPath $AgentFile)) {
    throw "agent.py를 찾을 수 없습니다: $AgentFile"
}

# Resolve Python while registering the task, then store its absolute path.
# This avoids relying on SYSTEM's PATH at boot time.
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand -or -not (Test-Path -LiteralPath $pythonCommand.Source)) {
    $pythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
}
if ($null -eq $pythonCommand) {
    throw "Python을 찾을 수 없습니다. Python 설치 후 다시 실행하세요."
}

$AgentPython = $pythonCommand.Source
$PythonArguments = if ([IO.Path]::GetFileName($AgentPython) -ieq "py.exe") {
    "-3 `"$AgentFile`" --port 8765"
} else {
    "`"$AgentFile`" --port 8765"
}

$Action = New-ScheduledTaskAction `
    -Execute $AgentPython `
    -Argument $PythonArguments `
    -WorkingDirectory $AgentRepo

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName "RemoteControllerAgent" `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Force | Out-Null

$FirewallRuleName = "RemoteController-Agent-8765"
if (Get-NetFirewallRule -Name $FirewallRuleName -ErrorAction SilentlyContinue) {
    Enable-NetFirewallRule -Name $FirewallRuleName
    Set-NetFirewallRule -Name $FirewallRuleName -Profile Any
} else {
    New-NetFirewallRule `
        -Name $FirewallRuleName `
        -DisplayName "Remote Controller Agent (8765)" `
        -Enabled True `
        -Direction Inbound `
        -Protocol TCP `
        -Action Allow `
        -LocalPort 8765 `
        -Profile Any | Out-Null
}

Write-Host "RemoteControllerAgent 작업을 등록했습니다." -ForegroundColor Green
Write-Host "TCP 8765 인바운드 방화벽 규칙을 확인했습니다."
Write-Host "저장소: $AgentRepo"
Write-Host "Python: $AgentPython"
Write-Host "부팅 후 포트: 8765"
Write-Host "즉시 테스트: Start-ScheduledTask -TaskName RemoteControllerAgent"
