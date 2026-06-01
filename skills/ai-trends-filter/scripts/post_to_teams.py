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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import requests

WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()


def _resolve_history_path() -> Path:
    """이력 파일 경로 결정 — SKILL.md 의 dedup 읽기 경로($HERMES_HOME)와 일치시킨다."""
    explicit = os.environ.get("TREND_HISTORY_PATH", "").strip()
    if explicit:
        return Path(explicit)
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        return Path(hermes_home) / "trend_history.jsonl"
    return Path.home() / ".hermes" / "trend_history.jsonl"


HISTORY_PATH = _resolve_history_path()


def _build_payload(title: str, bullets: Iterable[str]) -> dict:
    body = [
        {
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "text": title,
            "wrap": True,
        }
    ]
    for line in bullets:
        body.append(
            {
                "type": "TextBlock",
                "text": f"• {line}",
                "wrap": True,
            }
        )
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": body,
                },
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
    timeout: float = 15.0,
) -> requests.Response:
    if not WEBHOOK_URL:
        raise RuntimeError(
            "TEAMS_WEBHOOK_URL env var is not set. "
            "Add it to $HERMES_HOME/.env (loaded by hermes gateway) and restart gateway, "
            "or export it before running standalone tests."
        )
    bullets_list = list(bullets)
    payload = _build_payload(title, bullets_list)
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
