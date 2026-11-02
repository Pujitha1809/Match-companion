"""Unit tests for live simulation progression, Dugout AI Q&A, and dynamic captain switching."""

from engine.points import compute_ball_deltas
from engine.whatif import calculate_captain_whatifs
from ai.narrator import answer_fan_query, build_deterministic_dugout_fallback


def test_whatif_captain_switching_impact():
    """Verifies dynamic captain switching correctly shifts multipliers and differentials."""
    base_points = {
        "V Kohli": 15.0,
        "JJ Bumrah": 33.0,
        "RG Sharma": 10.0,
    }

    # Initial captain: Kohli
    whatifs_kohli = calculate_captain_whatifs(base_points, current_captain="V Kohli")
    bumrah_option = next(w for w in whatifs_kohli if w["player"] == "JJ Bumrah")
    assert bumrah_option["net_difference"] == 18.0
    assert bumrah_option["alternate_total_change"] == "+18 pts"

    # Switching captain to Bumrah
    whatifs_bumrah = calculate_captain_whatifs(base_points, current_captain="JJ Bumrah")
    kohli_option = next(w for w in whatifs_bumrah if w["player"] == "V Kohli")
    assert kohli_option["net_difference"] == -18.0
    assert kohli_option["alternate_total_change"] == "-18 pts"


def test_dugout_ai_query_bowling_english(monkeypatch):
    """Verifies Dugout AI provides relevant tactical insight on bowling in English."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    snapshot = {
        "delivery_display": "Over 17.3",
        "innings": 2,
        "team_batting": "South Africa",
        "batter": "KA Maharaj",
        "bowler": "JJ Bumrah",
        "team_points": 145.0,
        "captain_name": "JJ Bumrah",
        "vc_name": "V Kohli",
        "last_event": "Wicket (Bowled +8 bonus)",
    }
    answer = answer_fan_query("Why is this bowler bowling right now?", snapshot, language="English")
    assert "JJ Bumrah" in answer or "bowler" in answer.lower()
    assert len(answer.split()) < 45


def test_dugout_ai_query_upside_hinglish(monkeypatch):
    """Verifies Dugout AI provides natural Hinglish response for upside queries."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    snapshot = {
        "delivery_display": "Over 19.1",
        "innings": 2,
        "team_batting": "South Africa",
        "batter": "DA Miller",
        "bowler": "HH Pandya",
        "team_points": 180.0,
        "captain_name": "V Kohli",
        "vc_name": "JJ Bumrah",
        "last_event": "Wicket (Caught)",
    }
    answer = answer_fan_query("Who in my lineup has the highest upside this phase?", snapshot, language="Hinglish")
    assert "V Kohli" in answer or "Captain" in answer
    assert len(answer.split()) < 45


def test_dugout_ai_field_setup_fallback():
    """Verifies field setup question fallback generates valid tactical advice."""
    snapshot = {
        "delivery_display": "Over 0.3",
        "innings": 1,
        "team_batting": "India",
        "batter": "RG Sharma",
        "bowler": "K Rabada",
        "team_points": 15.0,
        "captain_name": "V Kohli",
        "vc_name": "JJ Bumrah",
        "last_event": "Six (+2 bonus)",
    }
    answer = build_deterministic_dugout_fallback("Explain the current field setup.", snapshot, language="English")
    assert "RG Sharma" in answer or "field" in answer.lower() or "catch" in answer.lower()


def test_simulation_state_progression():
    """Verifies sequential ball accumulation preserves monotonic progress."""
    rules = {
        "batting": {"run": 1, "boundary_bonus": 1, "six_bonus": 2, "duck_penalty": -2},
        "bowling": {"wicket_standard": 25, "lbw_bowled_bonus": 8, "dot_ball": 1, "maiden_over": 12},
        "fielding": {"catch": 8, "stumping": 12, "runout_direct": 12},
    }
    team_map = {"V Kohli": 2.0, "JJ Bumrah": 1.5}

    deliveries = [
        {"delivery_index": 1, "batter": "V Kohli", "bowler": "K Rabada", "runs_batter": 4, "runs_total": 4},
        {"delivery_index": 2, "batter": "V Kohli", "bowler": "K Rabada", "runs_batter": 1, "runs_total": 1},
        {"delivery_index": 3, "batter": "Q de Kock", "bowler": "JJ Bumrah", "runs_batter": 0, "runs_total": 0, "wicket_kind": "bowled", "player_out": "Q de Kock"},
    ]

    total_pts = 0.0
    for d in deliveries:
        deltas = compute_ball_deltas(d, rules, team_map)
        for delta in deltas:
            if delta.get("in_user_team"):
                total_pts += delta["final_points"]

    # Ball 1: 5 * 2 = 10 pts
    # Ball 2: 1 * 2 = 2 pts
    # Ball 3: 33 * 1.5 = 49.5 pts
    # Total = 61.5 pts
    assert total_pts == 61.5
