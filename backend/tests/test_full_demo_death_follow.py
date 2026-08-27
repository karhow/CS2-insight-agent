"""Tests for full-demo death-follow schedule builder."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.recording.full_demo_death_follow import (
    _alive_teammates,
    build_death_follow_schedule,
)
from app.recording.models import (
    DemoContext,
    RecordingOptions,
    RecordingRequestDTO,
    RequestType,
    SourceType,
    TargetPlayer,
)
from app.recording.plan_builder import build_plan

_SAMPLE_DEMO = r"D:\download\DEMO\9223057596767899916_0.dem"


def test_alive_teammates_excludes_dead_and_target():
    by_steam = {}
    by_name = {
        "alice": {"name": "Alice", "steamid64": "1", "spec_slot": 1, "team_num": 2},
        "bob": {"name": "Bob", "steamid64": "2", "spec_slot": 2, "team_num": 2},
        "dave": {"name": "Dave", "steamid64": "4", "spec_slot": 4, "team_num": 2},
        "carol": {"name": "Carol", "steamid64": "3", "spec_slot": 3, "team_num": 3},
    }
    deaths = [{"tick": 100, "victim": "Bob"}]
    mates = _alive_teammates(
        round_num=1,
        death_tick=200,
        target_name="Alice",
        target_steamid="1",
        team_num=2,
        deaths_in_round=deaths,
        by_steam=by_steam,
        by_name=by_name,
    )
    names = {m["name"] for m in mates}
    assert names == {"Dave"}
    assert "Alice" not in names
    assert "Carol" not in names


def test_build_plan_includes_death_follow_schedule():
    fake_schedule = [
        {
            "tick": 5000,
            "action": "away",
            "player_name": "Killer",
            "steamid64": "9",
            "spec_slot": 4,
            "round": 1,
            "reason": "killer",
        },
        {
            "tick": 8000,
            "action": "back",
            "player_name": "Alice",
            "steamid64": "1",
            "spec_slot": 1,
            "round": 2,
            "reason": "respawn",
        },
    ]
    demo = DemoContext(
        demo_path="/tmp/match.dem",
        demo_filename="match.dem",
        map_name="de_dust2",
        tick_rate=64.0,
        first_tick=10_000,
        demo_end_tick=500_000,
        final_round=24,
        final_round_start_tick=480_000,
        final_round_end_tick=499_000,
        all_players=[
            {"name": "Alice", "steamid64": "1", "spec_slot": 1, "team_num": 2},
        ],
    )
    dto = RecordingRequestDTO(
        request_id="fd-df-1",
        request_type=RequestType.full_demo,
        source_type=SourceType.demo,
        demo=demo,
        target_player=TargetPlayer(name="Alice", steamid64="1", spec_slot=1),
        options=RecordingOptions(death_follow_mode="killer"),
    )
    with patch(
        "app.recording.planners.full_demo_planner.build_death_follow_schedule",
        return_value=(fake_schedule, []),
    ):
        plan = build_plan(dto)
    seg = plan.segments[0]
    assert seg.metadata.get("death_follow_mode") == "killer"
    assert seg.metadata.get("death_follow_schedule") == fake_schedule


@pytest.mark.skipif(not os.path.isfile(_SAMPLE_DEMO), reason="sample demo missing")
def test_build_schedule_on_local_demo():
    schedule, warnings = build_death_follow_schedule(
        _SAMPLE_DEMO,
        target_name="惠州学院-TOP1317",
        target_steamid="76561198978575399",
        all_players=[],
        mode="killer",
        tick_rate=64.0,
        post_death_sec=1.0,
    )
    assert isinstance(schedule, list)
    assert isinstance(warnings, list)
    if schedule:
        assert any(s["action"] == "away" for s in schedule)
