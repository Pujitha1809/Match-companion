"""Script to pre-generate offline cache for all match deliveries in English and Hinglish."""

import json
from pathlib import Path
import yaml
from engine.parser import parse_cricsheet_json
from engine.points import compute_ball_deltas


def build_curated_narration(fact: dict, language: str) -> str:
    """Generates punchy cricket expert narration for an event."""
    player = fact.get("player", "Player")
    event = fact.get("event", "Event")
    base_pts = fact.get("base_points", 0)
    final_pts = fact.get("final_points", 0)
    mult = fact.get("multiplier", 1.0)
    in_team = fact.get("in_user_team", False)
    cat = fact.get("category", "")

    pts_str = str(int(final_pts)) if float(final_pts).is_integer() else f"{final_pts:.1f}"
    base_str = str(int(base_pts)) if float(base_pts).is_integer() else f"{base_pts:.1f}"
    is_hinglish = language.lower() == "hinglish"

    # Batting
    if cat == "Batting":
        if "Six" in event:
            if in_team:
                if mult == 2.0:
                    return f"{player} ne shaandar chhakka maara — Captain 2.0x boost se +{pts_str} pts team ko mile!" if is_hinglish else f"{player} launched a massive six, netting +{pts_str} pts boosted by your 2.0x Captain armband!"
                return f"{player} ne boundary ke paar chhakka lagaya, team ko mile solid +{pts_str} pts!" if is_hinglish else f"{player} cleared the ropes with a monster six for +{pts_str} fantasy points!"
            return f"{player} ne chhakka lagaya (+{base_str} pts), par yeh aapki XI mein nahi hai." if is_hinglish else f"{player} smoked a six (+{base_str} base pts), though not in your active XI."
        elif "Four" in event or "Boundary" in event:
            if in_team:
                if mult == 2.0:
                    return f"Captain {player} ka khoobsurat chauka! 2.0x multiplier ke saath +{pts_str} pts mile." if is_hinglish else f"Captain {player} threads the gap for four, securing +{pts_str} pts with your 2.0x boost!"
                elif mult == 1.5:
                    return f"Vice-Captain {player} ne karara chauka jad diya — 1.5x VC multiplier se +{pts_str} pts!" if is_hinglish else f"Vice-Captain {player} smashes a crisp boundary, earning +{pts_str} pts with your 1.5x boost!"
                return f"{player} ne timing ke saath chauka lagaya, +{pts_str} fantasy points mile!" if is_hinglish else f"{player} finds the boundary with pristine timing, adding +{pts_str} fantasy points."
            return f"{player} ne chauka maara (+{base_str} pts), lekin aapki fantasy team mein nahi hai." if is_hinglish else f"{player} struck a boundary (+{base_str} base pts) outside your fantasy XI."
        else:
            if in_team:
                if mult == 2.0:
                    return f"Captain {player} ne strike rotate karte hue +{pts_str} pts (2.0x) jod liye." if is_hinglish else f"Captain {player} rotates the strike, banking +{pts_str} pts with the 2.0x multiplier."
                return f"{player} ne running between wickets se +{pts_str} pts score kiye." if is_hinglish else f"{player} turns the strike over, chipping in +{pts_str} pts."
            return f"{player} ne single liya (+{base_str} base pts)." if is_hinglish else f"{player} picked up a single (+{base_str} base pts)."

    # Bowling
    elif cat == "Bowling":
        if "Wicket" in event:
            if in_team:
                if mult == 1.5:
                    return f"⚡ VC {player} ka deadly wicket (+8 bowled bonus)! 1.5x boost ke sath mile +{pts_str} pts!" if is_hinglish else f"⚡ VC {player} rattles the stumps (+8 bowled bonus)! Rewarding your team with +{pts_str} pts!"
                elif mult == 2.0:
                    return f"👑 Captain {player} ne match-turning wicket chatkaya! 2.0x Captain boost se +{pts_str} pts!" if is_hinglish else f"👑 Captain {player} strikes with a breakthrough wicket! Doubled to +{pts_str} pts!"
                return f"🎯 {player} ne game-changing wicket nikala, team ke account mein +{pts_str} pts!" if is_hinglish else f"🎯 {player} delivers a crucial breakthrough, gifting your fantasy XI +{pts_str} pts!"
            return f"{player} ne wicket chatkaya (+{base_str} pts), par yeh bowler aapki team mein nahi hai." if is_hinglish else f"{player} claimed a wicket (+{base_str} base pts) for the opposition."
        elif "Dot" in event:
            if in_team:
                mult_tag = " (1.5x VC)" if mult == 1.5 else (" (2.0x C)" if mult == 2.0 else "")
                return f"{player} ne tight dot ball fenki{mult_tag}, +{pts_str} point earn kiya." if is_hinglish else f"{player} beats the bat with a tight dot ball{mult_tag}, gaining +{pts_str} point."
            return f"{player} ne dot ball daali (+{base_str} base pt)." if is_hinglish else f"{player} bowled a dot ball (+{base_str} base pt)."

    # Fielding
    elif cat == "Fielding":
        if "Catch" in event:
            if in_team:
                return f"🧤 {player} ne shaandar boundary catch pakda! Fielding bonus ke sath +{pts_str} pts!" if is_hinglish else f"🧤 {player} holds onto a stunning catch under pressure! +{pts_str} fielding points awarded!"
            return f"{player} ne catch liya (+{base_str} pts)." if is_hinglish else f"{player} completed a regulation catch (+{base_str} base pts)."

    # Fallback
    if is_hinglish:
        return f"{player} ne {event} kiya aur team ko +{pts_str} pts mile."
    return f"{player} delivered {event}, securing +{pts_str} fantasy points for your squad."


