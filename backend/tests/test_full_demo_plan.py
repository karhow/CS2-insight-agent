"""Tests for whole-demo recording plan."""
from app.recording.models import (
    DemoContext,
    RecordingOptions,
    RecordingRequestDTO,
    RequestType,
    SourceType,
    TargetPlayer,
)
from app.recording.plan_builder import build_plan


def _full_demo_dto(**kwargs) -> RecordingRequestDTO:
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
        win_panel_match_tick=498_000,
        all_players=[
            {"name": "Alice", "steamid64": "1", "spec_slot": 1, "team_num": 2},
            {"name": "Bob", "steamid64": "2", "spec_slot": 2, "team_num": 3},
        ],
    )
    opts = RecordingOptions(
        show_ingame_chat=True,
        voice_comm_boost=1.5,
        listen_all_voice=True,
    )
    base = dict(
        request_id="fd-1",
        request_type=RequestType.full_demo,
        source_type=SourceType.demo,
        demo=demo,
        target_player=TargetPlayer(name="Alice", steamid64="1", spec_slot=1),
        events=[],
        rounds=[],
        options=opts,
    )
    base.update(kwargs)
    return RecordingRequestDTO(**base)


def test_full_demo_single_segment_with_chat_and_voice_meta():
    plan = build_plan(_full_demo_dto())
    assert plan.request_type == RequestType.full_demo
    assert len(plan.segments) == 1
    seg = plan.segments[0]
    assert seg.metadata.get("full_demo") is True
    assert seg.metadata.get("show_ingame_chat") is True
    assert seg.metadata.get("voice_comm_boost") == 1.5
    assert seg.start_tick >= 10_000 - int(3 * 64)
    assert seg.end_tick < 500_000
    assert seg.voice_listen_mask is not None
    assert seg.voice_listen_mask > 0


def test_full_demo_respects_win_panel_ceiling():
    plan = build_plan(_full_demo_dto())
    seg = plan.segments[0]
    # win_panel 498000 - 2s guard = 497872
    assert seg.end_tick <= 498_000 - int(2 * 64)
