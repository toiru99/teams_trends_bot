"""ai-trends-filter 결정론 유틸.

원칙: **판단(선별·점수·서술·사이트 적응)은 LLM 이, 기계적·결정론적 작업은 여기 코드가.**
LLM 이 매 실행 인라인으로 재구현하지 말고 이 모듈을 import 해서 쓴다:

    import os, sys
    sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "skills", "ai-trends-filter", "scripts"))
    import trends_util as tu
    recent = tu.recent_history(7)                 # 7일 이력
    if tu.is_duplicate_url(url, recent): ...       # URL 정확 일치 중복 (의미 중복은 LLM 판단)
    bonus = tu.freshness_bonus("2026-05-28")       # 신선도 가점(+1 if <=14일)
    html = tu.fetch(url)                           # requests→jina 결정론 페치 (None 이면 LLM 이 browser)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import requests

_UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-trends-filter/1.0)"}


# ── 환경/경로 (post_to_teams 와 동일 규칙 — 쓰기/읽기 경로 단일화) ──────────────

def _parse_env_file(path: Path) -> None:
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


def ensure_env_loaded() -> None:
    """TEAMS_WEBHOOK_URL 이 없으면 $HERMES_HOME/.env → ~/.hermes/.env 를 결정론적으로 로드."""
    if os.environ.get("TEAMS_WEBHOOK_URL", "").strip():
        return
    candidates = []
    hh = os.environ.get("HERMES_HOME", "").strip()
    if hh:
        candidates.append(Path(hh) / ".env")
    candidates.append(Path.home() / ".hermes" / ".env")
    for env_file in candidates:
        if env_file.is_file():
            _parse_env_file(env_file)
            if os.environ.get("TEAMS_WEBHOOK_URL", "").strip():
                return


def resolve_history_path() -> Path:
    """이력 파일 경로 — 읽기(여기)와 쓰기(post_to_teams)가 항상 같은 파일을 가리키도록."""
    explicit = os.environ.get("TREND_HISTORY_PATH", "").strip()
    if explicit:
        return Path(explicit)
    hh = os.environ.get("HERMES_HOME", "").strip()
    if hh:
        return Path(hh) / "trend_history.jsonl"
    return Path.home() / ".hermes" / "trend_history.jsonl"


# ── 이력 / 중복 (결정론) ──────────────────────────────────────────────────────

def recent_history(days: int = 7) -> List[dict]:
    """최근 N일 게시 이력 레코드 리스트. dedup 기준으로 사용."""
    path = resolve_history_path()
    if not path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            ts = datetime.fromisoformat(str(rec.get("ts", "")))
        except (ValueError, json.JSONDecodeError):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            out.append(rec)
    return out


def _norm_url(u: str) -> str:
    """URL 정규화 — scheme/www/트레일링슬래시/쿼리 제거해 정확비교 안정화."""
    if not u:
        return ""
    u = u.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("?", 1)[0].split("#", 1)[0]
    return u.rstrip("/")


def is_duplicate_url(url: str, recent: Optional[List[dict]] = None) -> bool:
    """URL 정확 일치 중복 여부(결정론). 의미 중복은 LLM 이 따로 판단."""
    if not url:
        return False
    if recent is None:
        recent = recent_history(7)
    n = _norm_url(url)
    return any(_norm_url(r.get("source_url", "")) == n for r in recent if r.get("source_url"))


# ── 신선도 (결정론 날짜 계산) ─────────────────────────────────────────────────

def days_since(date_str: str) -> Optional[int]:
    """발표일 문자열 → 오늘(UTC)까지 경과 일수. 파싱 실패 시 None."""
    if not date_str:
        return None
    s = str(date_str).strip()
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    if m:
        s = m.group(0)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            d = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - d).days
        except ValueError:
            continue
    return None


def freshness_bonus(date_str: str) -> int:
    """Step 4 신선도 가점: 14일 이내 +1, 그 외 0. (30일 초과 하드게이트는 LLM/Step0)."""
    d = days_since(date_str)
    if d is None:
        return 0
    return 1 if d <= 14 else 0


# ── 페치 (결정론 escalation: requests → jina) ─────────────────────────────────

def fetch(url: str, timeout: float = 20.0, min_len: int = 200) -> Optional[str]:
    """1차 출처 본문 텍스트. requests→jina.ai 순으로 시도. 둘 다 실패하면 None
    (이때 LLM 이 agent-browser 도구로 직접 열어야 한다 — HOW 는 사이트마다 달라 판단 영역)."""
    try:
        r = requests.get(url, headers=_UA, timeout=timeout)
        if r.status_code == 200 and len(r.text) >= min_len:
            return r.text
    except requests.RequestException:
        pass
    try:
        bare = re.sub(r"^https?://", "", url)
        jr = requests.get(f"https://r.jina.ai/http://{bare}", headers=_UA, timeout=timeout)
        if jr.status_code == 200 and len(jr.text) >= min_len:
            return jr.text
    except requests.RequestException:
        pass
    return None