def main():
    root_dir = Path(__file__).resolve().parent
    config_path = root_dir / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    rules = config.get("rules", {})
    user_players = config.get("team", {}).get("user_players", [])
    user_team = {p["name"]: float(p.get("multiplier", 1.0)) for p in user_players}

    match_path = root_dir / "data" / "match.json"
    df = parse_cricsheet_json(match_path)

    events_cache = {}
    catchup_cache = {}

    match_state = {}
    all_facts = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        deltas = compute_ball_deltas(row_dict, rules, user_team, match_state)
        for d in deltas:
            d["delivery_index"] = row_dict["delivery_index"]
            d["delivery_display"] = row_dict["delivery_display"]
            all_facts.append(d)

            # Generate English and Hinglish explanations
            d_idx = d["delivery_index"]
            p_name = d["player"]
            event_name = d["event"]

            key_en = f"{d_idx}_{p_name}_{event_name}_english"
            key_hi = f"{d_idx}_{p_name}_{event_name}_hinglish"

            events_cache[key_en] = build_curated_narration(d, "English")
            events_cache[key_hi] = build_curated_narration(d, "Hinglish")

    # Generate catchup recaps for key milestones
    milestones = [6, 12, 18, 24, 30, len(df)]
    for m in milestones:
        sub_facts = [f for f in all_facts if f["delivery_index"] <= m]
        recent = sub_facts[-8:] if sub_facts else []
        row_m = df.iloc[m - 1]
        inn = row_m["innings"]
        team_bat = row_m["team_batting"]
        d_disp = row_m["delivery_display"]

        status = f"Innings {inn}: {team_bat} ({d_disp})"

        # English Recap
        en_lines = [
            f"• 🏏 Match Phase: {status} in the ICC T20 World Cup Final.",
            f"• 🌟 Fantasy Impact: Your squad has accumulated strong points led by active Captain & VC performances.",
            f"• ⚡ Momentum Shift: Intense ball-by-ball contest with crucial boundary pressure and breakthroughs.",
            f"• 📊 Squad Yield: Excellent fantasy foundation built across batting and death bowling phases."
        ]
        catchup_cache[f"catchup_{m}_english"] = "\n\n".join(en_lines)

        # Hinglish Recap
        hi_lines = [
            f"• 🏏 Match Status: {status} — World Cup Final ka high-voltage game chal raha hai!",
            f"• 🌟 Fantasy Impact: Aapke Captain aur Vice-Captain ne regular points deliver karke team ko aage rakha hai.",
            f"• ⚡ Big Moments: Chhakke, chauke aur clean bowled wickets se match ka balance palat raha hai.",
            f"• 📊 Squad Standings: Aapki Fantasy XI top rhythm mein hai aur points lagatar badh rahe hain!"
        ]
        catchup_cache[f"catchup_{m}_hinglish"] = "\n\n".join(hi_lines)

    cache_dir = root_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "explanations.json"

    payload = {
        "events": events_cache,
        "catchup": catchup_cache
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Generated cache with {len(events_cache)} event narrations and {len(catchup_cache)} catchups!")


if __name__ == "__main__":
    main()

