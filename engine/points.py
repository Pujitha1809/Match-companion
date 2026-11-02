"""Deterministic fantasy points calculation engine."""

from typing import Any, Dict, List, Optional


def compute_ball_deltas(
    row: Dict[str, Any],
    rules: Dict[str, Any],
    user_team: Dict[str, float],
    match_state: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Computes fantasy point deltas for all players involved in a single delivery.

    Parameters
    ----------
    row : dict
        Dictionary of delivery fields (batter, bowler, runs_batter, wicket_kind, etc.)
    rules : dict
        Fantasy scoring rules dictionary.
    user_team : dict
        Dictionary mapping player_name -> multiplier for the user's team.
    match_state : dict, optional
        Persistent cumulative match tracking state (batter_runs, over_runs, etc.)

    Returns
    -------
    list of dict
        Structured fact dictionaries:
        {
            "player": str,
            "category": str,
            "event": str,
            "base_points": float,
            "multiplier": float,
            "final_points": float,
            "in_user_team": bool
        }
    """
    facts: List[Dict[str, Any]] = []

    batting_rules = rules.get("batting", {})
    bowling_rules = rules.get("bowling", {})
    fielding_rules = rules.get("fielding", {})

    batter = row.get("batter", "")
    bowler = row.get("bowler", "")
    runs_batter = int(row.get("runs_batter", 0))
    runs_total = int(row.get("runs_total", runs_batter))
    wicket_kind = row.get("wicket_kind")
    player_out = row.get("player_out")
    fielders = row.get("fielders", [])
    innings = row.get("innings", 1)
    over_num = row.get("over", 0)
    ball_idx = row.get("ball", 1)

    # Sanitize pandas NaN values
    if wicket_kind is not None and (str(wicket_kind).strip().lower() in ["none", "nan", ""] or (isinstance(wicket_kind, float))):
        wicket_kind = None
    if player_out is not None and (str(player_out).strip().lower() in ["none", "nan", ""] or (isinstance(player_out, float))):
        player_out = None

    # Initialize or update match state tracking
    if match_state is not None:
        if "batter_runs" not in match_state:
            match_state["batter_runs"] = {}
        if "over_runs" not in match_state:
            match_state["over_runs"] = {}

        # Track batter cumulative runs
        if batter:
            match_state["batter_runs"][batter] = match_state["batter_runs"].get(batter, 0) + runs_batter

        # Track over runs
        over_key = (innings, over_num)
        match_state["over_runs"][over_key] = match_state["over_runs"].get(over_key, 0) + runs_total

    # 1. BATTING POINTS
    if runs_batter > 0:
        run_pts = batting_rules.get("run", 1)
        base_pts = float(runs_batter * run_pts)
        event_desc = f"{runs_batter} Run{'s' if runs_batter > 1 else ''}"

        if runs_batter == 4:
            boundary_bonus = float(batting_rules.get("boundary_bonus", 1))
            base_pts += boundary_bonus
            event_desc = "Boundary Four (+1 bonus)"
        elif runs_batter == 6:
            six_bonus = float(batting_rules.get("six_bonus", 2))
            base_pts += six_bonus
            event_desc = "Six (+2 bonus)"

        in_team = batter in user_team
        mult = float(user_team.get(batter, 1.0)) if in_team else 1.0
        final_pts = float(round(base_pts * mult, 2)) if in_team else 0.0

        facts.append({
            "player": batter,
            "category": "Batting",
            "event": event_desc,
            "base_points": base_pts,
            "multiplier": mult,
            "final_points": final_pts,
            "in_user_team": in_team
        })

    # 2. DUCK PENALTY
    if wicket_kind and player_out:
        is_duck = False
        if row.get("is_duck") is True:
            is_duck = True
        elif match_state is not None:
            # Batter had 0 total runs when dismissed
            is_duck = (match_state["batter_runs"].get(player_out, 0) == 0)

        if is_duck:
            duck_penalty = float(batting_rules.get("duck_penalty", -2))
            if duck_penalty != 0:
                in_team = player_out in user_team
                mult = float(user_team.get(player_out, 1.0)) if in_team else 1.0
                final_pts = float(round(duck_penalty * mult, 2)) if in_team else 0.0
                facts.append({
                    "player": player_out,
                    "category": "Batting",
                    "event": "Dismissed for Duck (-2 pts penalty)",
                    "base_points": duck_penalty,
                    "multiplier": mult,
                    "final_points": final_pts,
                    "in_user_team": in_team
                })

    # 3. BOWLING POINTS
    if wicket_kind:
        w_kind_lower = str(wicket_kind).strip().lower()
        # Non-run-out wickets are credited to the bowler
        if w_kind_lower != "run out":
            wicket_base = float(bowling_rules.get("wicket_standard", 25))
            bonus = 0.0
            event_desc = f"Wicket ({wicket_kind.title()})"

            if w_kind_lower in ["bowled", "lbw"]:
                bonus = float(bowling_rules.get("lbw_bowled_bonus", 8))
                wicket_base += bonus
                event_desc = f"Wicket ({wicket_kind.title()} +8 bonus)"

            in_team = bowler in user_team
            mult = float(user_team.get(bowler, 1.0)) if in_team else 1.0
            final_pts = float(round(wicket_base * mult, 2)) if in_team else 0.0

            facts.append({
                "player": bowler,
                "category": "Bowling",
                "event": event_desc,
                "base_points": wicket_base,
                "multiplier": mult,
                "final_points": final_pts,
                "in_user_team": in_team
            })
    else:
        # Check for dot ball points if applicable and no runs conceded on delivery
        dot_ball_pts = float(bowling_rules.get("dot_ball", 0))
        if dot_ball_pts > 0 and runs_total == 0:
            in_team = bowler in user_team
            mult = float(user_team.get(bowler, 1.0)) if in_team else 1.0
            final_pts = float(round(dot_ball_pts * mult, 2)) if in_team else 0.0
            facts.append({
                "player": bowler,
                "category": "Bowling",
                "event": "Dot Ball",
                "base_points": dot_ball_pts,
                "multiplier": mult,
                "final_points": final_pts,
                "in_user_team": in_team
            })

    # 4. MAIDEN OVER BONUS
    maiden_rule_pts = float(bowling_rules.get("maiden_over", 12))
    if maiden_rule_pts > 0:
        is_maiden = False
        if row.get("is_maiden") is True:
            is_maiden = True
        elif match_state is not None and ball_idx == 6:
            over_key = (innings, over_num)
            if match_state["over_runs"].get(over_key, 0) == 0:
                is_maiden = True

        if is_maiden:
            in_team = bowler in user_team
            mult = float(user_team.get(bowler, 1.0)) if in_team else 1.0
            final_pts = float(round(maiden_rule_pts * mult, 2)) if in_team else 0.0
            facts.append({
                "player": bowler,
                "category": "Bowling",
                "event": "Maiden Over (+12 bonus)",
                "base_points": maiden_rule_pts,
                "multiplier": mult,
                "final_points": final_pts,
                "in_user_team": in_team
            })

    # 5. FIELDING POINTS
    if wicket_kind and fielders:
        w_kind_lower = str(wicket_kind).strip().lower()
        for fielder in fielders:
            fielder_name = str(fielder).strip()
            if not fielder_name:
                continue

            fielding_pts = 0.0
            event_desc = ""

            if w_kind_lower == "caught":
                fielding_pts = float(fielding_rules.get("catch", 8))
                event_desc = f"Catch dismisses {player_out or 'batter'}"
            elif w_kind_lower == "stumped":
                fielding_pts = float(fielding_rules.get("stumping", 12))
                event_desc = f"Stumping dismisses {player_out or 'batter'}"
            elif w_kind_lower == "run out":
                fielding_pts = float(fielding_rules.get("runout_direct", 12))
                event_desc = f"Run Out dismisses {player_out or 'batter'}"

            if fielding_pts > 0:
                in_team = fielder_name in user_team
                mult = float(user_team.get(fielder_name, 1.0)) if in_team else 1.0
                final_pts = float(round(fielding_pts * mult, 2)) if in_team else 0.0

                facts.append({
                    "player": fielder_name,
                    "category": "Fielding",
                    "event": event_desc,
                    "base_points": fielding_pts,
                    "multiplier": mult,
                    "final_points": final_pts,
                    "in_user_team": in_team
                })

    return facts
