"""AI narrator with pre-generated offline caching and seamless deterministic fallback.

Design Principle:
- Deterministic points engine always calculates points.
- LLM or Cache only narrates explanations.
- Never recalculates numbers. Never crashes.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.prompts import (
    POINT_EXPLAINER_SYSTEM_PROMPT,
    CATCH_UP_SYSTEM_PROMPT,
    build_point_event_prompt,
    build_catch_up_prompt,
)

# Optional Gemini client initialization
_genai_available = False
try:
    import google.generativeai as genai
    _genai_available = True
except ImportError:
    _genai_available = False


def _get_cache_path() -> Path:
    """Returns absolute path to cache/explanations.json."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "cache" / "explanations.json"


_IN_MEMORY_CACHE: Optional[Dict[str, Any]] = None


def _load_cache() -> Dict[str, Any]:
    """Loads pre-generated offline explanations cache from disk."""
    global _IN_MEMORY_CACHE
    if _IN_MEMORY_CACHE is not None:
        return _IN_MEMORY_CACHE

    cache_file = _get_cache_path()
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                _IN_MEMORY_CACHE = json.load(f)
                return _IN_MEMORY_CACHE
        except Exception:
            pass

    _IN_MEMORY_CACHE = {"events": {}, "catchup": {}}
    return _IN_MEMORY_CACHE


