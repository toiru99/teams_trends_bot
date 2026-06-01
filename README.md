# AI Trends → Teams (Hermes Agent)

매일 외부 AI 트렌드 소스를 **에이전틱하게 조사**해서, 팀에 의미 있는 후보 1~3건을 골라
Microsoft Teams 채널에 **AdaptiveCard 로 자동 게시**하는 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 세팅.

- **조사**: GitHub Trending · HuggingFace Papers · arXiv · OpenAI/Anthropic 발표 등을 Hermes 가
  스스로 훑고, 차단되면 fallback 레시피로 우회하고, **페이지를 직접 열어 검증**하며 점수화 → Top 1~3 선별.
- **게시**: 단방향. Teams 의 **Workflows(Power Automate) 웹훅 URL** 로 POST. (봇·양방향 아님)
- **진화**: Hermes 의 self-improving 스킬 구조 — 실행하며 `skills/ai-trends-filter/references/` 의
  스크래핑 노하우를 스스로 갱신. 그 변화를 git 으로 버전 관리.

> **이 저장소 폴더 = Hermes 의 `HERMES_HOME`** (두뇌: 설정·스킬·이력·cron).
> USB 에 통째로 담아 다니고, 각 PC 에는 Hermes 런타임만 1회 설치한 뒤 `HERMES_HOME` 을 이 폴더로 가리킵니다.
> (Python venv 등 런타임은 OS 마다 달라 USB 로 옮길 수 없으므로 "두뇌만 이동" 구조)

---

## 0. 사전 준비 — 시크릿 2개

`.env.example` 를 `.env` 로 복사하고 두 값을 채웁니다. **`.env` 는 git 에 안 올라갑니다.**

