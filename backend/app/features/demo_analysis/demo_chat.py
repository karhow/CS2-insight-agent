"""Extract in-game text chat from CS2 demo files via demoparser2."""
from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
from demoparser2 import DemoParser

from .parse_utils import _DEMOPARSER_RE_RAISE, _to_pandas_df

logger = logging.getLogger(__name__)

# CS2 文字聊天走 User Message（SayText / SayText2），不是常规 game event。
# demoparser2 0.41.x 的 Python/JS 公开 API 尚无 parse_chat_messages，只能尝试
# demo 内是否碰巧注册了 say/chat 类 game event（多数竞技 demo 没有）。
_CHAT_EVENT_CANDIDATES = (
    "player_say",
    "player_chat",
    "say_text",
    "player_chat_info",
)

_PLAYER_COLS = (
    "user_name",
    "attacker_name",
    "player_name",
    "name",
)
_TEXT_COLS = (
    "text",
    "message",
    "say_text",
    "chat",
    "chat_message",
)
_TEAM_COLS = ("team", "team_num")
_ROUND_COLS = ("total_rounds_played",)


def _first_col(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def _cell_str(row: pd.Series, col: str | None) -> str:
    if not col:
        return ""
    val = row.get(col)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s


def _normalize_chat_row(row: pd.Series, event_name: str) -> dict[str, Any] | None:
    tick_raw = row.get("tick")
    try:
        tick = int(float(tick_raw))
    except (TypeError, ValueError):
        return None

    player_col = _first_col(row.to_frame().T, _PLAYER_COLS)
    text_col = _first_col(row.to_frame().T, _TEXT_COLS)
    player = _cell_str(row, player_col)
    text = _cell_str(row, text_col)
    if not text:
        return None

    team_col = _first_col(row.to_frame().T, _TEAM_COLS)
    round_col = _first_col(row.to_frame().T, _ROUND_COLS)
    team = _cell_str(row, team_col)
    rnd = _cell_str(row, round_col)
    round_num: int | None = None
    if rnd:
        try:
            round_num = int(float(rnd)) + 1
        except (TypeError, ValueError):
            round_num = None

    channel = _cell_str(row, "chat") or _cell_str(row, "messagename") or ""
    return {
        "tick": tick,
        "round": round_num,
        "player": player or "unknown",
        "text": text,
        "team": team,
        "channel": channel,
        "event": event_name,
    }


def _chat_diagnostics(available: set[str], event_names: list[str]) -> dict[str, Any]:
    say_like = sorted(e for e in available if re.search(r"say|chat", e, re.I))
    return {
        "parser": "demoparser2",
        "chat_api_available": False,
        "events_tried": event_names,
        "say_like_events_in_demo": say_like,
        "note_zh": (
            "CS2 文字聊天在 demo 里是网络 User Message（SayText2），不是 player_death 这类 game event。"
            "当前 demoparser2 0.41.x 尚未提供 parse_chat_messages，因此多数 demo 会解析为空。"
            "另：竞技 demo 常不记录队伍频道，即便未来支持解析也可能只有全体聊天。"
        ),
        "note_en": (
            "CS2 text chat is stored as network user messages (SayText2), not standard game events. "
            "demoparser2 0.41.x does not expose parse_chat_messages yet, so most demos return empty. "
            "Competitive demos also often omit team chat even when parsing is supported."
        ),
    }


def parse_demo_chat_messages(dem_path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (messages, diagnostics)."""
    parser = DemoParser(dem_path)
    try:
        available = set(parser.list_game_events() or [])
    except BaseException as e:
        if isinstance(e, _DEMOPARSER_RE_RAISE):
            raise
        logger.warning("list_game_events failed for %s: %s", dem_path, e)
        available = set()

    event_names = [e for e in _CHAT_EVENT_CANDIDATES if e in available]
    if not event_names:
        event_names = sorted(
            e for e in available if re.search(r"say|chat", e, re.I)
        )

    messages: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()

    for ev in event_names:
        try:
            df = _to_pandas_df(parser.parse_event(ev))
        except BaseException as e:
            if isinstance(e, _DEMOPARSER_RE_RAISE):
                raise
            logger.debug("parse_event(%s) failed: %s", ev, e)
            continue
        if df.empty:
            continue
        for _, row in df.iterrows():
            item = _normalize_chat_row(row, ev)
            if not item:
                continue
            key = (item["tick"], item["player"], item["text"])
            if key in seen:
                continue
            seen.add(key)
            messages.append(item)

    messages.sort(key=lambda m: (m["tick"], m["player"], m["text"]))
    diag = _chat_diagnostics(available, event_names)
    if not messages and not event_names:
        logger.info(
            "demo chat empty: no say/chat game events in demo (path=%s say_like=%s)",
            dem_path,
            diag.get("say_like_events_in_demo"),
        )
    return messages, diag
