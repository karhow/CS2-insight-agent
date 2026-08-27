from app.features.demo_analysis.demo_chat import _normalize_chat_row
import pandas as pd


def test_normalize_chat_row_player_say():
    row = pd.Series(
        {
            "tick": 12345,
            "user_name": "Alice",
            "text": "rush B",
            "total_rounds_played": 4,
        }
    )
    out = _normalize_chat_row(row, "player_say")
    assert out is not None
    assert out["tick"] == 12345
    assert out["player"] == "Alice"
    assert out["text"] == "rush B"
    assert out["round"] == 5


def test_normalize_chat_row_chat_message_column():
    row = pd.Series(
        {
            "tick": 4954,
            "user_name": "Player1",
            "chat_message": "rush B",
        }
    )
    out = _normalize_chat_row(row, "chat_message")
    assert out is not None
    assert out["text"] == "rush B"
    assert out["player"] == "Player1"
    assert out["event"] == "chat_message"


def test_chat_diagnostics_when_no_events():
    from app.features.demo_analysis.demo_chat import _chat_diagnostics

    diag = _chat_diagnostics(set(["player_death", "weapon_fire"]), [])
    assert diag["chat_api_available"] is False
    assert diag["events_tried"] == []
