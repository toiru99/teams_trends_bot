"""Microsoft Teams AI Trends 채널 webhook poster.

`post_card(title, bullets, source_url=None, summary=None)` 로 호출하면
Power Automate workflow trigger 로 AdaptiveCard 를 던지고, 성공 시 게시 이력을
이력 파일에 append 한다 (LLM dedup 용).

이력 파일 경로 결정 순서:
  1) 환경변수 `TREND_HISTORY_PATH` (명시적 지정)
  2) `$HERMES_HOME/trend_history.jsonl` (HERMES_HOME 설정 시 — SKILL.md 의 dedup 읽기 경로와 일치)
  3) `~/.hermes/trend_history.jsonl` (위 둘 다 없을 때 fallback)

CLI 사용:

    python post_to_teams.py "제목" "bullet 1" "bullet 2" \\
        --source-url https://github.com/foo/bar \\
        --summary "한줄 요약"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import requests

# 결정론 유틸(env 로딩·이력 경로)을 trends_util 로 단일화 — 읽기/쓰기 경로 분기 방지.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trends_util import ensure_env_loaded, resolve_history_path  # noqa: E402

ensure_env_loaded()
WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
HISTORY_PATH = resolve_history_path()


_LABEL_RE = re.compile(r"^\s*(【[^】]+】)")


def _build_payload(
    title: str,
    bullets: Iterable[str],
    facts: Optional[dict] = None,
    source_url: Optional[str] = None,
    source_label: str = "원문 열기",
) -> dict:
    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": title,
            "wrap": True,
        }
    ]
    # 기본 정보 표 → FactSet. 방어: 값은 문자열로 강제(리스트→결합), 너무 많으면 잘라 깔끔히.
    if facts:
        def _fact_val(v):
            if isinstance(v, (list, tuple)):
                return ", ".join(str(x) for x in v)
            if isinstance(v, dict):
                return ", ".join(f"{k}: {x}" for k, x in v.items())
            return str(v)
        fact_items = [{"title": str(k), "value": _fact_val(v)} for k, v in list(facts.items())[:6]]
        body.append({"type": "FactSet", "separator": True, "facts": fact_items})
    # 본문 bullet — 【라벨】 강조 + 구분선으로 섹션처럼
    for line in bullets:
        line = str(line)
        m = _LABEL_RE.match(line)
        if m:
            label = m.group(1)
            rest = line[m.end():].strip()
            if "우리에게 의미" in label:
                # 팀이 가장 봐야 할 섹션 1곳만 accent 박스로 강조 (색 도배는 안 함)
                items = [{"type": "TextBlock", "text": label, "weight": "Bolder", "wrap": True}]
                if rest:
                    items.append({"type": "TextBlock", "text": rest, "wrap": True, "spacing": "Small"})
                body.append(
                    {"type": "Container", "style": "accent", "separator": True,
                     "spacing": "Medium", "items": items}
                )
            else:
                # 일반 섹션: 라벨을 별도 줄 헤더(Accent·구분선)로
                body.append(
                    {"type": "TextBlock", "text": label, "weight": "Bolder",
                     "color": "Accent", "wrap": True, "separator": True, "spacing": "Medium"}
                )
                if rest:
                    body.append({"type": "TextBlock", "text": rest, "wrap": True, "spacing": "Small"})
        else:
            # 라벨 없는 줄 (☐ 액션·일반). ☐ 액션은 굵게.
            blk = {"type": "TextBlock", "text": line, "wrap": True,
                   "separator": True, "spacing": "Small"}
            if line.strip().startswith("☐"):
                blk["weight"] = "Bolder"
            body.append(blk)
    # 출처는 하단 "원문 열기" 버튼(actions)으로만 — 본문 중복 링크 제거
    content = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        # Teams 전용: 카드를 좁은 기본폭이 아닌 대화 폭 전체로 렌더링 (가로 줄바꿈 감소)
        "msteams": {"width": "Full"},
    }
    if source_url:
        content["actions"] = [
            {"type": "Action.OpenUrl", "title": source_label, "url": source_url}
        ]
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": content,
            }
        ],
    }


def _append_history(record: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def post_card(
    title: str,
    bullets: Iterable[str],
    source_url: Optional[str] = None,
    summary: Optional[str] = None,
    facts: Optional[dict] = None,
    source_label: str = "원문 열기",
    timeout: float = 15.0,
) -> requests.Response:
    """Teams 채널에 AdaptiveCard 게시 + 이력 append.

    facts: {"⭐":"28.2k", "License":"GPL-3.0", ...} 형태면 카드 상단에 표(FactSet)로 렌더링.
    source_url: 주어지면 "원문 열기" 버튼 + 본문 링크 추가 (dedup 이력에도 기록).
    기존 호출 post_card(title, bullets, source_url=, summary=) 은 그대로 동작 (하위호환).
    """
    if not WEBHOOK_URL:
        raise RuntimeError(
            "TEAMS_WEBHOOK_URL env var is not set. "
            "Add it to $HERMES_HOME/.env (loaded by hermes gateway) and restart gateway, "
            "or export it before running standalone tests."
        )
    bullets_list = list(bullets)
    payload = _build_payload(
        title, bullets_list, facts=facts, source_url=source_url, source_label=source_label
    )
    response = requests.post(WEBHOOK_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    _append_history(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "source_url": source_url,
            "summary": summary or (bullets_list[0] if bullets_list else None),
            "bullets": bullets_list,
        }
    )
    return response


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Teams AI Trends 카드 게시 + 이력 기록")
    parser.add_argument("title", help="카드 제목")
    parser.add_argument("bullets", nargs="+", help="bullet 라인들 (1개 이상)")
    parser.add_argument("--source-url", default=None, help="1차 출처 URL (dedup 용)")
    parser.add_argument("--summary", default=None, help="의미 dedup 용 한줄 요약 (생략시 첫 bullet)")
    args = parser.parse_args(argv)

    response = post_card(
        title=args.title,
        bullets=args.bullets,
        source_url=args.source_url,
        summary=args.summary,
    )
    print(f"상태코드: {response.status_code}")
    print(f"응답: {response.text}")
    print(f"이력 기록: {HISTORY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
