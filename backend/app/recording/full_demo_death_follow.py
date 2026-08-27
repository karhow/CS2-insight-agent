"""Build spec-switch schedule for full-demo death follow (killer / teammate)."""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

import pandas as pd
from demoparser2 import DemoParser

from ..features.demo_analysis.parse_utils import _DEMOPARSER_RE_RAISE, _to_pandas_df, safe_parse_events_batch

logger = logging.getLogger(__name__)

_DEATH_FOLLOW_MODES = frozenset({"off", "killer", "teammate"})


def _int_cell(val: object) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _str_cell(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _round_from_row(row: pd.Series) -> int:
    rnd = row.get("total_rounds_played")
    if rnd is None or (isinstance(rnd, float) and pd.isna(rnd)):
        return 0
    return _int_cell(rnd) + 1


def _freeze_end_ticks_by_round(freeze_end_df: pd.DataFrame) -> dict[int, int]:
    out: dict[int, int] = {}
    if freeze_end_df.empty or "tick" not in freeze_end_df.columns:
        return out
    df = freeze_end_df.copy()
    df["_tick"] = pd.to_numeric(df["tick"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("_tick")
    for idx, (_, row) in enumerate(df.iterrows()):
        rnd = _round_from_row(row) or (idx + 1)
        out[rnd] = int(row["_tick"])
    return out


def _round_at_tick(tick: int, freeze_by_round: dict[int, int]) -> int:
    """Infer round number from freeze_end boundaries when death rows lack round."""
    if not freeze_by_round:
        return 0
    rnd = 1
    for r in sorted(freeze_by_round.keys()):
        if freeze_by_round[r] <= tick:
            rnd = r
        else:
            break
    return rnd


def _roster_index(all_players: list) -> tuple[dict[str, dict], dict[str, dict]]:
    by_steam: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for raw in all_players or []:
        if not isinstance(raw, dict):
            continue
        name = _str_cell(raw.get("name"))
        steam = _str_cell(raw.get("steamid64"))
        entry = {
            "name": name,
            "steamid64": steam,
            "spec_slot": raw.get("spec_slot"),
            "team_num": raw.get("team_num"),
        }
        if steam:
            by_steam[steam] = entry
        if name:
            by_name[name.lower()] = entry
    return by_steam, by_name


def _lookup_player(
    name: str,
    steamid: str,
    by_steam: dict[str, dict],
    by_name: dict[str, dict],
) -> dict[str, Any]:
    if steamid and steamid in by_steam:
        return by_steam[steamid]
    if name and name.lower() in by_name:
        return by_name[name.lower()]
    return {"name": name, "steamid64": steamid, "spec_slot": None, "team_num": None}


def _target_team(
    target_name: str,
    target_steamid: str,
    by_steam: dict[str, dict],
    by_name: dict[str, dict],
) -> Optional[int]:
    p = _lookup_player(target_name, target_steamid, by_steam, by_name)
    tn = p.get("team_num")
    if tn is None:
        return None
    try:
        return int(float(tn))
    except (TypeError, ValueError):
        return None


def _alive_teammates(
    *,
    round_num: int,
    death_tick: int,
    target_name: str,
    target_steamid: str,
    team_num: Optional[int],
    deaths_in_round: list[dict],
    by_steam: dict[str, dict],
    by_name: dict[str, dict],
) -> list[dict]:
    if team_num is None:
        return []
    dead_names = {
        _str_cell(d.get("victim")).lower()
        for d in deaths_in_round
        if _int_cell(d.get("tick")) <= death_tick
    }
    dead_names.add(target_name.lower())

    mates: list[dict] = []
    seen: set[str] = set()
    for raw in list(by_name.values()):
        name = _str_cell(raw.get("name"))
        if not name or name.lower() in dead_names:
            continue
        try:
            if int(float(raw.get("team_num"))) != team_num:
                continue
        except (TypeError, ValueError):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        mates.append(raw)
    return mates


def _switch_entry(
    tick: int,
    action: str,
    player: dict,
    *,
    round_num: int = 0,
    reason: str = "",
) -> dict[str, Any]:
    slot = player.get("spec_slot")
    try:
        slot_i = int(slot) if slot is not None else None
    except (TypeError, ValueError):
        slot_i = None
    return {
        "tick": int(tick),
        "action": action,
        "player_name": _str_cell(player.get("name")),
        "steamid64": _str_cell(player.get("steamid64")),
        "spec_slot": slot_i,
        "round": round_num,
        "reason": reason,
    }


def build_death_follow_schedule(
    dem_path: str,
    *,
    target_name: str,
    target_steamid: str,
    all_players: list,
    mode: str,
    tick_rate: float,
    post_death_sec: float = 1.0,
    match_start_tick: int = 0,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (schedule sorted by tick, warnings). mode: off | killer | teammate."""
    mode = (mode or "off").strip().lower()
    if mode not in _DEATH_FOLLOW_MODES or mode == "off":
        return [], []

    warnings: list[str] = []
    by_steam, by_name = _roster_index(all_players)
    main_player = _lookup_player(target_name, target_steamid, by_steam, by_name)
    team_num = _target_team(target_name, target_steamid, by_steam, by_name)

    parser = DemoParser(dem_path)
    batch = safe_parse_events_batch(parser, ["player_death", "round_freeze_end"])
    death_df = batch.get("player_death", pd.DataFrame())
    freeze_df = batch.get("round_freeze_end", pd.DataFrame())

    if death_df.empty:
        warnings.append("death_follow: no player_death events in demo")
        return [], warnings

    if match_start_tick > 0 and "tick" in death_df.columns:
        death_df = death_df.loc[
            pd.to_numeric(death_df["tick"], errors="coerce").fillna(0).astype(int)
            >= match_start_tick
        ].copy()

    target_l = target_name.strip().lower()
    freeze_by_round = _freeze_end_ticks_by_round(freeze_df)
    post_ticks = max(1, int(float(post_death_sec) * float(tick_rate or 64)))
    target_deaths: list[dict] = []
    deaths_by_round: dict[int, list[dict]] = {}

    for _, row in death_df.iterrows():
        vic = _str_cell(row.get("user_name"))
        tick = _int_cell(row.get("tick"))
        rnd = _round_from_row(row)
        if tick <= 0:
            continue
        rec = {
            "tick": tick,
            "round": rnd,
            "victim": vic,
            "attacker": _str_cell(row.get("attacker_name")),
            "attacker_steamid": _str_cell(row.get("attacker_steamid")),
            "victim_steamid": _str_cell(row.get("user_steamid")),
        }
        if rec["round"] <= 0:
            rec["round"] = _round_at_tick(tick, freeze_by_round)
        if rec["round"] > 0:
            deaths_by_round.setdefault(rec["round"], []).append(rec)
        vic_steam = rec["victim_steamid"]
        if vic.lower() == target_l or (target_steamid and vic_steam == target_steamid):
            target_deaths.append(rec)

    if not target_deaths:
        warnings.append(f"death_follow: no deaths found for {target_name!r}")
        return [], warnings

    schedule: list[dict[str, Any]] = []
    rng = random.Random(hash((dem_path, target_steamid or target_name, mode)) & 0xFFFFFFFF)

    for death in sorted(target_deaths, key=lambda d: d["tick"]):
        rnd = death["round"]
        death_tick = death["tick"]
        away_tick = death_tick + post_ticks

        away_player: Optional[dict] = None
        reason = mode

        if mode == "killer":
            atk_name = death["attacker"]
            atk_steam = death["attacker_steamid"]
            if atk_name and atk_name.lower() != target_l:
                away_player = _lookup_player(atk_name, atk_steam, by_steam, by_name)
                reason = "killer"
            else:
                mates = _alive_teammates(
                    round_num=rnd,
                    death_tick=death_tick,
                    target_name=target_name,
                    target_steamid=target_steamid,
                    team_num=team_num,
                    deaths_in_round=deaths_by_round.get(rnd, []),
                    by_steam=by_steam,
                    by_name=by_name,
                )
                if mates:
                    away_player = mates[rng.randrange(len(mates))]
                    reason = "killer_fallback_teammate"
                    warnings.append(
                        f"death_follow: round {rnd} no valid killer; using teammate"
                    )
        elif mode == "teammate":
            mates = _alive_teammates(
                round_num=rnd,
                death_tick=death_tick,
                target_name=target_name,
                target_steamid=target_steamid,
                team_num=team_num,
                deaths_in_round=deaths_by_round.get(rnd, []),
                by_steam=by_steam,
                by_name=by_name,
            )
            if mates:
                away_player = mates[rng.randrange(len(mates))]
            else:
                warnings.append(
                    f"death_follow: round {rnd} no alive teammate at tick {death_tick}; skip switch"
                )

        if away_player and _str_cell(away_player.get("name")):
            schedule.append(
                _switch_entry(
                    away_tick, "away", away_player, round_num=rnd, reason=reason
                )
            )
            back_tick = freeze_by_round.get(rnd + 1)
            if back_tick is not None and back_tick > away_tick:
                schedule.append(
                    _switch_entry(
                        back_tick,
                        "back",
                        main_player,
                        round_num=rnd + 1,
                        reason="respawn",
                    )
                )

    schedule.sort(key=lambda s: (s["tick"], 0 if s["action"] == "away" else 1))
    logger.info(
        "[FullDemo][DeathFollow] mode=%s deaths=%d switches=%d path=%s",
        mode,
        len(target_deaths),
        len(schedule),
        dem_path,
    )
    return schedule, warnings
