"""심층 카드 생성 — 코드 오케스트레이션 3단 파이프라인.

문제: 에이전트에게 "섹션별로 따로 써라"고 글로 지시해도, 결국 한 번에(one-shot) 생성해
attention 이 분산되고 칸마다 얕아진다. 그래서 **섹션별 개별 LLM 호출을 코드가 강제**한다.

흐름:
  build_deep_card(evidence, card_type)
    5-B  각 섹션을 '독립 LLM 호출'로 생성 (한 호출=한 섹션, attention 집중)
    5-C  종합 호출 1회 — 중복 제거 + 경쟁구도(고유명) 보강 + 서사 일관 + 한국어 교정 + 분량
    → {"title", "bullets":[...], "facts":{...}}  (post_card 에 그대로 전달)

evidence: Step 0.5 의 깊은 읽기 결과(원문 실측)를 정리한 텍스트/노트. LLM 은 이 노트만 근거로 쓴다.
LLM: Fireworks Kimi K2.6 (OpenAI 호환 chat/completions, requests 직접 호출 — openai SDK 불필요).
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

import requests

import trends_util as tu

LLM_BASE = os.environ.get("TRENDS_LLM_BASE", "https://api.fireworks.ai/inference/v1")
LLM_MODEL = os.environ.get("TRENDS_LLM_MODEL", "accounts/fireworks/models/kimi-k2p6")

# 유형별 섹션 구성 (SKILL.md Step 5 라벨과 일치). 각: (라벨, 그 섹션 작성 지침)
SECTION_SPECS: Dict[str, List[Tuple[str, str]]] = {
    "paper": [
        ("【무엇】", "누가/언제 발표했고 무엇인지. 도메인 모르는 사람도 이해되게."),
        ("【핵심 혁신】", "기존 대안 대비 차별점 + 구체 수치 + 인용 위치(§/Table)."),
        ("【방법론】", "핵심 알고리즘·아키텍처를 평이하게."),
        ("【실험 결과】", "주요 벤치 점수·비교군·ablation 핵심."),
        ("【한계/재현성】", "Limitations 요지 + 코드·데이터 공개 여부."),
        ("【지금 왜 트렌드인가】", "구체 화제성 신호 + 얼마나 최신인지."),
        ("【우리에게 의미】", "우리 진행 과제/시스템에 1:1로 어디에 닿는지."),
    ],
    "github": [
        ("【무엇】", "누가 만든 무슨 도구인지 + 카테고리."),
        ("【핵심 혁신】", "차별점 + ⭐·증가추세 등 수치."),
        ("【아키텍처】", "src 핵심 동작을 평이하게."),
        ("【실제 사용 예시】", "examples/README 호출 코드 + 해석."),
        ("【알려진 이슈·의존성】", "critical 이슈 + 의존성 호환."),
        ("【지금 왜 트렌드인가】", "채택 신호 + 최신성."),
        ("【우리에게 의미】", "우리 시스템/과제에 1:1 매핑."),
    ],
    "model": [
        ("【무엇】", "제공사·모델명·발표일·무엇이 바뀌었나."),
        ("【핵심 혁신】", "이전 버전·경쟁모델 대비 차별점 + 수치."),
        ("【가격·접근성】", "input/output 가격·컨텍스트·한국 가용성."),
        ("【벤치마크】", "주요 평가셋·비교모델·공정성."),
        ("【기능 매트릭스】", "tool use·vision 등 + 이전 대비 차이."),
        ("【지금 왜 트렌드인가】", "화제성 + 최신성."),
        ("【우리에게 의미】", "하네스·라우팅 등 1:1 매핑."),
    ],
    "report": [
        ("【핵심 주장】", "리포트 중심 논지(번호 트렌드면 3~5개 추려)."),
        ("【근거·수치】", "인용된 정량 근거 + 사례."),
        ("【지금 왜 트렌드인가】", "왜 지금 중요한가 + 최신성."),
        ("【우리에게 의미】", "우리 전략·로드맵 함의."),
    ],
}

_SYS_SECTION = (
    "너는 AI 트렌드 큐레이터다. 아래 '증거 노트'에 있는 사실만 근거로, 요청된 단 하나의 섹션만 작성한다. "
    "정확하고 자연스러운 한국어로 쓴다. 증거에 없는 사실·수치는 지어내지 말 것. "
    "기술 용어는 정확한 표기를 쓴다(예: 휴리스틱, 베이스라인, 딥리서치, 시맨틱)."
)

_SYS_SYNTH = (
    "너는 시니어 AI 애널리스트다. 섹션 초안들을 하나의 깊고 일관된 Teams 브리핑 카드로 종합한다. "
    "반드시 정확하고 자연스러운 한국어로 교정하며, 어색하거나 존재하지 않는 단어를 바로잡는다."
)


def _llm(messages: list, max_tokens: int = 600, temperature: float = 0.3, timeout: float = 120.0) -> str:
    tu.ensure_env_loaded()
    key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FIREWORKS_API_KEY not set (card_pipeline LLM 호출 불가)")
    r = requests.post(
        f"{LLM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": LLM_MODEL, "messages": messages,
              "max_tokens": max_tokens, "temperature": temperature},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def generate_section(evidence: str, label: str, instruction: str) -> str:
    """5-B: 한 섹션만 집중 생성 (독립 호출)."""
    user = (
        f"[증거 노트]\n{evidence}\n\n"
        f"[작성할 섹션] {label}\n[지침] {instruction}\n\n"
        f"이 한 섹션의 본문만 작성하라(100~300자). 다른 섹션은 쓰지 말 것. "
        f"'{label} '로 시작하는 한 덩어리로."
    )
    return _llm(
        [{"role": "system", "content": _SYS_SECTION},
         {"role": "user", "content": user}],
        max_tokens=12800,  # Kimi K2.6 reasoning_content 가 예산을 먹으므로 넉넉히
    )


def _parse_card_json(text: str) -> dict:
    """LLM 출력에서 JSON 카드 추출. reasoning 모델이 JSON 앞뒤에 추론 텍스트(중괄호 포함)를
    섞어 내보내도 견고하게: 균형 중괄호로 후보 객체들을 모두 뽑아 파싱되는 카드를 고른다."""
    t = re.sub(r"```(?:json)?", "", text)
    candidates = []
    depth, start = 0, None
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(t[start:i + 1])
                start = None
    # 가장 큰(=내용 많은) 후보부터, title/bullets 가진 dict 우선
    for c in sorted(candidates, key=len, reverse=True):
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("bullets" in obj or "title" in obj):
            return obj
    raise ValueError("카드 JSON 을 출력에서 찾지 못함")


def synthesize(drafts: Dict[str, str], evidence: str, card_type: str) -> dict:
    """5-C: 종합·스크리닝 1회 — 중복제거+경쟁구도+서사+한국어 교정+분량."""
    drafts_txt = "\n\n".join(f"{k}\n{v}" for k, v in drafts.items())
    user = (
        f"[증거 노트]\n{evidence}\n\n[섹션 초안들]\n{drafts_txt}\n\n"
        "[작업] 위 섹션 초안들을 종합해 하나의 카드로 완성하라:\n"
        "1) 섹션 간 중복 문장 제거.\n"
        "2) 경쟁 대안 2~3개를 '고유명'으로 비교해 우리 위치를 보강(증거에 있으면).\n"
        "3) 한국어 교정: 어색하거나 존재하지 않는 단어를 자연스럽게 바로잡기.\n"
        "4) 인과·수치 정확: ablation 은 '해당 요소의 기여도'로 정확히(예: 퍼지매칭이 +33%p 기여).\n\n"
        "[라벨 규칙 — 엄수]\n"
        "- 입력 섹션의 라벨을 그대로 유지하라. 멋대로 【개요】【효율】 등으로 바꾸지 말 것.\n"
        "- 특히 **【지금 왜 트렌드인가】 와 【우리에게 의미】 는 반드시 각각 독립 bullet 로 보존**(우리 팀 관련성이라 가장 중요).\n\n"
        "[개조식 + 하이라이트 — 가독성]\n"
        "- 정보 많은 섹션(구조/방법론/성능/실험 등)은 한 문단으로 길게 쓰지 말고, "
        "라벨 뒤에 줄바꿈(\\n)으로 **'• '로 시작하는 짧은 항목 2~4개**(개조식)로 나눠 써라.\n"
        "- ★핵심 수치·고유명·키워드는 마크다운 **굵게**(`**...**`)로 강조해 눈에 띄게 하라.\n"
        "  예: \"【성능】\\n• 재개 블록 **78토큰**(σ21.4) vs 베이스라인 159~170\\n• Decision recall **46.6%** (슬라이딩 29.6%·요약 37.6%·RAG 33.3%)\"\n"
        "- 서술이 자연스러운 섹션(무엇/우리에게 의미)은 1~2문장 산문으로 두되, 핵심은 **굵게**.\n\n"
        "[출력 규칙]\n"
        "- 코드펜스·설명 없이 **순수 JSON 객체 하나만**.\n"
        "- 키 3개: title(문자열), bullets(문자열 배열 — 각 '【라벨】 본문'), facts(객체).\n"
        "- bullets 마지막 두 개: '【출처】 URL·날짜', 그리고 액션 bullet 은 '☐ ' 다음 **바로 동사**로 시작('액션' 같은 라벨 단어 쓰지 말 것).\n"
        "- facts 는 빈 객체 {} 로 둬라(상단 표는 코드가 발표일만 따로 채운다). 모든 수치는 본문 bullet 으로.\n"
        "- 자리표시자('제목'·'...'·'발표일') 금지, 실제 내용으로.\n"
        "지금 완성된 카드 JSON 을 출력하라:"
    )
    out = _llm(
        [{"role": "system", "content": _SYS_SYNTH},
         {"role": "user", "content": user}],
        max_tokens=48000, temperature=0.2,  # reasoning + 카드 JSON 둘 다 들어가도록 넉넉히
    )
    card = _parse_card_json(out)
    if not isinstance(card.get("bullets"), list) or not card.get("title"):
        raise ValueError("synthesize: 카드 JSON 형식 불충분")
    card.setdefault("facts", {})
    return card


def _first_json_obj(text: str) -> Optional[dict]:
    """출력에서 첫 파싱 가능한 dict 추출 (reasoning/잡텍스트 방어)."""
    t = re.sub(r"```(?:json)?", "", text)
    depth, start = 0, None
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(t[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                start = None
    return None


def extract_facts(evidence: str) -> dict:
    """상단 표(FactSet)용 — 발표일 1개만 코드가 결정론적으로 확보(상단은 최대한 간결).
    나머지 수치·메타는 본문 bullet 으로 간다."""
    user = (
        "다음 증거에서 '발표일'(또는 게재일/출시일)만 뽑아라. 형식 YYYY-MM-DD.\n"
        "코드펜스·설명 없이 JSON 하나만: {\"발표일\":\"YYYY-MM-DD\"}\n\n[증거]\n" + evidence
    )
    try:
        out = _llm(
            [{"role": "system", "content": "너는 메타데이터 추출기다. JSON 객체만 출력한다."},
             {"role": "user", "content": user}],
            max_tokens=2000, temperature=0,
        )
        obj = _first_json_obj(out) or {}
    except Exception:
        return {}
    date = obj.get("발표일") or obj.get("date") or ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(date))
    return {"발표일": m.group(0)} if m else {}


def build_deep_card(evidence: str, card_type: str = "paper") -> dict:
    """심층 카드 생성 엔트리. 반환 dict 를 post_card(**card, source_url=...) 로 게시.
    반환: {"title": str, "bullets": [str...], "facts": {..}}.
    """
    specs = SECTION_SPECS.get(card_type, SECTION_SPECS["paper"])
    drafts: Dict[str, str] = {}
    for label, instruction in specs:
        drafts[label] = generate_section(evidence, label, instruction)  # 섹션마다 독립 호출
    card = synthesize(drafts, evidence, card_type)
    # facts 는 코드가 보장(합성이 비우는 경향 → 전용 추출로 override)
    facts = extract_facts(evidence)
    if facts:
        card["facts"] = facts
    return card
