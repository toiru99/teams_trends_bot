# AI Trends Filter — Source-specific scraping recipes

> 에이전트가 실행하며 사이트별 차단·SPA·우회 노하우를 `skill_manage` 로 이 파일에 누적한다(자가학습 타깃).
> 아래는 시드 레시피. 새 차단 사이트를 만나면 한 줄씩 추가할 것.

## 대원칙 — 1차 출처를 끝까지 확보 (2차 매체 후퇴 금지)

`requests` → `jina.ai` → **`agent-browser`** 순으로 escalate. 공식 블로그/changelog는 정적 요청이 자주 막히므로, 막히면 **브라우저로 직접 렌더링**해 본문을 읽는다. 2차 매체(뉴스 요약)로 후퇴해 "미확인"을 남기지 말 것.

## 공식 블로그·changelog — requests 차단 → 브라우저 필수

| 사이트 | 증상 | 권장 |
|---|---|---|
| anthropic.com/news, claude.com/blog | `requests` 403 / 본문 비어있음 잦음 | **agent-browser 로 URL 직접 열기**. 모델 발표는 가격·기능·벤치 표가 본문에 있으니 렌더링 후 추출. (검증: Opus 4.8 건에서 requests 후퇴 → 가격·신기능 누락) |
| openai.com/news, platform.openai.com/docs/changelog | `requests` 403 잦음 | jina.ai 우선, 실패 시 agent-browser. changelog는 최근 14일치만 필터 |
| blog.google / deepmind.google, ai.meta.com, mistral.ai | SPA·nav-only 잦음 | agent-browser 로 렌더링 후 본문 |

## arXiv / HF Papers

- HF Papers: `data-props` JSON 파싱(SPA). abstract 비면 arXiv abs 페이지 직접.
- arXiv abstract: `arxiv.org/abs/{id}` 의 `<blockquote class="abstract">` 직접 추출. PDF는 `arxiv.org/pdf/{id}`.

## arXiv — 목록 및 본문 추출 (2026-06-05 갱신)

- arXiv cs.AI recent (`arxiv.org/list/cs.AI/recent`): `fetch()` OK. HTML은 `<dt>`(arxiv id, pdf 링크) + `<dd>`(title) DOM 쌍으로 구성됨. 단순 regex보다 `document.querySelectorAll('dt')` → `dt.nextElementSibling` 방식이 안정적.
- arXiv HTML experimental (`arxiv.org/html/{id}`): `fetch()` OK이나 section 구조가 복잡하여 단순 `<h2>` regex로는 본문 추출 실패. **PDF 다운로드 (`arxiv.org/pdf/{id}`) + PyMuPDF (`fitz`) 텍스트 추출**이 더 안정적이고 풍부한 정보를 제공함 (verified on 2606.06337, 2606.06453, 2606.06036).

## OpenAI Changelog — SPA/lazy-loading 주의 (2026-06-05 갱신)

- `platform.openai.com/docs/changelog`: `fetch()`는 200을 반환하지만, 반환 HTML은 사이드바 네비게이션 위주로 렌더링되고 메인 changelog 콘텐츠가 SPA/lazy-loading됨. `document.body.innerText`에서 date/title 패턴을 검색하거나, 브라우저에서 메인 콘텐츠 영역까지 스크롤 후 DOM을 재조회해야 실제 changelog 항목을 확보할 수 있음. 단순 HTML regex 파싱은 실패할 수 있음.

## GitHub Trending

- `github.com/trending?since=daily` 는 서버사이드 렌더 → `Box-row` 정규식 안정. ⭐·언어 추출 가능.
- 정확한 별표수/이슈는 repo 페이지 직접 요청(토큰 없으면 rate-limit 주의).
- **브라우저 직접 접근**이 star 수 증가 추세(“3,142 stars today”), 최근 커밋 메시지, 폴더 구조 등 추가 메타를 확보하는 데 유리함.
