#Requires -Version 5.1
<#
  매일 지정 시각(기본 07:30)에 Cursor Agent를 깨우는 Loop.
  config/settings.json 의 daily_time 사용 (PC 로컬 시간).
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SettingsPath = Join-Path $Root "config\settings.json"
$settings = Get-Content $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$timeStr = if ($settings.daily_time) { $settings.daily_time } else { "07:30" }
$parts = $timeStr -split ":"
$targetHour = [int]$parts[0]
$targetMinute = [int]$parts[1]

function Get-SecondsUntilNextRun {
    $now = Get-Date
    $next = Get-Date -Hour $targetHour -Minute $targetMinute -Second 0
    if ($next -le $now) {
        $next = $next.AddDays(1)
    }
    return [int](($next - $now).TotalSeconds), $next
}

$prompt = @'
prompts/loop_briefing.md 지시문을 따르세요. (1) topic_manager next (2) briefings 작성 (3) send_kakao.py 전송 (4) topic_manager complete (5) 결과 보고.
'@
$promptJson = ($prompt -replace '\\', '\\\\' -replace '"', '\"')

Write-Host "=== AI 개념 일일 브리핑 ($timeStr) ===" -ForegroundColor Cyan
Write-Host "프로젝트: $Root"
Write-Host "PC 로컬 시간 기준 매일 ${timeStr}에 실행됩니다."
Write-Host "Cursor가 켜져 있어야 Agent가 동작합니다."
Write-Host "중지: Ctrl+C"
Write-Host ""

while ($true) {
    $sec, $nextRun = Get-SecondsUntilNextRun
    Write-Host ("다음 실행: {0} ({1}초 후)" -f $nextRun.ToString("yyyy-MM-dd HH:mm"), $sec)
    Start-Sleep -Seconds $sec
    $payload = "{`"prompt`":`"$promptJson`"}"
    Write-Output "AGENT_LOOP_TICK_ai_briefing $payload"
}
