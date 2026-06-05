---
name: ai-trends-filter
description: AI 랩·팀의 현재 관심사에 맞춰 GitHub trending / arXiv / 모델 출시 노트 / 산업 발표 등 외부 AI 트렌드 후보를 필터링하고, 채택된 항목을 Microsoft Teams 채널에 AdaptiveCard로 게시한다. 매일 11:50 KST (Asia/Seoul, AM) Hermes cron 으로 실행.
version: 0.5.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [AI-Trends, Monitoring, Teams, Cron, Curation]
prerequisites:
  packages: [requests]
---

# AI Trends Filter — 관심사 기반 Teams 큐레이션

## 목적

매일 Microsoft Teams "AI Trends" 채널에 게시되는 트렌드 항목을 **팀의 현재 관심사** 기준으로 골라낸다. 화제성이 아니라 **우리가 지금 하는 일에 직결되는가** 가 유일한 기준이다.

## 자동 실행 (Hermes Cron)

- **스케줄**: 매일 11:50 KST (Asia/Seoul, AM) — `hermes cron` 으로 등록
- **출력 채널**: Microsoft Teams "AI Trends" 채널 (Power Automate workflow webhook)
- **하루 게재 한도**: 최대 3건. 채택 후보가 0건이면 빈 카드 보내지 말 것.
- **카드 단위**: 1 채택 항목 = 1 카드. 여러 건 채택 시 카드 N개를 각각 따로 게시.
- **중복 차단 (2단)**:
  1. **URL dedup** — 지난 7일 이력에 같은 1차 출처(URL) 있으면 폐기 (자동·기계적)
  2. **의미 dedup** — URL 이 달라도 핵심 사실이 같으면 폐기 (LLM 판단). 예: HF Papers / arxiv / 공식 블로그가 같은 release 를 보도하는 경우. 게시 이력의 `summary` 와 후보 핵심 한줄을 비교.
- **이력 파일**: `$HERMES_HOME/trend_history.jsonl` (한 줄 = 한 카드, `{"ts","title","source_url","summary","bullets"}`)
  - `post_to_teams.py` 가 게시 성공 시 자동 append. 별도 코드 없어도 누적됨.
  - Step 0 직전에 반드시 읽고 마지막 7일치를 dedup 비교에 사용.
- **랩 컨텍스트 파일**: `$HERMES_HOME/lab_context.md` (있으면 같이 읽어 진행 과제·사내 도구 매핑에 사용. 없으면 5축 일반 분류만 적용.)
- **게시 호출**: 채택 건마다 `scripts/post_to_teams.py` 호출. **`--source-url` 과 `--summary` 인자 반드시 같이 넘길 것** (다음 날 dedup 정확도 좌우).
  - CLI: `python scripts/post_to_teams.py "제목" "bullet1" "bullet2" ... --source-url <원본 URL> --summary "핵심 한줄"`
  - 모듈: `from post_to_teams import post_card; post_card(title, bullets, source_url=..., summary=...)`

### First-run checklist (cold-start)

최초 실행 시 다음 파일이 없을 수 있다. 없으면 생성/안내한다:

1. **`$HERMES_HOME/trend_history.jsonl`** — 없으면 빈 파일 생성 (`Path.touch()`). Dedup 시 `exists()` 체크로 자동 통과.
2. **`$HERMES_HOME/lab_context.md`** — **템플릿만 있으면 5축 일반 분류만 적용되므로 후보가 전원 ≤2점으로 폐기된다.** 반드시 진행 중 과제·사내 도구를 채워야 채택률이 생긴다.
   - **자동 검증**: 파일이 존재하더라도 모든 실제 항목이 `(예시)`, `(example)`, `TODO`, `FIXME` 등 템플릿 마커로 시작하거나 섹션 1~3에 유효 항목이 0개이면 **템플릿 상태로 간주**한다. 이 경우 Step 2 (진행 과제 매핑)를 강제 0점으로 설정하고, 5축 일반 분류만 적용하며, 출력에 `[lab_context.md 템플릿 상태 — 실제 과제를 채워넣어야 채택률이 생깁니다]` 경고를 추가한다.
3. **`scripts/post_to_teams.py`** — 본 스킬과 동봉되어 있다. 실행 CWD 가 `$HERMES_HOME` 인 경우 상대경로 `scripts/...` 를 찾지 못할 수 있으니 `skill_view(name='ai-trends-filter', file_path='scripts/post_to_teams.py')` 로 절대경로 확보 또는 `sys.path.insert(0, ...)` 로 import.
4. **Teams Webhook URL** — `post_to_teams.py` 는 `TEAMS_WEBHOOK_URL` 환경변수에서 URL 을 읽는다. 하드코딩 fallback 제거됨. `$HERMES_HOME/.env` 에 `TEAMS_WEBHOOK_URL=...` 한 줄로 등록되어 있고, hermes gateway 가 시작할 때 환경변수로 로드한다. 미설정시 `post_card` 는 명확한 `RuntimeError` 를 던지니 silent fallback 위험 없다. 채널 교체 시 `.env` 한 줄만 갱신 + gateway 재시작.

### Cron 실행 환경별 주의사항 (Pitfalls)

#### Windows 호스트
- `terminal` 도구는 bash/MSYS를 통해 실행된다. PowerShell/cmd 구문이 아닌 POSIX 구문(`ls`, `curl`, `&&`)만 사용 가능하며, Windows 네이티브 경로(`C:\...`)는 인식하지 못할 수 있다.
- **모든 파일 I/O·네트워크 요청·PDF 다운로드는 `execute_code` Python 코드로 수행**하는 것이 가장 안정적이다. `terminal`의 `curl`, `cat`, `grep` 등은 Windows 환경에서 동작 불일치가 빈번하다.
- `post_to_teams.py`를 `skill_view`로 찾을 수 없는 경우(스킬 디렉토리에 실제로 없음), `skill_view(name='ai-trends-filter', file_path='scripts/post_to_teams.py')`로 본문을 획득해 CWD에 직접 작성하거나, `execute_code` 내에서 모듈 함수를 인라인으로 재구현한다.

