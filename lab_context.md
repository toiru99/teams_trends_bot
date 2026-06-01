# Lab Context — Agent Part (이스트소프트 est-alan)

> `ai-trends-filter` 스킬이 매 실행마다 로드한다. 진행 과제·사내 도구를 채울수록
> Step 2(진행 과제 매핑) 점수가 정확해져 게재 정확도가 올라간다.
>
> **소속**: 이스트소프트(est-alan) **Agent Part** (구 NLP & LLM Space)
> **미션**: 앨런(Alan) 서비스를 LangGraph 기반 멀티모달 **Agentic AI** 로 진화
> **3대 목표**: ① 앨런(Alan) ② AX(AI Transformation) ③ R&D

## 1. 현재 진행 중 과제 (2026 기준)

- **앨런(Alan) Agentic 진화** — LangGraph 기반 검색·딥리서치·슬라이드 생성을 하나의 흐름으로 묶는 멀티모달 Agentic AI 서비스
- **Agent Platform** — LangGraph/Agent 시스템을 **OpenAI Compatible API** 로 노출하는 Python 라이브러리 (`est-alan/agent-platform`)
- **하네스(Harness)** — 모델 게이트웨이 + 멀티 LLM 라우팅 + **비용 통제층** + AI 개발 도구 인프라
- **Alan Works** — 멀티 LLM 래퍼
- **AX 트랙** — 제안서 작성 에이전트 / 소프트웨어 개발 에이전트 / 재무관리실 관리회계 AX
- **정부 과제(제안·수행)** — 정통부 AI Agent 융합확산·국가유산 AI 해설·신속상용화(교정안전), 문체부 한국어 지식연계 상담 에이전트·관광 특화 오케스트레이션, 국방 AX 군 민원상담, AX 스프린트(농업·복지부)
- **GPU 고성능컴퓨팅지원(과기부)** — 주제: RAG, Conflict Resolution, factuality / Knowledge Confidence 벤치마크
- **AI Champion 대회** — Slide Agent 출품
- **제조 AX(검토 중)** — 다이캐스팅 공정 최적화·이상 대응 순환형 멀티 에이전트

## 2. 사내 도구·시스템

- **Alan / Alan Works** — Agentic AI 서비스 + 멀티 LLM 래퍼
- **Agent Platform** (`est-alan/agent-platform`) — OpenAI 호환 API 라이브러리
- **하네스(Harness)** — 모델 게이트웨이·비용 통제·평가 인프라
- **MCP-Agent** (`est-alan/mcp_agent`) — Notion·Playwright·Gmail 등 MCP 서버 연결 자동화 에이전트
- **Slide Agent** — 주제 → 발표자료 end-to-end Multi-Agent
- **Deep Research** — 연구 프로세스를 그래프로 구현한 Multi-Agent 보고서 시스템
- **Memory System** — Agentic AI 장기 기억 / 유저 메모리 인프라
- **Image Generation Agent** — 이미지 생성 에이전트
- 인프라: GPU `RTX PRO 6000 Blackwell`, GitHub org `est-alan`

### 기술 관심 키워드 (5축 매핑 가속용)
- **Platform**: MCP, A2A 인터페이스 프로토콜, OpenAI 호환 어댑터, 멀티에이전트 오케스트레이션, 동적 라우팅·도구 선택 정책 학습
- **Core Product**: LangGraph, RAG / retrieval / embedding, Deep Research, 슬라이드 생성, Memory System
- **Tooling/Harness**: LLM 게이트웨이, 멀티 LLM 라우팅, 비용 통제, dogfooding 평가 도구
- **R&D**: 사실성 보증 가드레일, Knowledge Confidence / factuality, 데이터 합성, 파인튜닝(LoRA·DPO·ORPO), Voice Translation·dubbing(Isochrony·prosody·TTS)
- **Deployment/AX**: 직무별 에이전트 템플릿(제안서·소프트웨어·재무), 정부 과제형 도메인 에이전트(상담·번역·관광·민원·제조)