| 키 | 설명 |
|---|---|
| `FIREWORKS_API_KEY` | [Fireworks AI](https://fireworks.ai) API 키. Kimi K2.6 호출용. |
| `TEAMS_WEBHOOK_URL` | Teams Workflows 웹훅 URL (아래 5번에서 발급). `https://default...` 로 시작하는 게 정상. |

```bash
# macOS / Linux
cp .env.example .env && ${EDITOR:-nano} .env
```
```powershell
# Windows (PowerShell)
Copy-Item .env.example .env ; notepad .env
```

---

## 1. macOS / Linux 에서 실행

```bash
# 저장소(또는 USB의 이 폴더)로 이동 후:
source bin/bootstrap-mac.sh
```
스크립트가 ① `HERMES_HOME` 지정 ② Hermes 설치(없으면) ③ `.env` 확인 ④ `agent-browser` 설치
⑤ 다음 단계 안내까지 처리합니다. 이후 안내대로:

```bash
hermes tools     # browser / code / web 활성화 (최초 1회)
hermes           # 대화로 점검: "ai-trends-filter 로 오늘 트렌드 큐레이션해줘"
# 매일 11:50 KST 자동 실행 등록 (시간대는 'hermes cron list' 로 확인)
hermes cron create "50 11 * * *" \
  "ai-trends-filter 스킬을 실행해 오늘의 AI 트렌드를 큐레이션하고 채택 건을 Teams 에 AdaptiveCard 로 게시하라" \
  --skill ai-trends-filter
hermes gateway   # cron tick 위해 상주 (또는: hermes gateway install)
```

---

## 2. Windows 에서 실행 — 두 가지 경로

### 경로 A — WSL2 (권장, 가장 안정적)
Windows 네이티브 Hermes 는 공식적으로 *experimental* 이고, 과거 이 작업에서 **네이티브 Windows 의
cron 루프가 멈춘(hang) 사례**가 있었습니다. 상시 자동 실행을 돌릴 거면 WSL2 가 안전합니다.

```powershell
wsl --install            # 최초 1회 (재부팅 필요할 수 있음)
```
WSL2(Ubuntu) 터미널에서 이 폴더로 이동 후 — USB 는 보통 `/mnt/<드라이브>/...` 로 보입니다:
```bash
cd /mnt/e/heremes_setting   # 예: USB 가 E: 드라이브일 때
source bin/bootstrap-mac.sh # 이후는 macOS 절차와 동일
```
- 브라우저로 "페이지 직접 열기"를 쓸 때, Chrome 이 Windows 호스트에 있으면
  WSL 안 Hermes 에서 `/browser connect` 로 호스트 Chrome 에 붙입니다. (Hermes 공식 권장)

### 경로 B — Windows 네이티브 (간단하지만 experimental)
```powershell
.\bin\bootstrap-win.ps1
```
스크립트가 `HERMES_HOME`(영구) 지정 + Hermes 설치 + `.env` 확인 + `agent-browser` 설치를 처리합니다.
이후 `hermes tools` → `hermes` → `hermes cron create ...` → `hermes gateway` 순서는 동일.

> 네이티브에서 cron 루프가 멈추면 경로 A(WSL2)로 전환하세요.

---

## 3. 스케줄(cron) 시간대 주의

`hermes cron create "50 11 * * *" ...` 의 `50 11` 이 **로컬 시각인지 UTC 인지** 환경마다 다를 수 있습니다.
등록 직후 반드시 확인:
```bash
hermes cron list
```
- 로컬(KST) 기준이면 그대로 11:50.
- UTC 기준이면 11:50 KST = **02:50 UTC** → `"50 2 * * *"` 로 다시 등록.

---

## 4. 로컬 검증 (게시 파이프라인만 따로 테스트)

LLM·cron 없이 Teams 게시가 되는지 먼저 확인하고 싶을 때:
```bash
export TEAMS_WEBHOOK_URL="https://default...."   # .env 값과 동일
python skills/ai-trends-filter/scripts/post_to_teams.py \
  "🧪 연결 테스트" "이 카드가 보이면 웹훅 연결 정상" \
  --source-url https://example.com/test --summary "webhook smoke test"
```
HTTP 202 가 나오고 채널에 카드가 뜨면 성공. (테스트 카드는 이력에 🧪 로 남으니 나중에 정리)

---

## 5. Teams Workflows 웹훅 URL 만들기

Microsoft 가 기존 *Incoming Webhook 커넥터*를 폐기 중이라, 현재 권장 방식은 **Workflows(Power Automate)** 입니다.

1. Teams → 게시할 **채널** → `⋯` → **Workflows**
2. 템플릿 **"Post to a channel when a webhook request is received"** (웹훅 요청이 오면 채널에 게시) 선택
3. 채널 지정 후 생성 → 발급된 **HTTP POST URL** 복사
4. 그 URL 을 `.env` 의 `TEAMS_WEBHOOK_URL` 에 붙여넣기 (`https://default...` 로 시작 = 정상)

> 채널을 바꾸려면 `.env` 의 한 줄만 교체하고 게이트웨이를 재시작하면 됩니다.

---

## 6. lab_context.md 를 꼭 채우세요 (채택률 좌우)

[`lab_context.md`](./lab_context.md) 가 **예시(템플릿)만** 들어있으면 "진행 과제 매핑" 점수가 0 이 되어
후보가 거의 다 탈락합니다. **현재 진행 중인 실제 과제·사내 도구·시한 결정**을 3개 이상 채워 넣으세요.

---

## 7. USB 로 옮기기 & 다른 PC 에서 복원

- 이 폴더를 USB 에 통째로 복사 → 다른 PC 에서 그 폴더로 이동 후 위 1·2 절차 그대로.
- `HERMES_HOME` 은 부트스트랩이 **폴더 위치 기준으로 자동 계산**하므로 드라이브 문자(E:, /Volumes/…)가 달라도 동작.
- 단, **Hermes 런타임·`agent-browser` 는 PC 마다 1회 설치** 필요(부트스트랩이 자동 처리).

---

## 8. GitHub (private) 백업

```bash
git init && git add . && git commit -m "Initial: Hermes AI-trends→Teams 세팅"
# GitHub CLI 사용 시:
gh repo create <레포명> --private --source=. --push
```
- `.env`·`auth.json`·`sessions/`·`*.db`·`cron/output/` 는 `.gitignore` 로 자동 제외됩니다.
- 커밋되는 것: `config.yaml`, `skills/`(SKILL.md·post_to_teams.py·진화하는 references), `lab_context.md`,
  `trend_history.jsonl`(dedup 메모리), 부트스트랩, 이 README.

---

## 디렉터리 구조

```
heremes_setting/                 ← git repo = HERMES_HOME (USB 상주)
├── config.yaml                  # Fireworks Kimi K2.6 + (hermes tools 로) toolset
├── .env                         # 🔒 시크릿 (gitignore)
├── .env.example                 # 템플릿
├── skills/ai-trends-filter/
│   ├── SKILL.md                 # 필터·카드 spec = LLM system prompt (단일 소스)
│   ├── scripts/post_to_teams.py # Teams 게시 + 이력 append
│   └── references/*.md          # 스크래핑 레시피 (자가학습으로 진화)
├── lab_context.md               # ★실제 과제로 채울 것
├── trend_history.jsonl          # dedup 이력 (7일)
├── cron/                        # hermes cron 잡 (등록 시 jobs.json 생성)
├── bin/bootstrap-mac.sh         # macOS/Linux/WSL2 부트스트랩
├── bin/bootstrap-win.ps1        # Windows 네이티브 부트스트랩
└── handoff-bundle/              # (원본 인계 문서 — 출처/참고용, 런타임 미사용)
```

## 절대 하지 말 것 (이전 학습 손실 방지)
- `post_to_teams.py` 에 `WEBHOOK_URL.startswith('https://default')` 같은 placeholder 검증 추가 금지.
- `.env` 내용을 콘솔 출력하거나 코드에 인용 금지.
- 카드 bullet 을 1~2줄로 짧게 압축 금지 (7~10 bullet, 100~300자 — 처음 보는 사람이 트렌드를 이해할 분량).
- 채택 후보를 찾고도 `post_card` 호출 없이 종료 금지 (분석만 = 작업 실패).