#### Webhook URL — 환경변수 단일 소스 (2026-06-01 갱신)
- `post_to_teams.py` 의 하드코딩된 fallback URL 은 **완전 제거**되었다. URL 은 오직 `TEAMS_WEBHOOK_URL` 환경변수에서만 읽는다.
- `$HERMES_HOME/.env` 에 `TEAMS_WEBHOOK_URL=...` 등록 + gateway 재시작 후 사용.
- 환경변수 미설정 시 `post_card()` 호출 즉시 `RuntimeError` — silent fallback 없으니 채널 잘못 가는 사고 안 일어남.
- 채널 교체 시 `.env` 한 줄 갱신 + `hermes gateway stop && hermes gateway` 재시작.

#### `lab_context.md` 템플릿 함정
- 파일이 존재하더라도 예시 항목만 채워져 있으면 Step 2(진행 과제 매핑)가 0점이 되어 **합산 5점 도달이 거의 불가능**하다(5축 max 3 + Step 3 max 2 = 5, 현실적으로 3~4점). 예외 상승 규칙(산업 전략 변화 등)에 의존하지 않으려면, 템플릿 예시를 삭제하고 **현재 진행 중인 실제 과제 3개 이상**을 기입해야 한다.

## Step −1 — 게시 이력 + 랩 컨텍스트 로드 (필수 선행)

**경로 룰**: 모든 hermes 데이터는 `HERMES_HOME` 환경변수에 정의된 경로 아래에 있다. 절대 경로를 직접 쓰지 말고 — 머신·OS·USB 드라이브마다 다르므로 — 항상 `os.environ["HERMES_HOME"]` 으로 시작하라.

후보 평가 전 반드시 다음을 먼저 로드한다.

1. **게시 이력 (dedup 기준)** — 인라인으로 재구현하지 말고 **결정론 헬퍼 `trends_util` 을 import** 해서 쓴다:
   ```python
   import os, sys
   sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "skills", "ai-trends-filter", "scripts"))
   import trends_util as tu
   recent = tu.recent_history(7)     # 최근 7일 레코드 (경로·날짜필터는 코드가 처리)
   ```
   이 `recent` 가 Step 0 의 dedup 기준이다. (이력 경로는 `trends_util` 이 post_to_teams 의 쓰기 경로와 단일화하므로 읽기/쓰기 불일치 없음.)

2. **`$HERMES_HOME/lab_context.md`** (선택) — 진행 과제·사내 도구·시한이 있는 의사결정. 있으면 Step 2 (진행 과제 매핑) 점수의 근거. 없으면 일반 카테고리로 판정.

## 관심사 입력 — `lab_context.md` 가 비어있다면 호출 시 제공 권장

본 스킬은 일반 골격이다. 더 정확한 판정을 원하면 `lab_context.md` 또는 호출 컨텍스트로 다음을 제공한다:

- **현재 진행 중 과제 목록** — 제안서·프로젝트·도입 트랙 등 (3~10개 정도)
- **사내 도구 시스템** — 현재 빌드/운영 중인 내부 도구 이름과 한 줄 설명
- **시한이 있는 의사결정** — 마감일·베타 신청·대회 등

이 정보가 없으면 5축 일반 분류만으로 판정한다.

## 소스 (정기 모니터링)

새 후보 발굴은 다음 5개 버킷에서 한다. 매일 1회 훑는다.

> **평가 시 원본을 직접 요청해야 한다.** 사이트별 요청 차단(403/451) 혹은 SPA 하이드레이션 문제가 많다. 해결 코드와 패턴은 `references/scraping_tips.md`를 참조한다. **최근 실행에서 어떤 소스가 망가졌는지는 `references/source-status-YYYY-MM-DD.md` 파일들에 기록된다.**

**1) 저장소**
| 소스 | URL |
|---|---|
| GitHub Trending | https://github.com/trending (필터: 언어/기간) |

**2) 논문**
| 소스 | URL |
|---|---|
| HuggingFace Papers | https://huggingface.co/papers |
| arXiv (cs.AI / cs.CL / cs.LG 최신) | https://arxiv.org/list/cs.AI/recent (abstract 는 arxiv.org/abs 직접) |

**3) 모델 공식 발표** (신규 모델·버전·가격 변경)
| 소스 | URL |
|---|---|
| OpenAI Platform changelog | https://platform.openai.com/docs/changelog |
| Anthropic News / Release notes | https://www.anthropic.com/news (직접 HTML 파싱 우선) |
| Google AI / DeepMind Blog | https://blog.google/technology/ai/ · https://deepmind.google/discover/blog/ |
| Meta AI / Mistral | https://ai.meta.com/blog/ · https://mistral.ai/news |

**4) 공식 블로그·전략 리포트** (사람 채널이 실제로 자주 인용 — 신설)
| 소스 | URL |
|---|---|
| Anthropic Blog | https://claude.com/blog (트렌드·사례·템플릿 글 다수) |
| OpenAI Blog | https://openai.com/news/ |
| MIT Technology Review — AI | https://www.technologyreview.com/topic/artificial-intelligence/ |
| 국내 AI 뉴스 | AI타임스(aitimes.com / aitimes.kr) 등 — 국내 관점·번역 소식 |

**5) 소셜·기타**
| 소스 | URL |
|---|---|
| 주요 인물·기관 X 공식 계정 | 연구자·랩 공식 발표 (예: 데모·티저). 1차 출처로 점프 필수 |
| 컨퍼런스 노트·해커톤·릴리스 페이지 | 자유 |

