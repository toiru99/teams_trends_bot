# =============================================================================
# Hermes Agent — AI Trends -> Teams  (Windows 부트스트랩, 네이티브)
#
# 사용법 (PowerShell):
#     .\bin\bootstrap-win.ps1
#
# 하는 일:
#   1) 이 repo 폴더를 HERMES_HOME 으로 지정 (현재 세션 + 사용자 영구 환경변수)
#   2) Hermes 미설치 시 공식 설치
#   3) .env 존재 확인
#   4) 브라우저 도구(agent-browser) 설치
#   5) 다음 단계 안내
#
# 참고: Windows 네이티브 Hermes 는 공식적으로 "experimental" 입니다. cron/게이트웨이를
#       장시간 안정적으로 돌리려면 WSL2 안에서 bin/bootstrap-mac.sh 를 쓰는 방법이 더
#       안정적입니다. (README 의 "Windows: WSL2 경로" 참고)
# =============================================================================
$ErrorActionPreference = "Stop"

# repo 루트 = 이 스크립트(bin\)의 상위 폴더
$Here = Split-Path -Parent $PSScriptRoot
$HistPath = Join-Path $Here "trend_history.jsonl"

$env:HERMES_HOME = $Here
$env:TREND_HISTORY_PATH = $HistPath
# 영구(현재 사용자) — 새 터미널/게이트웨이에서도 유지
setx HERMES_HOME "$Here"        | Out-Null
setx TREND_HISTORY_PATH "$HistPath" | Out-Null

Write-Host "==> HERMES_HOME = $Here"
Write-Host "==> TREND_HISTORY_PATH = $HistPath"

# 1) Hermes 설치 확인
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
  Write-Host "[*] Hermes 미설치 — 공식 설치 진행"
  iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
} else {
  Write-Host "[*] Hermes 설치됨"
}

# 2) .env 확인
if (-not (Test-Path (Join-Path $Here ".env"))) {
  Write-Host ""
  Write-Host "[!] .env 가 없습니다. 아래로 만든 뒤 FIREWORKS_API_KEY / TEAMS_WEBHOOK_URL 을 채우세요:"
  Write-Host "      Copy-Item `"$Here\.env.example`" `"$Here\.env`""
  Write-Host "    그런 다음 다시 .\bin\bootstrap-win.ps1 실행."
  exit 1
}

# 3) 브라우저 도구
if (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host "[*] agent-browser 설치 시도"
  npm install -g agent-browser
} else {
  Write-Host "[!] npm 없음 — 브라우저 도구는 나중에 'npm i -g agent-browser'"
}

# 4) 진단
Write-Host "[*] hermes doctor"
hermes doctor

Write-Host ""
Write-Host "──────────────────────────────────────────────────────────────"
Write-Host "다음 단계:"
Write-Host "  1) hermes tools        # browser / code / web 켜기"
Write-Host "  2) hermes              # 대화로 ai-trends-filter 점검"
Write-Host "  3) 매일 11:50 KST 등록 (시간대는 'hermes cron list' 로 확인):"
Write-Host "       hermes cron create `"50 11 * * *`" `"ai-trends-filter 스킬로 오늘 AI 트렌드를 큐레이션하고 Teams 에 게시`" --skill ai-trends-filter"
Write-Host "       # UTC 기준이면 02:50 UTC -> `"50 2 * * *`""
Write-Host "  4) hermes gateway      # cron tick 위해 상주"
Write-Host "──────────────────────────────────────────────────────────────"
