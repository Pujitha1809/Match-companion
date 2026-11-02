"""Unit tests for deterministic fantasy points and what-if calculations."""

import pytest
from engine.points import compute_ball_deltas
from engine.whatif import calculate_captain_whatifs, format_points_change
from engine.parser import parse_cricsheet_json
from pathlib import Path


@pytest.fixture
def sample_rules():
    """Standard fantasy cricket rules fixture matching Dream11 T20 rules."""
    return {
        "batting": {
            "run": 1,
            "boundary_bonus": 1,
            "six_bonus": 2,
            "duck_penalty": -2,
        },
        "bowling": {
            "wicket_standard": 25,
            "lbw_bowled_bonus": 8,
            "dot_ball": 1,
            "maiden_over": 12,
        },
        "fielding": {
            "catch": 8,
            "stumping": 12,
            "runout_direct": 12,
        },
    }


def test_standard_runs_calculation(sample_rules):
    """Test 1: Standard single and double runs give exact 1 pt per run."""
    user_team = {"V Kohli": 1.0}
    delivery_row = {
        "batter": "V Kohli",
        "bowler": "K Rabada",
        "runs_batter": 1,
        "runs_total": 1,
        "wicket_kind": None,
    }

    deltas = compute_ball_deltas(delivery_row, sample_rules, user_team)
    assert len(deltas) == 1
    fact = deltas[0]
    assert fact["player"] == "V Kohli"
    assert fact["category"] == "Batting"
    assert fact["base_points"] == 1.0
    assert fact["multiplier"] == 1.0
    assert fact["final_points"] == 1.0
    assert fact["in_user_team"] is True

    # Test 2 runs
    delivery_two = {
        "batter": "V Kohli",
        "bowler": "K Rabada",
        "runs_batter": 2,
        "runs_total": 2,
        "wicket_kind": None,
    }
    deltas_two = compute_ball_deltas(delivery_two, sample_rules, user_team)
    assert deltas_two[0]["base_points"] == 2.0
    assert deltas_two[0]["final_points"] == 2.0


def test_boundary_four_and_six_bonus_calculation(sample_rules):
    """Test 2: Boundary four bonus (+1 -> 5 pts) and six bonus (+2 -> 8 pts)."""
    user_team = {"RG Sharma": 1.0}

    # Boundary 4: 4 runs + 1 bonus = 5 pts
    four_row = {
        "batter": "RG Sharma",
        "bowler": "K Rabada",
        "runs_batter": 4,
        "runs_total": 4,
        "wicket_kind": None,
    }
    deltas_four = compute_ball_deltas(four_row, sample_rules, user_team)
    assert len(deltas_four) == 1
    fact_four = deltas_four[0]
    assert fact_four["base_points"] == 5.0
    assert fact_four["final_points"] == 5.0
    assert "Boundary" in fact_four["event"] or "Four" in fact_four["event"]

    # Six: 6 runs + 2 bonus = 8 pts
    six_row = {
        "batter": "RG Sharma",
        "bowler": "K Rabada",
        "runs_batter": 6,
        "runs_total": 6,
        "wicket_kind": None,
    }
    deltas_six = compute_ball_deltas(six_row, sample_rules, user_team)
    assert len(deltas_six) == 1
    fact_six = deltas_six[0]
    assert fact_six["base_points"] == 8.0
    assert fact_six["final_points"] == 8.0
    assert "Six" in fact_six["event"]


def test_bowled_wicket_bonus(sample_rules):
    """Test 3: Bowled wicket gives +33 pts (25 wicket standard + 8 bowled bonus)."""
    user_team = {"JJ Bumrah": 1.0}
    delivery_row = {
        "batter": "Q de Kock",
        "bowler": "JJ Bumrah",
        "runs_batter": 0,
        "runs_total": 0,
        "wicket_kind": "bowled",
        "player_out": "Q de Kock",
    }

    deltas = compute_ball_deltas(delivery_row, sample_rules, user_team)
    # Bowler should get 33 points
    bowler_facts = [f for f in deltas if f["player"] == "JJ Bumrah"]
    assert len(bowler_facts) == 1
    fact = bowler_facts[0]
    assert fact["category"] == "Bowling"
    assert fact["base_points"] == 33.0
    assert fact["final_points"] == 33.0
    assert "Bowled" in fact["event"]