### 선별 원칙 (주제 화이트리스트가 아님)

판단 기준은 **고정된 주제 목록이 아니라 다음 한 가지**다:

> **"응용 AI·에이전트를 만드는 우리 팀이 지금 하는 일(5축 + lab_context 과제)에 실질적으로 닿는가?"**

- 어느 주제든 5축(Core Product / Platform / Deployment·AX / Tooling·Harness / R&D) 중 하나 이상에 구체적으로 연결되면 후보다. **새로운 유형의 트렌드도 환영** — 아래 목록에 없다는 이유로 떨어뜨리지 말 것.
- 반대로 화제성만 높고 우리 일과 매핑이 안 되면 점수가 낮아야 한다(Step 1~3 가 이를 처리).
- 깊이 있는 분석감이면 길게, 단순히 흥미로운 데모·도구면 가볍게 — 둘 다 게재 가능(분량은 Step 5 규칙).

**참고용 예시 (지금까지 자주 닿았던 결, 비한정·비배타)**: 에이전트 오케스트레이션·장기실행, 메모리/컨텍스트, 딥리서치, 에이전트 플랫폼·인프라·샌드박스·비용/게이트웨이, 벤치마크 공개, AX·도메인 에이전트 템플릿, 미디어 생성, 학습·효율·양자화, RAG·검색 진화 등. — 이건 **방향 감각용 예시일 뿐 점수 규칙이 아니다.** 실제 점수는 항상 Step 1~3(5축·과제매핑·유사도)로 매긴다.

> recency: 트렌드 채널이므로 **기준일 기준 14일 이내** 소식을 우선한다. 자세한 규칙은 Step 0·Step 4 참조.

## 입력 (후보)

- 위 소스 중 한 곳의 URL + (가능하면) 본문 발췌
- 단일 또는 N개 batch

## 출력

후보별로 다음 중 하나:
1. **게재** → Teams AdaptiveCard (Step 5 포맷)
2. **보류** → 1줄 사유 + 어떤 조건이 충족되면 재검토할지 (Teams 게시 안 함, 로그에만 기록)
3. **폐기** → 1줄 사유 (Teams 게시 안 함, 로그에만 기록)

---

## 워크플로우

### Step 0 — 하드 게이트 (탈락 우선)

다음 중 하나라도 해당하면 **즉시 폐기**, 아래 단계 진행 안 함:

- 지역 한정 + API 없음 + 직접 테스트 불가
- 이미 채택·운영 중인 도구의 마이너 버전업 (예: x.4 → x.4.1)
- 단순 벤치마크 1~2% 향상에 그치고 응용/워크플로우 통찰 없음
- **신선도(recency)**: 1차 출처의 **발표일이 기준일(오늘)로부터 30일 초과**면 원칙적으로 폐기. 단, **산업 전략 변화·지속가치(evergreen) 리포트**(예: 패러다임 정리, 도입 프레임워크)는 예외로 통과 가능 — 이런 예외는 드물어야 한다.
- **URL 중복 (코드로 판정)**: `trends_util.is_duplicate_url(url, recent)` 가 True 면 폐기. 정확 일치 비교는 LLM 이 눈으로 하지 말고 **반드시 이 헬퍼로** (정규화 포함, 결정론).
- **의미 중복 (LLM 판단)**: URL 이 달라도 후보 핵심 한줄이 `recent` 이력의 어떤 `summary` 와 같은 사건을 가리키는 경우. 판단 기준:
  - 같은 모델·릴리스·논문·저장소를 다른 매체가 보도한 경우 → 중복
  - 후속 마이너 업데이트(같은 프로덕트의 v1.0.1 → v1.0.2 식) → 중복
  - 새로운 사실·새로운 비교군·새로운 기능이 추가됐다면 → 중복 아님 (이전 카드 보완)
  - 애매하면 폐기 쪽으로 (false negative 보다 중복 게시가 더 나쁨)

### Step 0.5 — 원본 직접 평가 (깊이 분석)

후보 한 건마다 **원본을 직접 받아 들여다본다**. 페이지 요약·트윗·메타데이터로 점수 매기지 말 것. 다음 절차는 게재 후보가 될 만한 모든 항목에 적용한다.

> **⚠️ 1차 출처 우선 — 2차 매체로 후퇴 금지 (핵심).**
> `requests.get()` 이 403/451/빈 본문을 주는 사이트(특히 **Anthropic·OpenAI·Google 등 공식 블로그/changelog**)가 많다. 이때 **AI Times 같은 2차 매체 요약으로 후퇴하지 말 것.**
> 1. **`html = tu.fetch(url)`** — requests→jina.ai 결정론 escalation을 코드가 처리. 본문이면 그대로 사용.
> 2. **`tu.fetch` 가 `None` 이면 → `agent-browser` 로 1차 URL 을 직접 열어** 렌더링된 본문(가격표·기능·벤치 표)을 읽는다. Chrome 이 떠 있으면 `/browser connect`. (어떤 셀렉터·어떻게 파싱할지는 사이트마다 달라 **LLM 판단 영역**)
> - 새로 만난 차단·우회 패턴은 **`references/scraping_tips.md` 에 한 줄 누적**한다(자가학습 — 다음 run 이 같은 시행착오 반복 안 하도록).
> - **2차 매체만 읽고 "1차 미확인"으로 카드 쓰지 말 것** — 그건 사람 큐레이터보다 명백히 얕은 결과를 낳는다(검증된 실패 패턴).

#### 논문 (HuggingFace Papers / alphaXiv / arXiv / 모델 카드 동봉 논문)

