"""Deterministic Captain What-If calculation engine."""

from typing import Any, Dict, List


def format_points_change(delta: float) -> str:
    """Formats point difference as '+18 pts', '-8 pts', or '0 pts'."""
    val = round(delta, 2)
    display_val = int(val) if val.is_integer() else val
    if val > 0:
        return f"+{display_val} pts"
    elif val < 0:
        return f"{display_val} pts"
    return "0 pts"


def calculate_captain_whatifs(
    player_base_points: Dict[str, float],
    current_captain: str
) -> List[Dict[str, Any]]:
    """Computes the net team points impact if an alternate player had been chosen as captain (2.0x).

    Formula
    -------
    net_difference = player_base_points[player] - player_base_points[current_captain]

    Parameters
    ----------
    player_base_points : dict
        Mapping of player_name -> base fantasy points earned so far.
    current_captain : str
        Name of the current team captain.

    Returns
    -------
    list of dict
        Sorted list (descending by net_difference) with:
        [
            {
                "player": str,
                "net_difference": float,
                "alternate_total_change": str  # e.g., "+18 pts", "-8 pts"
            },
            ...
        ]
    """
    captain_base = float(player_base_points.get(current_captain, 0.0))
    results: List[Dict[str, Any]] = []

    for player, base_pts in player_base_points.items():
        if player == current_captain:
            continue

        net_diff = float(base_pts) - captain_base
        results.append({
            "player": player,
            "net_difference": round(net_diff, 2),
            "alternate_total_change": format_points_change(net_diff)
        })

    # Sort descending by net_difference so best alternative captain picks appear first
    results.sort(key=lambda x: x["net_difference"], reverse=True)
    return results
