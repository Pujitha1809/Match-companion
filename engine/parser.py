"""Parser module for Cricsheet JSON format."""

import json
from pathlib import Path
from typing import Union
import pandas as pd


def parse_cricsheet_json(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads a Cricsheet JSON file and flattens innings, overs, and deliveries

    into a sequential pandas DataFrame.

    Parameters
    ----------
    file_path : str or Path
        Path to the Cricsheet JSON match file.

    Returns
    -------
    pd.DataFrame
        Sequential DataFrame containing per-delivery ball-by-ball details.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Match data file not found at: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    delivery_index = 1

    innings_list = data.get("innings", [])
    for inn_idx, innings_obj in enumerate(innings_list, start=1):
        team_batting = innings_obj.get("team", f"Team {inn_idx}")
        overs_list = innings_obj.get("overs", [])

        for over_obj in overs_list:
            over_num = int(over_obj.get("over", 0))  # 0-indexed over
            deliveries = over_obj.get("deliveries", [])

            for ball_idx, delivery in enumerate(deliveries, start=1):
                batter = delivery.get("batter", "")
                bowler = delivery.get("bowler", "")
                non_striker = delivery.get("non_striker", "")

                runs_obj = delivery.get("runs", {})
                runs_batter = int(runs_obj.get("batter", 0))
                runs_extras = int(runs_obj.get("extras", 0))
                runs_total = int(runs_obj.get("total", runs_batter + runs_extras))

                # Extract wicket information if any
                wickets_list = delivery.get("wickets", [])
                wicket_kind = None
                player_out = None
                fielders = []

                if wickets_list:
                    w0 = wickets_list[0]
                    wicket_kind = w0.get("kind")
                    player_out = w0.get("player_out")
                    for fielder_obj in w0.get("fielders", []):
                        if isinstance(fielder_obj, dict):
                            fname = fielder_obj.get("name")
                            if fname:
                                fielders.append(fname)
                        elif isinstance(fielder_obj, str):
                            fielders.append(fielder_obj)

                delivery_display = f"Over {over_num}.{ball_idx}"

                rows.append({
                    "delivery_index": delivery_index,
                    "innings": inn_idx,
                    "team_batting": team_batting,
                    "over": over_num,
                    "over_display": over_num + 1,
                    "ball": ball_idx,
                    "delivery_display": delivery_display,
                    "batter": batter,
                    "bowler": bowler,
                    "non_striker": non_striker,
                    "runs_batter": runs_batter,
                    "runs_extras": runs_extras,
                    "runs_total": runs_total,
                    "wicket_kind": wicket_kind,
                    "player_out": player_out,
                    "fielders": fielders,
                })
                delivery_index += 1

    df = pd.DataFrame(rows)
    return df