def test_captain_multiplier_doubling_points(sample_rules):
    """Test 4: Captain 2.0x multiplier doubles both base batting and bowling points."""
    # Captain batting four: 5 base points * 2.0 = 10 final points
    user_team_bat = {"V Kohli": 2.0}
    bat_row = {
        "batter": "V Kohli",
        "bowler": "K Rabada",
        "runs_batter": 4,
        "runs_total": 4,
        "wicket_kind": None,
    }
    deltas_bat = compute_ball_deltas(bat_row, sample_rules, user_team_bat)
    assert deltas_bat[0]["base_points"] == 5.0
    assert deltas_bat[0]["multiplier"] == 2.0
    assert deltas_bat[0]["final_points"] == 10.0

    # Captain bowler bowled wicket: 33 base points * 2.0 = 66 final points
    user_team_bowl = {"JJ Bumrah": 2.0}
    bowl_row = {
        "batter": "Q de Kock",
        "bowler": "JJ Bumrah",
        "runs_batter": 0,
        "runs_total": 0,
        "wicket_kind": "bowled",
        "player_out": "Q de Kock",
    }
    deltas_bowl = compute_ball_deltas(bowl_row, sample_rules, user_team_bowl)
    bowler_facts = [f for f in deltas_bowl if f["player"] == "JJ Bumrah"]
    assert bowler_facts[0]["base_points"] == 33.0
    assert bowler_facts[0]["multiplier"] == 2.0
    assert bowler_facts[0]["final_points"] == 66.0


def test_duck_penalty_and_captain_multiplier(sample_rules):
    """Test 5: Duck penalty applies -2 points (and -4 for Captain)."""
    user_team = {"SA Yadav": 2.0}
    duck_row = {
        "batter": "SA Yadav",
        "bowler": "K Rabada",
        "runs_batter": 0,
        "runs_total": 0,
        "wicket_kind": "caught",
        "player_out": "SA Yadav",
        "is_duck": True,
    }
    deltas = compute_ball_deltas(duck_row, sample_rules, user_team)
    duck_facts = [f for f in deltas if f["player"] == "SA Yadav" and f["category"] == "Batting"]
    assert len(duck_facts) == 1
    assert duck_facts[0]["base_points"] == -2.0
    assert duck_facts[0]["multiplier"] == 2.0
    assert duck_facts[0]["final_points"] == -4.0


def test_fielding_catches_and_runout(sample_rules):
    """Test 6: Fielding points for catch (+8) and direct run-out (+12)."""
    user_team = {"SA Yadav": 1.0, "RG Sharma": 1.5}

    # Catch by SA Yadav
    catch_row = {
        "batter": "DA Miller",
        "bowler": "HH Pandya",
        "runs_batter": 0,
        "runs_total": 0,
        "wicket_kind": "caught",
        "player_out": "DA Miller",
        "fielders": ["SA Yadav"],
    }
    deltas_catch = compute_ball_deltas(catch_row, sample_rules, user_team)
    surya_facts = [f for f in deltas_catch if f["player"] == "SA Yadav" and f["category"] == "Fielding"]
    assert len(surya_facts) == 1
    assert surya_facts[0]["base_points"] == 8.0
    assert surya_facts[0]["final_points"] == 8.0

    # Direct run-out by Vice-Captain Rohit Sharma (1.5x)
    runout_row = {
        "batter": "K Rabada",
        "bowler": "JJ Bumrah",
        "runs_batter": 0,
        "runs_total": 0,
        "wicket_kind": "run out",
        "player_out": "K Rabada",
        "fielders": ["RG Sharma"],
    }
    deltas_ro = compute_ball_deltas(runout_row, sample_rules, user_team)
    rohit_facts = [f for f in deltas_ro if f["player"] == "RG Sharma" and f["category"] == "Fielding"]
    assert len(rohit_facts) == 1
    assert rohit_facts[0]["base_points"] == 12.0
    assert rohit_facts[0]["multiplier"] == 1.5
    assert rohit_facts[0]["final_points"] == 18.0


def test_whatif_captain_differential_logic():
    """Test 7: What-if captain differential calculation logic."""
    player_base_points = {
        "V Kohli": 15.0,        # Current Captain
        "JJ Bumrah": 33.0,      # If Bumrah was Captain: +18 pts
        "RG Sharma": 7.0,       # If Rohit was Captain: -8 pts
        "Arshdeep Singh": 25.0, # If Arshdeep was Captain: +10 pts
    }
    current_captain = "V Kohli"

    whatifs = calculate_captain_whatifs(player_base_points, current_captain)

    # Captain should not be in what-ifs list
    players = [w["player"] for w in whatifs]
    assert "V Kohli" not in players
    assert len(whatifs) == 3

    # Best alternate captain should be first (sorted descending)
    assert whatifs[0]["player"] == "JJ Bumrah"
    assert whatifs[0]["net_difference"] == 18.0
    assert whatifs[0]["alternate_total_change"] == "+18 pts"

    # Rohit difference is 7 - 15 = -8
    rohit_whatif = next(w for w in whatifs if w["player"] == "RG Sharma")
    assert rohit_whatif["net_difference"] == -8.0
    assert rohit_whatif["alternate_total_change"] == "-8 pts"

    # Format check for 0 delta
    assert format_points_change(0.0) == "0 pts"


def test_parser_cricsheet_json():
    """Test 8: Parser accurately loads match.json into 42 deliveries."""
    match_file = Path(__file__).resolve().parent.parent / "data" / "match.json"
    df = parse_cricsheet_json(match_file)
    assert len(df) == 42
    assert "delivery_index" in df.columns
    assert "batter" in df.columns
    assert "bowler" in df.columns
    assert "runs_batter" in df.columns
    assert "wicket_kind" in df.columns
