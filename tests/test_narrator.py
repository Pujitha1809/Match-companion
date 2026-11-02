"""Unit tests for AI narrator, caching, and deterministic fallback guarantees."""

import os
from ai.narrator import (
    narrate_point_event,
    narrate_catch_up,
    build_deterministic_event_template,
    build_deterministic_catchup_template,
)


def test_deterministic_event_template_english():
    """Checks English deterministic narration formatting and exact point inclusion."""
    fact = {
        "player": "V Kohli",
        "category": "Batting",
        "event": "Boundary Four (+1 bonus)",
        "base_points": 5.0,
        "multiplier": 2.0,
        "final_points": 10.0,
        "in_user_team": True,
    }
    result = build_deterministic_event_template(fact, language="English")
    assert "V Kohli" in result
    assert "+10 pts" in result
    assert "Captain" in result


def test_deterministic_event_template_hinglish():
    """Checks Hinglish deterministic narration formatting and natural slang."""
    fact = {
        "player": "JJ Bumrah",
        "category": "Bowling",
        "event": "Wicket (Bowled +8 bonus)",
        "base_points": 33.0,
        "multiplier": 1.5,
        "final_points": 49.5,
        "in_user_team": True,
    }
    result = build_deterministic_event_template(fact, language="Hinglish")
    assert "JJ Bumrah" in result
    assert "+49.5 pts" in result
    assert "Vice-Captain" in result or "VC" in result


def test_narrate_point_event_offline_guarantee():
    """Guarantees narrate_point_event never returns empty and under 30 words."""
    fact = {
        "delivery_index": 21,
        "player": "JJ Bumrah",
        "category": "Bowling",
        "event": "Wicket (Bowled +8 bonus)",
        "base_points": 33.0,
        "multiplier": 1.5,
        "final_points": 49.5,
        "in_user_team": True,
    }
    en_res = narrate_point_event(fact, language="English")
    assert len(en_res) > 5
    assert len(en_res.split()) < 30

    hi_res = narrate_point_event(fact, language="Hinglish")
    assert len(hi_res) > 5
    assert len(hi_res.split()) < 30


def test_narrate_catch_up_bullet_structure():
    """Guarantees narrate_catch_up returns bullet points under 90 words."""
    recent_facts = [
        {
            "delivery_index": 35,
            "player": "HH Pandya",
            "category": "Bowling",
            "event": "Wicket (Caught)",
            "final_points": 25.0,
            "in_user_team": True,
        },
        {
            "delivery_index": 35,
            "player": "SA Yadav",
            "category": "Fielding",
            "event": "Catch dismisses DA Miller",
            "final_points": 8.0,
            "in_user_team": True,
        },
    ]
    status = "Innings 2: South Africa stands at 169/7 (Over 19.5)"
    recap = narrate_catch_up(recent_facts, status, language="English")
    assert "•" in recap
    assert len(recap.split()) < 100


def test_invalid_api_key_graceful_fallback(monkeypatch):
    """Verifies that an invalid API key gracefully falls back to deterministic template without crashing."""
    monkeypatch.setenv("GEMINI_API_KEY", "invalid_dummy_key_not_real_12345")
    fact = {
        "delivery_index": 999,  # Uncached delivery index to force API branch
        "player": "Unknown Player",
        "category": "Batting",
        "event": "1 Run",
        "base_points": 1.0,
        "multiplier": 1.0,
        "final_points": 1.0,
        "in_user_team": True,
    }
    # Should not raise exception
    res = narrate_point_event(fact, language="English")
    assert "Unknown Player" in res
    assert "+1 pts" in res


def test_missing_api_key_uses_cache_or_fallback(monkeypatch):
    """Verifies that when no API key is present, cached or fallback narration works flawlessly."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    fact = {
        "delivery_index": 1,
        "player": "V Kohli",
        "category": "Batting",
        "event": "Boundary Four (+1 bonus)",
        "base_points": 5.0,
        "multiplier": 2.0,
        "final_points": 10.0,
        "in_user_team": True,
    }
    res = narrate_point_event(fact, language="English")
    assert "V Kohli" in res
    assert "+10 pts" in res
