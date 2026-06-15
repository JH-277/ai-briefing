#Requires -Version 5.1
<#
.SYNOPSIS
  AI 개념 브리핑 Loop — Cursor Agent 주기적 깨우기

.DESCRIPTION
  config/settings.json 의 loop_interval_hours 를 읽어 백그라운드 루프를 시작합니다.
  Cursor 채팅에서 /loop 와 동일한 역할을 PowerShell로 수행합니다.

  사용법 (Cursor Agent에게 요청):
    "scripts/start_loop.ps1 로 루프 시작해줘"

  또는 터미널:
    powershell -ExecutionPolicy Bypass -File scripts/start_loop.ps1
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SettingsPath = Join-Path $Root "config\settings.json"

if (-not (Test-Path $SettingsPath)) {
    Write-Error "config/settings.json 이 없습니다."
}

$settings = Get-Content $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$hours = [int]$settings.loop_interval_hours
if ($hours -lt 1) { $hours = 24 }
$seconds = $hours * 3600

$prompt = @'
prompts/loop_briefing.md 지시문을 따르세요. 다음 순서로 한 턴에 모두 수행: (1) python scripts/topic_manager.py next 로 주제 확인 (2) 웹 검색 후 briefings/{id}-{날짜}.md 작성 (3) python scripts/send_kakao.py --file 로 카카오 전송 (4) python scripts/topic_manager.py complete 로 상태 갱신 (5) 결과 한 줄 보고.
'@

$promptJson = ($prompt -replace '\\', '\\\\' -replace '"', '\"')

Write-Host "=== AI 개념 브리핑 Loop ===" -ForegroundColor Cyan
Write-Host "간격: ${hours}시간 (${seconds}초)"
Write-Host "프로젝트: $Root"
Write-Host ""
Write-Host "첫 브리핑은 지금 1회 실행하세요 (Cursor Agent에게 loop_briefing.md 실행 요청)."
Write-Host "이후 ${hours}시간마다 AGENT_LOOP_TICK 신호가 발생합니다."
Write-Host "중지: Ctrl+C"
Write-Host ""

# 첫 틱 전에 1회 즉시 실행 신호 (Agent가 수동으로 먼저 돌릴 수 있도록 안내만)
Start-Sleep -Seconds 2

while ($true) {
    Start-Sleep -Seconds $seconds
    $payload = "{`"prompt`":`"$promptJson`"}"
    Write-Output "AGENT_LOOP_TICK_ai_briefing $payload"
}