1. **PDF 다운로드** — abstract 페이지의 PDF 링크를 `curl` 또는 `WebFetch` 로 받아 작업 디렉토리에 저장
   ```bash
   curl -L -o paper.pdf "https://arxiv.org/pdf/XXXX.XXXXX"
   ```
2. **Method / Results / Limitations 정독** — 초록 + 결론만 보면 cherry-pick 에 속는다. 다음을 확인:
   - 핵심 아이디어를 **1~2문장으로 압축 가능한가** — 안 되면 게재 후보 X
   - 식·도표·알고리즘 박스의 실제 의미 (캡션 한 번 더 읽기)
   - 벤치마크 비교군이 공정한가 (자기들이 강한 셋팅만 골랐는지)
   - **Limitations** 섹션을 저자가 솔직히 적었는지 — 없으면 신뢰도 낮춤
3. **재현성** — 코드/데이터 공개 여부, 공개됐다면 GitHub 링크를 따라가 아래 GitHub 절차도 함께
4. **수집 산출물** — 핵심 아이디어 1~2문장, 정량 수치 2~3개, 한계 1~2개

#### GitHub 저장소

1. **메타 정보** — 페이지에서 다음을 기록:
   - `⭐` 총수 + 증가 추세 ("지난 7일 +312" 등 Trending 그래프 확인)
   - License (Apache/MIT/AGPL/CC — 사내 채택 가능 여부 영향 큼)
   - 최근 commit 빈도, open issue/PR 수
2. **README 정독** — 단순 features 나열이 아니라 실 사용 예시·벤치마크·아키텍처 다이어그램
3. **코드베이스 직접 살펴보기** — README 만으로 끝내지 말 것:
   - `src/` (또는 패키지 루트) 의 **핵심 파일 2~3개** 직접 열어 구현 수준 확인
   - `tests/` 또는 `examples/` 디렉토리의 실제 호출 코드 1~2건 읽기
   - "우리가 그대로 import 해서 쓰면 어떻게 작동하나" 한 줄로 시뮬레이션
4. **알려진 한계** — 최근 30일 open issues 중 "critical / bug / not working" 라벨 훑기
5. **의존성** — `pyproject.toml` / `package.json` / `requirements.txt` 의 주요 의존성이 자체 스택과 충돌하지 않는지
6. **수집 산출물** — `⭐ {총수} (기간 +{증가량}) · {License}` 한 줄 + 핵심 사용 예시 한 줄 + 알려진 한계 0~1개

#### 모델 공식 발표 (OpenAI / Anthropic / Google / Meta / Mistral / HF Hub)

1. **공식 모델 카드** 직접 열기 (블로그 요약이 아니라 본 모델 카드)
2. **API 문서·changelog** 에서 다음 확인:
   - **가격** — input/output, cache hit, batch (1M tokens 기준)
   - 컨텍스트 윈도우, max output tokens
   - rate limit, SLA, 지역별 가용성 (한국 접근 가능?)
   - 함수 호출·tool use·vision 등 기능 매트릭스
3. **벤치마크 페이지** — 비교 대상 모델이 공정한지, "특정 셋팅만 우월" 패턴인지
4. **이전 모델 대비 차이** — 가격·성능·기능 어느 축이 달라졌는지 한 줄 요약 가능해야 함
5. **수집 산출물** — `Input $X / Output $Y · 한국 OK/제한 · vs {비교 모델}` + 차별점 1~2개

#### 뉴스 (The Verge AI 등)

1. **1차 출처로 점프** — 기사 본문의 "공식 발표"·"논문"·"GitHub" 링크를 따라가 위 3개 절차 중 해당하는 것을 적용
2. 1차 출처가 없거나 익명 소스("관계자에 따르면") 만 있으면 → **보류** 처리 (1차 출처 확보 후 재평가)
3. **announced ≠ available 구분** — 발표일과 실제 사용 가능일을 분리 기록

#### 공통 — 평가 결과를 어떻게 쓰는가

위에서 수집한 자료를 그대로 Step 1~3 의 점수 근거로 사용한다. 예:
- "Method §3 에서 GRPO 대비 35배 적은 시도로 동일 성능" → R&D 2점 근거
- "`src/orchestrator.py` 가 LangGraph `StateGraph` 를 그대로 받음" → Core Product 3점 근거
- "Input $0.50/1M, 한국 가용" → Tooling 2점 근거

**증거 없는 점수 금지** — Step 0.5 에서 직접 확인하지 않은 사실은 점수에 반영하지 않는다.

### Step 1 — 관심 영역 5축 매핑 (각 영역 0~3점)

AI 랩의 일반적 관심 영역 5축. 어느 영역이 강한지는 팀마다 다르므로, 호출 시 제공된 정보(있다면)로 가중치를 조정한다.

| 영역 | 0점 | 1점 | 2점 | 3점 |
|---|---|---|---|---|
| **Core Product** (핵심 응용 제품) | 무관 | 일반 LLM 동향 | Multi-Agent / LangGraph / RAG / Memory / 음성·이미지 생성 기법 적용 가능 | 운영 중 핵심 제품에 직접 채택 또는 대체 가능 |
| **Platform** (에이전트 플랫폼·API) | 무관 | 일반 API 동향 | OpenAI 호환 / Adapter 패턴 / MCP / Pydantic 등 | 운영 중 플랫폼에 직접 결합 또는 대체 가능 |
| **Deployment / AX** (사내·외부 도입) | 무관 | 일반 AI 도입 사례 | 직무별 에이전트 템플릿 / AX 성숙도 모델 / 워크플로우 표준화 | 진행 중 도입 트랙에 직접 적용 가능 |
| **Tooling / Harness** (개발 인프라·비용 통제) | 무관 | 모델 옵션 일반 | LLM 게이트웨이 / 비용 통제 / 멀티 LLM 라우팅 / dogfooding 도구 | 진행 중 도구·인프라 작업과 직결 |
| **R&D** (학습·평가·아키텍처) | 무관 | 신규 모델 출시 | 학습 효율 / 평가 벤치마크 / 데이터셋 / 파인튜닝 기법 | 진행 중 제안서·대회·학습 계획에 직결 |

