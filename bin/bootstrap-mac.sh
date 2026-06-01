#!/usr/bin/env bash
# =============================================================================
# Hermes Agent — AI Trends → Teams  (macOS / Linux 부트스트랩)
#
# 사용법 (반드시 source 로 실행 — 환경변수가 현재 셸에 유지되도록):
#     source bin/bootstrap-mac.sh
#
# 하는 일:
#   1) 이 repo 폴더를 HERMES_HOME 으로 지정 (Hermes 의 모든 데이터/스킬/cron 이 여기 상주)
#   2) Hermes 미설치 시 공식 설치
#   3) .env 존재 확인
#   4) 브라우저 도구(agent-browser) 설치
#   5) 다음 단계 안내 출력
# =============================================================================
set -uo pipefail

# repo 루트 = 이 스크립트의 상위 폴더
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export HERMES_HOME="$HERE"
export TREND_HISTORY_PATH="$HERMES_HOME/trend_history.jsonl"

echo "==> HERMES_HOME = $HERMES_HOME"
echo "==> TREND_HISTORY_PATH = $TREND_HISTORY_PATH"

# 1) Hermes 설치 확인
if ! command -v hermes >/dev/null 2>&1; then
  echo "[*] Hermes 미설치 — 공식 설치 진행"
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  # PATH 갱신
  source "$HOME/.zshrc"  2>/dev/null || true
  source "$HOME/.bashrc" 2>/dev/null || true
else
  echo "[*] Hermes 설치됨: $(command -v hermes)"
fi

# 2) .env 확인
if [ ! -f "$HERMES_HOME/.env" ]; then
  echo ""
  echo "[!] .env 가 없습니다. 아래로 만든 뒤 FIREWORKS_API_KEY / TEAMS_WEBHOOK_URL 을 채우세요:"
  echo "      cp \"$HERMES_HOME/.env.example\" \"$HERMES_HOME/.env\""
  echo "    그런 다음 다시 'source bin/bootstrap-mac.sh' 실행."
  return 1 2>/dev/null || exit 1
fi

# 3) 브라우저 도구(페이지 직접 열기)
if ! command -v agent-browser >/dev/null 2>&1; then
  echo "[*] agent-browser 설치 시도 (npm)"
  npm install -g agent-browser || echo "[!] npm 없음/실패 — 브라우저 도구는 나중에 'npm i -g agent-browser'"
fi

# 4) 진단
echo "[*] hermes doctor"
hermes doctor || true

cat <<'EOF'

──────────────────────────────────────────────────────────────────────────────
다음 단계 (이 셸에서 그대로 이어서):

  1) 도구 활성화 (최초 1회)
       hermes tools           # browser / code / web 켜기

  2) 동작 점검 (대화형)
       hermes
       # "ai-trends-filter 스킬로 오늘 트렌드 한 번 큐레이션해줘" 라고 시켜보기

  3) 매일 11:50 KST 자동 실행 등록  (스케줄 시간대는 'hermes cron list' 로 꼭 확인)
       hermes cron create "50 11 * * *" \
         "ai-trends-filter 스킬을 실행해 오늘의 AI 트렌드를 큐레이션하고 채택 건을 Teams 에 AdaptiveCard 로 게시하라" \
         --skill ai-trends-filter
       # 스케줄러가 UTC 기준이면 11:50 KST = 02:50 UTC → "50 2 * * *" 로 등록

  4) 게이트웨이 상주 (cron 이 돌려면 떠 있어야 함)
       hermes gateway          # 포그라운드
       # 또는 서비스 등록:  hermes gateway install

주의: HERMES_HOME 이 이 셸에만 설정돼 있습니다. 새 터미널에서 hermes 를 쓰려면
      다시 'source bin/bootstrap-mac.sh' 하거나, 셸 프로필(~/.zshrc)에
      export HERMES_HOME="<이 폴더 경로>" 를 추가하세요.
──────────────────────────────────────────────────────────────────────────────
EOF