def _get_api_key() -> Optional[str]:
    """Retrieves GEMINI_API_KEY from os.getenv or Streamlit secrets."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key and key.strip():
        return key.strip()

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GEMINI_API_KEY" in st.secrets:
                val = str(st.secrets["GEMINI_API_KEY"]).strip()
                if val:
                    return val
            if "GOOGLE_API_KEY" in st.secrets:
                val = str(st.secrets["GOOGLE_API_KEY"]).strip()
                if val:
                    return val
    except Exception:
        pass

    return None


def _format_num(val: float) -> str:
    """Formats float as integer if whole number."""
    fval = float(val)
    return str(int(fval)) if fval.is_integer() else f"{fval:.1f}"


def build_deterministic_event_template(fact: Dict[str, Any], language: str = "English") -> str:
    """Builds a high-quality deterministic explanation string without LLM."""
    player = fact.get("player", "Player")
    event = fact.get("event", "Event")
    base_pts = _format_num(fact.get("base_points", 0))
    final_pts = _format_num(fact.get("final_points", 0))
    mult = fact.get("multiplier", 1.0)
    in_team = fact.get("in_user_team", False)

    is_hinglish = language.lower() == "hinglish"

    if in_team:
        if mult == 2.0:
            if is_hinglish:
                return f"{player} ne {event} kiya — Captain 2.0x boost ke sath total +{final_pts} pts mile!"
            return f"{player} ({event}) delivered +{final_pts} pts, doubled with your 2.0x Captain boost!"
        elif mult == 1.5:
            if is_hinglish:
                return f"{player} ne {event} kiya — Vice-Captain 1.5x multiplier se +{final_pts} pts team ko mile!"
            return f"{player} ({event}) brought +{final_pts} pts, boosted by your 1.5x Vice-Captain multiplier."
        else:
            if is_hinglish:
                return f"{player} ne {event} kiya aur aapki team ke account mein +{final_pts} pts jud gaye."
            return f"{player} earned +{final_pts} pts for your team with {event}."
    else:
        if is_hinglish:
            return f"{player} ne {event} kiya (+{base_pts} pts), par yeh player aapki fantasy XI mein nahi hai."
        return f"{player} delivered {event} (+{base_pts} base pts), but isn't in your active XI."


def build_deterministic_catchup_template(
    recent_facts: List[Dict[str, Any]],
    match_status: str,
    language: str = "English"
) -> str:
    """Builds a structured 3-4 bullet recap deterministically."""
    is_hinglish = language.lower() == "hinglish"

    # Filter fantasy team events
    team_facts = [f for f in recent_facts if f.get("in_user_team", False)]
    wickets = [f for f in recent_facts if "wicket" in str(f.get("event", "")).lower() or f.get("category") == "Bowling"]
    boundaries = [f for f in recent_facts if "four" in str(f.get("event", "")).lower() or "six" in str(f.get("event", "")).lower()]

    bullets = []

    # Bullet 1: Match Status
    if is_hinglish:
        bullets.append(f"🏏 Match Status: {match_status}.")
    else:
        bullets.append(f"🏏 Match Phase: {match_status}.")

    # Bullet 2: Top fantasy earner
    if team_facts:
        top_fact = max(team_facts, key=lambda x: x.get("final_points", 0))
        pts_str = _format_num(top_fact.get("final_points", 0))
        player = top_fact.get("player")
        event = top_fact.get("event")
        if is_hinglish:
            bullets.append(f"🌟 Fantasy Star: {player} ne {event} se aapko +{pts_str} pts dilaye!")
        else:
            bullets.append(f"🌟 Fantasy Impact: {player} led your tally with +{pts_str} pts via {event}.")
    else:
        if is_hinglish:
            bullets.append("🛡️ Fantasy Watch: Pichle overs mein opponent players active rahe, aapki XI control mein hai.")
        else:
            bullets.append("🛡️ Fantasy Watch: Opponents dominated recent deliveries; your team remains steady.")

    # Bullet 3: Big moments (Wickets or Boundaries)
    if wickets:
        w = wickets[-1]
        w_player = w.get("player")
        w_event = w.get("event")
        if is_hinglish:
            bullets.append(f"⚡ Wicket Fall: {w_player} ne wicket nikala ({w_event}). Game badal raha hai!")
        else:
            bullets.append(f"⚡ Breakthrough: {w_player} struck with a crucial wicket ({w_event}).")
    elif boundaries:
        b = boundaries[-1]
        b_player = b.get("player")
        b_event = b.get("event")
        if is_hinglish:
            bullets.append(f"💥 Boundary Alert: {b_player} ne boundary lagayi ({b_event})!")
        else:
            bullets.append(f"💥 Big Hit: {b_player} punished the bowling with {b_event}.")
    else:
        if is_hinglish:
            bullets.append("🎯 Strike Rotation: Singles aur dot balls se match ka tempo build ho raha hai.")
        else:
            bullets.append("🎯 Game Tempo: Batters and bowlers are engaged in tactical strike rotation.")

    # Bullet 4: Summary takeaway
    total_pts_earned = sum(f.get("final_points", 0) for f in team_facts)
    total_str = _format_num(total_pts_earned)
    if is_hinglish:
        bullets.append(f"📊 Fantasy Scoreboard: In deliveries mein aapki team ne total +{total_str} pts earn kiye.")
    else:
        bullets.append(f"📊 Total Yield: Your squad collected +{total_str} fantasy points during this window.")

    return "\n\n".join([f"• {b}" for b in bullets])


def narrate_point_event(fact: Dict[str, Any], language: str = "English") -> str:
    """Narrates a single point event with pre-generated cache, Gemini API, or fallback.

    Order of priority:
    1. Pre-generated Cache (0ms latency, works offline)
    2. Live Gemini API (if API key present)
    3. Deterministic template fallback (guarantees 100% uptime)
    """
    lang_lower = language.strip().lower()

    # 1. Check offline cache
    cache = _load_cache()
    events_cache = cache.get("events", {})
    d_idx = fact.get("delivery_index", "")
    p_name = fact.get("player", "")
    event_name = fact.get("event", "")
    cache_key = f"{d_idx}_{p_name}_{event_name}_{lang_lower}"

    if cache_key in events_cache:
        return events_cache[cache_key]

    # 2. Try Gemini API if key is present
    api_key = _get_api_key()
    if _genai_available and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=POINT_EXPLAINER_SYSTEM_PROMPT
            )
            prompt = build_point_event_prompt(fact, language)
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 50, "temperature": 0.2}
            )
            if response and response.text:
                text = response.text.strip().replace("\n", " ")
                if len(text) > 5:
                    events_cache[cache_key] = text
                    return text
        except Exception:
            pass

    # 3. Deterministic template fallback
    return build_deterministic_event_template(fact, language)


def narrate_catch_up(
    recent_facts: List[Dict[str, Any]],
    match_status: str,
    language: str = "English"
) -> str:
    """Narrates match recap using Cache, Gemini, or deterministic fallback.

    Never recalculates numbers. Never crashes.
    """
    lang_lower = language.strip().lower()

    # 1. Check offline cache for matching delivery milestone
    cache = _load_cache()
    catchup_cache = cache.get("catchup", {})
    latest_idx = recent_facts[-1].get("delivery_index", 0) if recent_facts else 0

    # Look for exact or nearest milestone in cache
    exact_key = f"catchup_{latest_idx}_{lang_lower}"
    if exact_key in catchup_cache:
        return catchup_cache[exact_key]

    # Find nearest available milestone in cache
    milestone_keys = [
        int(k.split("_")[1]) for k in catchup_cache.keys()
        if k.startswith("catchup_") and k.endswith(f"_{lang_lower}") and k.split("_")[1].isdigit()
    ]
    if milestone_keys:
        candidates = [m for m in milestone_keys if m <= latest_idx]
        nearest = max(candidates) if candidates else min(milestone_keys)
        nearest_key = f"catchup_{nearest}_{lang_lower}"
        if nearest_key in catchup_cache:
            return catchup_cache[nearest_key]

    # 2. Try Gemini API if available
    api_key = _get_api_key()
    if _genai_available and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=CATCH_UP_SYSTEM_PROMPT
            )
            prompt = build_catch_up_prompt(recent_facts, match_status, language)
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 150, "temperature": 0.2}
            )
            if response and response.text:
                text = response.text.strip()
                if "•" in text or "-" in text:
                    return text
        except Exception:
            pass

    # 3. Deterministic template fallback
    return build_deterministic_catchup_template(recent_facts, match_status, language)