**증거 규칙**: 점수마다 "어떤 키워드/사실 때문에 N점인지" 한 줄로 기록한다. 점수 단독으로는 끝내지 말 것.

### Step 2 — 진행 과제 매핑 (0~3점)

호출 시 제공된 진행 과제 목록(있다면)과 매칭. 없으면 일반 카테고리로 판정:

- **제안서/공모 과제** — 정부·기업 공모, 컴피티션
- **사내 도구·시스템** — 빌드 중 / 운영 중 내부 제품
- **도입 트랙** — 사내·외부 AI 도입 프로젝트

점수:
- 3점: 진행 중 과제 중 하나에 **직접 자료로 활용 가능**
- 2점: **참고 패턴**으로 활용 가능
- 1점: 멀리서 연관
- 0점: 매칭 없음

### Step 3 — 컨텍스트 유사도 (0~3점)

"우리가 만든/만들려는 것과 유사한 외부 사례인가?"

- 3점: 우리 시스템과 1:1 비교 가능 ("우리 X와 사실상 같은 것을 외부에서 했다")
- 2점: 유사 도메인이나 구현 다름
- 1점: 멀리서 비슷
- 0점: 관련 없음

### Step 4 — 합산 및 분류

**총점 = max(5축 점수) + Step 2 + Step 3 + 신선도(freshness)** → 최대 10점.

**신선도(freshness)** — 발표일 *추출*은 LLM(원문에서), *날짜 계산·가점*은 코드: `tu.freshness_bonus("2026-05-28")` → 14일 이내 +1, 그 외 0. (30일 초과 하드게이트는 Step 0; 전략·지속가치 예외만 통과해 +0)

분류:
- **≥ 5점**: 게재 (Step 5 진행)
- **3~4점**: 보류 — "어떤 조건이 추가되면 채택?" 1줄
- **≤ 2점**: 폐기 — 사유 1줄
- **동점 시**: 더 최신 + 진행 과제에 더 가까운 것을 우선해 Top 3 선정

**예외 상승 조건** (점수 무관 게재):
- 사내 인프라·도구의 직접 보완 도구
- 팀의 우선순위·전략 변경에 영향 주는 산업 발표
- 채택 결정에 시한이 있는 경우 (대회 마감, 베타 신청 등)

### Step 5 — Teams AdaptiveCard 변환 (Brief 수준의 분량)

채택된 후보를 다음 호출로 Teams 채널에 게시한다. **수신자 = 이 트렌드를 처음 보는 동료**.

**Step 0.5 에서 PDF 전체 / 코드베이스 / changelog 를 다 읽었으니, 그 깊이가 카드에 드러나야 한다.** 키워드 나열·단편 정보로 압축하지 말 것.

**분량 가이드 — 후보 유형에 맞춰 유연하게** (사람 채널도 심층글 7섹션 ~ 가벼운 공유 2~3줄까지 편차가 큼):

| 후보 유형 | 분량 | 비고 |
|---|---|---|
| **심층** (오픈소스 도구 / 논문 / 전략 리포트) | 7~10 bullet, 각 100~300자 (총 1500~2500자) | 800자 미만이면 "왜 깊이 안 봤나" 재검토 |
| **모델 출시** | 5~8 bullet | 가격·컨텍스트·벤치·기능 매트릭스 중심 |
| **가벼운 공유** (흥미로운 데모·도구·X 글) | 3~5 bullet, 짧게 | 800자 하한 **적용 안 함**. 핵심 + 링크 + 우리에게 의미 한 줄이면 충분 |

- 너무 길어지면 카드 두 장으로 분리, 두 번째 카드 제목 끝에 ` (2/2)` 표기
- **유형 판단**은 Step 0.5 의 후보 성격(저장소/논문/모델/리포트/단순공유)에 따른다. 아래 유형별 bullet 구조 참조.

#### ★ 카드 생성 방식 — 3단 파이프라인 (심층 후보 필수, 가벼운 공유는 생략)

**한 번에 모든 섹션을 쓰지 말 것.** 한 호출에서 7~10개 칸을 동시에 채우면 attention 이 분산돼 칸마다 얕아지고 반복된다. 그런데 "섹션별로 따로 써라"고 **글로 지시하면 에이전트가 결국 한 방에 생성**하는 것이 검증됨 → 그래서 **섹션별 생성을 코드가 강제**한다. 직접 인라인으로 7개 섹션을 쓰지 말고 **반드시 `card_pipeline.build_deep_card()` 를 호출**하라:

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "skills", "ai-trends-filter", "scripts"))
import card_pipeline as cp
from post_to_teams import post_card

# 5-A) Step 0.5 의 1차 실측 결과를 '증거 노트' 텍스트로 정리 (수치·인용위치·한계·가격·경쟁대안 고유명·발표일)
evidence = """... PDF/원문에서 직접 뽑은 사실들 ..."""

# 5-B+5-C) 코드가 섹션마다 독립 LLM 호출 → 종합(중복제거·경쟁구도·한국어 교정·분량)
card = cp.build_deep_card(evidence, card_type="paper")   # paper|github|model|report

# 게시
post_card(title=card["title"], bullets=card["bullets"], facts=card.get("facts"),
          source_url="https://arxiv.org/abs/XXXX.XXXXX")
