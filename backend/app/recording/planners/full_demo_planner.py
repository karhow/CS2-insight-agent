import logging

from ..models import RecordingSegment, SourceType, Perspective
from ..normalizer import NormalizedRequest
from ..full_demo_death_follow import build_death_follow_schedule
from ..platform_utils import (
    platform_slot_offset,
    compute_voice_listen_all_mask,
)
from ..planners.round_pov_planner import sec_to_ticks

logger = logging.getLogger(__name__)

_WIN_PANEL_GUARD_SEC = 2.0


def _win_panel_ceiling(win_panel_tick: int, tick_rate: float) -> int | None:
    if not win_panel_tick or win_panel_tick <= 0:
        return None
    guard_ticks = max(1, sec_to_ticks(_WIN_PANEL_GUARD_SEC, tick_rate))
    return max(0, int(win_panel_tick) - guard_ticks)


def plan_full_demo(req: NormalizedRequest) -> tuple[list[RecordingSegment], list[str]]:
    """Single continuous segment covering the whole match demo."""
    planner_warnings: list[str] = []
    tick_rate = req.demo.tick_rate
    opts = req.options
    preroll_ticks = sec_to_ticks(opts.round_freeze_preroll_sec, tick_rate)

    start_tick = max(req.demo.first_tick, 0)
    if start_tick > 0 and preroll_ticks > 0:
        start_tick = max(0, start_tick - preroll_ticks)

    end_tick = req.demo.demo_end_tick
    win_ceiling = _win_panel_ceiling(req.demo.win_panel_match_tick, tick_rate)
    if win_ceiling is not None and win_ceiling > start_tick:
        end_tick = min(end_tick, win_ceiling)

    exit_guard = sec_to_ticks(opts.demo_end_guard_sec, tick_rate)
    end_tick = max(start_tick + 1, end_tick - exit_guard)

    offset = platform_slot_offset(req.demo.demo_filename, req.demo.server_name)
    if opts.listen_all_voice:
        voice_mask = compute_voice_listen_all_mask(req.demo.all_players, offset)
    else:
        from ..platform_utils import compute_voice_listen_mask

        voice_mask = compute_voice_listen_mask(
            req.demo.all_players, req.target_player.steamid64, offset
        )

    logger.info(
        "[RecordingV3][FullDemo] start=%d end=%d duration≈%.1fs chat=%s voice_boost=%s death_follow=%s",
        start_tick,
        end_tick,
        (end_tick - start_tick) / tick_rate if tick_rate > 0 else 0,
        opts.show_ingame_chat,
        opts.voice_comm_boost,
        opts.death_follow_mode,
    )

    death_follow_mode = (opts.death_follow_mode or "off").strip().lower()
    death_schedule: list = []
    death_warnings: list[str] = []
    if death_follow_mode not in ("off", ""):
        death_schedule, death_warnings = build_death_follow_schedule(
            req.demo.demo_path,
            target_name=req.target_player.name,
            target_steamid=req.target_player.steamid64,
            all_players=req.demo.all_players or [],
            mode=death_follow_mode,
            tick_rate=tick_rate,
            post_death_sec=float(opts.death_follow_post_sec),
            match_start_tick=max(req.demo.first_tick, 0),
        )
        for w in death_warnings:
            logger.info("[RecordingV3][FullDemo][DeathFollow] %s", w)
        planner_warnings.extend(death_warnings)

    segment = RecordingSegment(
        segment_index=0,
        source_type=SourceType.demo,
        start_tick=start_tick,
        end_tick=end_tick,
        anchor_ticks=[],
        round=None,
        target_player_name=req.target_player.name,
        target_steamid64=req.target_player.steamid64,
        target_spec_slot=req.target_player.spec_slot,
        perspective=Perspective.main,
        is_final_round=True,
        safe_seek_tick=start_tick,
        safe_end_tick=end_tick,
        disabled=False,
        disabled_reason=None,
        metadata={
            "full_demo": True,
            "show_ingame_chat": bool(opts.show_ingame_chat),
            "voice_comm_boost": float(opts.voice_comm_boost),
            "listen_all_voice": bool(opts.listen_all_voice),
            "death_follow_mode": death_follow_mode if death_follow_mode not in ("", "off") else "off",
            "death_follow_schedule": death_schedule,
            "end_reason": "full_demo_match",
        },
        voice_listen_mask=voice_mask,
        voice_listen_mask_enemy=None,
    )
    return [segment], planner_warnings