```

- **5-A (에이전트 몫)**: 깊은 읽기로 **증거 노트** 작성. 노트 품질이 카드 품질을 좌우 — 수치·인용위치·경쟁 대안 고유명까지 담아라.
- **5-B+5-C (코드 몫, `build_deep_card`)**: 섹션마다 따로 호출(attention 집중) → 종합 1회에서 중복제거·경쟁구도 보강·**한국어 교정**·분량 조정. 에이전트가 한 방에 합치는 것을 코드가 차단.
- 가벼운 공유 유형은 이 파이프라인 생략(짧게 직접 작성).

> 목표: "성실한 칸 채우기" → "관점 가진 애널리스트 브리핑". 종합 단계가 사람 글과의 마지막 깊이 격차(포지셔닝·통찰)와 한국어 품질을 함께 잡는다.

#### 카드 bullet 구조 (필수 라벨 그대로)

**공통 bullet (모든 후보 필수)**:

1. **`【무엇】`** (200~300자) — 누가 만들었나 + 어떤 카테고리 (멀티 에이전트 프레임워크 / RAG 라이브러리 / 새 모델 / 정책 변경 등) + 한 문단으로 무엇인지. 도메인 모르는 사람도 이해 가능하게 풀어쓰기.

2. **`【핵심 혁신/발견】`** (200~300자) — 기존 대안 대비 차별점. 반드시 구체 수치·비교 + 어디서 인용했는지 출처 표기 (논문 §3.2, README L42, 가격표 등). 예: "기존 GRPO 대비 35배 적은 시도로 동일 성능 (논문 §4, Table 2)".

**소스별 깊이 bullet (해당 카테고리만 — Step 0.5 에서 본 내용을 풀어쓴다)**:

* **논문**:
  - **`【방법론】`** (200~300자) — 핵심 알고리즘·아키텍처를 평이한 표현으로. 식·도표 의미 풀어쓰기.
  - **`【실험 결과】`** (150~250자) — 주요 벤치마크 점수, 비교군, ablation 핵심 1~2개.
  - **`【한계 / 재현성】`** (100~200자) — Limitations 섹션 요지 + 코드·데이터 공개 여부.

* **GitHub 저장소**:
  - **`【아키텍처】`** (200~300자) — `src/` 핵심 파일 2~3개 정독 결과를 한두 문단으로. 어떻게 동작하는지.
  - **`【실제 사용 예시】`** (150~250자) — `examples/` 또는 README 의 호출 코드 3~6 줄 인용 + 해석.
  - **`【알려진 이슈·의존성】`** (100~200자) — 최근 30일 open issue 중 critical/bug 라벨 요지 + 주요 의존성 호환성.

* **모델 출시**:
  - **`【가격·접근성】`** (150~250자) — input/output 가격(1M tokens), 컨텍스트 윈도우, max output, 한국 가용성, rate limit, SLA.
  - **`【벤치마크】`** (150~250자) — 주요 평가 셋 점수, 비교 모델, "특정 셋팅만 우월" 패턴 여부 평가.
  - **`【기능 매트릭스】`** (100~200자) — function calling, tool use, vision, structured output 등 지원 여부 + 이전 모델 대비 차이.

* **전략 리포트 / 산업 트렌드** (Anthropic·MIT TR 등 외부 아티클 다이제스트):
  - **`【핵심 주장】`** (200~300자) — 리포트의 중심 논지. 번호 트렌드형이면 핵심 3~5개를 추려 각 1줄.
  - **`【근거·수치】`** (150~250자) — 인용된 정량 근거 ("85% 조직이 …", "27% 작업이 …" 등) + 사례 1~2개.
  - **`【시사점】`** (150~250자) — 우리 전략·로드맵에 주는 함의.

* **벤치마크 공개**:
  - **`【무엇을 측정】`** (150~250자) — 과제 정의·평가 방식.
  - **`【현 수준】`** (150~250자) — 프런티어 모델 점수·한계 ("전부 50% 못 넘김" 식 정량).

* **가벼운 공유** (흥미로운 데모·도구·X 글 — 짧게):
  - 위 깊이 bullet 생략 가능. `【무엇】` + 링크 + `【우리에게 의미】` 한 줄이면 충분.

* **뉴스**: 1차 출처가 paper/repo/model/리포트 중 어느 것이냐에 따라 위 깊이 bullet 적용.

**공통 마무리 bullet** (가벼운 공유 제외, 나머지 유형 필수):

- **`【지금 왜 트렌드인가】`** (150~250자) — 별 수 급증, 주요 라이브러리/플랫폼 채택, 베타 신청 쇄도, 산업 발표 등 구체 화제성 신호 + **얼마나 최신인지(발표 후 며칠)**. "주목받는다" 같은 모호 표현 금지.
- **`【우리에게 의미】`** (150~250자) — 운영 시스템 / 진행 과제 / 도입 트랙 중 **어느 것에 닿는지 1:1로 명시** (예: "우리 Memory System 과 동일 설계", "하네스 비용통제에 직접 적용"). lab_context 비어있으면 일반 AI 랩 관점에서.
- **`【필수 메타】`** (한 줄에 압축) — 별 수·라이선스·가격·접근성·재현 코드 유무 등 압축. (렌더링은 post_card 의 `facts=` 표로도 가능 — Step 5 호출부 참조)
- **`【출처】`** (필수) — 1차 출처 URL + **발표 날짜**. announced ≠ available 이면 구분 표기. 여러 매체면 1차 출처를 맨 앞에. (post_card 의 `source_url=` 에도 반드시 동일 URL 전달)
- **`☐ {액션}`** (1문장) — 검토·실험·도입 결정을 위한 다음 단계. 동사로 시작. 책임자 미기재.

#### 호출 예시 (논문)

```python
import os, sys
# 이 스킬의 scripts/ 는 항상 $HERMES_HOME/skills/ai-trends-filter/scripts 아래에 있다.
sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "skills", "ai-trends-filter", "scripts"))
from post_to_teams import post_card

post_card(
    title="OmniRetrieval — 이종 지식 원천 통합 RAG 프레임워크",
    bullets=[
        "【무엇】 MIT-CSAIL · Google DeepMind 공동 연구진이 arXiv 2605.29250 (2026-05-23) 로 발표한 통합 retrieval 프레임워크. 비구조화 텍스트, 관계형 테이블, 지식 그래프, 프로퍼티 그래프 4종을 한 자연어 쿼리로 동시 질의 가능하게 한다. 기존엔 각 소스별로 별도 retriever 를 두던 패러다임을 깬다.",
        "【핵심 혁신】 동질화 (homogenization, 모든 소스를 임베딩 공간 하나로 합치는 방식) 대신 'source-native dispatch' 전략 채택. 자연어 쿼리에서 LLM 이 의도를 파악해 각 소스의 native query language (SQL / SPARQL / Cypher / dense retrieval) 로 변환·실행 후 통합 (논문 §3.1, Figure 2).",
        "【방법론】 ...",
        "【실험 결과】 ...",
        "【한계 / 재현성】 ...",
        "【지금 왜 트렌드인가】 ... (발표 후 9일, HF Papers 일간 1위)",
        "【우리에게 의미】 우리 Deep Research / Memory System 의 multi-source 라우팅과 직접 비교 가능.",
        "【출처】 arXiv 2605.29250 (2026-05-23 발표) · MIT-CSAIL & Google DeepMind",
        "☐ 우리 RAG 파이프라인의 multi-source 라우팅 모듈과 비교 점수 정리",
    ],
    facts={                       # ← 카드 상단에 표(FactSet)로 렌더링 (선택)
        "출처": "arXiv 2605.29250",
        "발표일": "2026-05-23",
        "소속": "MIT-CSAIL & Google DeepMind",
        "코드": "공개 (체크포인트 포함)",
        "벤치마크": "13개 데이터셋 309KB",
    },
    source_url="https://arxiv.org/abs/2605.29250",   # ← "원문 열기" 버튼 + dedup 기록
    summary="MIT-CSAIL+DeepMind 의 이종 KB 통합 retrieval — source-native dispatch 로 동질화 회피",
)
```

> `facts=` 는 **선택**이다. 주면 카드 상단에 표로 깔끔히 나오고, 안 주면 기존처럼 bullet 만 렌더링된다(하위호환). 모델 출시면 `facts={"가격":"$0.50/$1.50 per 1M","컨텍스트":"200K","한국":"가용"}` 식으로 쓰면 좋다.

#### 절대 룰
- **분량 미달 시 폐기 후 재작성**: 카드 전체 800자 미만 = 분석 깊이 부족. 자체 재검토. (가벼운 공유 유형 제외)
- **"미확인/추정" 가드 (모델 발표·도구)**: 카드에 **가격·핵심 벤치·주요 신기능이 "미확인/추정"으로 남으면 게재 금지.** 1차 출처를 `agent-browser` 로 다시 열어 실측 후 채운다. 브라우저로도 끝내 못 구하면, 그 항목은 **"미확인"이라고 쓰지 말고 아예 빼고** 구한 사실만으로 카드를 구성한다(빈약하면 보류 처리). — 2차 매체 추정으로 칸 채우지 말 것. (검증된 실패: Opus 4.8 건에서 1차 미확보로 가격·신기능 누락)
- **출처 없는 수치 금지**: 모든 수치는 (논문 §N / README L · / 가격표) 와 함께.
- **`【...】` 라벨 누락 금지**: 라벨 빼고 본문만 쓰지 말 것. 라벨이 카드의 목차 역할.
- **마지막 bullet `☐` 액션**: 동사로 시작. 액션이 정말 떠오르지 않으면 생략 가능 (전체 카드 분량 미달 안 되면).
- **책임자 미기재**: 담당자는 게재 후 회의에서 매핑.

**`【필수 메타】` bullet 의 소스별 양식**:

- **GitHub 저장소** → `⭐ {별표 총수} ({기간} +{증가량}) · {License} · {언어} · 의존성 충돌 여부`
  - 예: `⭐ 32.1k (지난 7일 +412) · MIT · Python 3.10+, pydantic v2 — 우리 스택 호환`
- **논문 (HF Papers / alphaXiv / arXiv)** → 발행 일자 + 저자 소속 + 재현 코드 공개 여부 + 데이터셋 공개 여부
  - 예: `arXiv 2605.29250 · 2026-05-23 · MIT-CSAIL & Google DeepMind · 코드·체크포인트 공개 · 자체 벤치마크 309 KB`
- **뉴스 (The Verge AI 등)** → 1차 출처 (공식 블로그/공시) + announced 일자 + available 일자·지역 구분
  - 예: `The Verge → Anthropic 공식 블로그 2026-05-25 · announced 2026-05-25, available US-only Q3 2026`
- **모델 출시** → input/output 가격(1M tokens) + 컨텍스트 윈도우 + 한국 접근성 + 비교 대상 모델
  - 예: `Input $0.50 / Output $1.50 per 1M · 200K ctx · 한국 OK (Tier-2 region) · GPT-5.4 mini 와 동급 보고 (LMSys Arena 1240)`

---

## Step 6 — 학습 누적 (write-back, 필수)

이 스킬의 가치는 **매 실행의 판단(CoT)에서 "재사용 가능한 교훈"만 골라 파일에 적어 복리로 쌓는 것**이다. run 을 끝내기 전에 아래를 점검해 해당되면 기록한다. (일회성 결과 — 특정 카드 본문·점수 — 는 쌓지 말 것. dedup 용 한 줄만 history 에 남으면 충분.)

| 무엇을 | 어디에 | 언제 |
|---|---|---|
| 새 차단·SPA·우회 패턴 (예: "X사 블로그 = requests 403 → browser") | `references/scraping_tips.md` 에 한 줄 추가 | Step 0.5 에서 새 사이트 막혔을 때 |
| 오늘 소스별 작동/차단 상태 | `references/source-status-{오늘날짜}.md` 새로 생성 | run 종료 시 (소스 1개 이상 죽었으면) |
| 선별 캘리브레이션 교훈 (예: "펀딩 뉴스 폐기 맞음", "이 유형은 과대평가했음") | `references/curation-notes.md` 에 날짜+한 줄 | Step 4 후 의미 있는 깨달음이 있을 때만 |

- 기록은 `skill_manage`(스킬 파일 수정) 또는 직접 파일 append 로. **없으면 만들고, 있으면 한 줄 덧붙인다.**
- 과적합 주의: "이번 후보가 좋았다" 같은 건 적지 말 것. **다음 run 의 의사결정을 바꿀 일반화된 교훈**만.

---

## 채택/폐기 패턴 사전 (카테고리)

**채택 패턴** (5축·신호별 전형):

| 카테고리 | 채택 근거 |
|---|---|
| 프로덕션 배포 인프라 도구 (보안/인증/샌드박스/체크포인트 포함) | Platform 3 + Tooling 2 — 운영 인프라 직접 보완 |
| 멀티 에이전트 오케스트레이션 프레임워크 (LangGraph/AutoGen 등 호환) | Core Product 3 + Platform 2 — 기존 그래프 호환성 |
| 스킬·프롬프트 자동 진화 방법론 (DSPY/JEPA 유형) | Core Product 2 + 진행 과제 매핑 — 에이전트 자체 진화 |
| 도메인별 에이전트 템플릿 모음 (금융/의료/제조 등) | Deployment/AX 3 — 직무별 워크플로우 직접 차용 |
| 비용 효율 모델 출시 (대비 가격 1/5~1/10) | Tooling 2 + R&D 1 — 라우팅·게이트웨이 옵션 |
| 사내 도구와 1:1 비교 가능한 외부 오픈소스 | 컨텍스트 유사도 3 — 벤치마킹 직접 가능 |
| 산업 전반 전략 변화 발표 (오픈소스 정책·라이선스·생태계) | 예외 상승 — 점수 무관 |

**폐기 패턴**:

| 카테고리 | 폐기 근거 |
|---|---|
| 단일 모델 +1~2% 벤치마크 향상 | 응용 통찰 없음 |
| 일반 Python 라이브러리 출시 (AI 응용과 거리 있음) | 5축 모두 0~1점 |
| 스타트업 펀딩 뉴스 | 컨텍스트/과제 매핑 없음 |
| 프롬프트 엔지니어링 팁 일반론 | 신호 없음 |
| 미국·특정 지역 한정 + API 미공개 | 하드 게이트 |
| 이미 채택한 도구의 마이너 업데이트 | 하드 게이트 |

---

## 사용 예시

**입력**:
> GitHub trending: `microsoft/autogen` v0.5 release (2026-05-25). Multi-agent orchestration framework, LangGraph 호환 어댑터 추가, 비동기 메시지 패싱 개선.

**Step 0.5 — 원본 페이지 직접 확인**:
- ⭐ 별표: 32.1k → Trending 페이지 그래프에서 지난 7일 +412 확인
- License: CC-BY-4.0 (코드는 MIT)
- README 의 예시: LangGraph `StateGraph` 객체를 그대로 `AutoGen.run()` 에 넘기는 한 줄 데모
- 의존성: Python 3.10+, pydantic v2 (우리 스택과 호환)

**처리**:
- Step 0 게이트: 통과
- Step 1 영역 매핑:
  - Core Product 3 — LangGraph 호환 → 운영 중 Multi-Agent 제품에 직접 채택 가능
  - Platform 2 — Adapter 패턴 관련
  - Deployment 0, Tooling 1, R&D 1
  - max = **3**
- Step 2 과제 매핑: 2 — 진행 중 Multi-Agent 설계 참고
- Step 3 컨텍스트 유사도: 2 — 운영 중 Supervisor 패턴과 유사
- 합산: 3+2+2 = **7점** → 게재

**Teams 게시 호출**:
```python
post_card(
    title="AutoGen v0.5 — LangGraph 호환 + 비동기 메시지",
    bullets=[
        "⭐ 32.1k (지난 7일 +412) · MIT · Microsoft 가 2026-05-25 출시한 Multi-agent orchestration 프레임워크 v0.5",
        "LangGraph 어댑터 추가 — 기존 `StateGraph` 객체를 그대로 호출 가능 (README 1줄 데모)",
        "비동기 메시지 패싱 개선으로 Supervisor 패턴 응답성 향상",
        "Python 3.10+, pydantic v2 — 우리 스택 호환",
        "☐ LangGraph 어댑터가 자체 Adapter 와 충돌 여부 확인",
    ],
)
```

---

## 갱신 가이드

본 스킬은 일반 골격이므로 자주 갱신할 필요 없다. 갱신이 필요한 경우:

- 새 카테고리의 트렌드가 반복 등장 (예: 새로운 형태의 AI 도구·플랫폼) → 5축 정의 또는 패턴 사전에 추가
- 하드 게이트가 오작동 (게재해야 할 것을 떨어뜨리거나 폐기해야 할 것을 통과시킴) → 게이트 조건 보강

호출 시 제공하는 "현재 진행 중 과제 목록"이 자주 바뀌는 것은 정상 — 스킬 본문은 그대로 유지하고 호출 컨텍스트만 갱신한다.
