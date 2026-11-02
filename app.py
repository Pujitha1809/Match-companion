"""🏏 Match Companion — Dream11 Live AI Assistant

Production-ready Streamlit application.
Deterministic calculation engine with real-time live simulation, AI Dugout Q&A, and interactive what-if customization.
"""

from pathlib import Path
import re
import time
from typing import Any, Dict, List
import yaml
import pandas as pd
import streamlit as st

from engine.parser import parse_cricsheet_json
from engine.points import compute_ball_deltas
from engine.whatif import calculate_captain_whatifs
from ai.narrator import narrate_point_event, narrate_catch_up, answer_fan_query

# Set page configuration
st.set_page_config(
    page_title="🏏 Match Companion — Dream11 Live AI Assistant",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dream11-inspired aesthetics & responsive design
st.markdown("""
<style>
    :root {
        --d11-red: #E11D48;
        --d11-dark-red: #BE123C;
        --card-bg: rgba(255, 255, 255, 0.05);
        --border-color: rgba(255, 255, 255, 0.1);
    }
    
    .main-title {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 800;
        font-size: 2.1rem;
        background: linear-gradient(90deg, #FF4D4D 0%, #F59E0B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    
    .subtitle {
        color: #94A3B8;
        font-size: 0.92rem;
        margin-bottom: 1.0rem;
    }

    .live-simulation-banner {
        background: linear-gradient(90deg, rgba(225, 29, 72, 0.25) 0%, rgba(30, 41, 59, 0.7) 100%);
        border: 1px solid rgba(225, 29, 72, 0.4);
        border-radius: 8px;
        padding: 8px 16px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
    }

    @keyframes pulse-red {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(1.15); }
        100% { opacity: 1; transform: scale(1); }
    }

    .live-pulse-dot {
        display: inline-block;
        color: #EF4444;
        animation: pulse-red 1.2s infinite;
        margin-right: 6px;
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 77, 77, 0.3);
    }
    
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #F8FAFC;
    }
    .metric-lbl {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
    }
    
    .event-card {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .badge-points {
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 20px;
        display: inline-block;
        white-space: nowrap;
    }
    
    .badge-cap {
        background: #F59E0B;
        color: black;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 12px;
        margin-left: 6px;
    }
    
    .badge-vc {
        background: #3B82F6;
        color: white;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 12px;
        margin-left: 6px;
    }
    
    .badge-neutral {
        background: rgba(148, 163, 184, 0.2);
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.75rem;
        padding: 3px 8px;
        border-radius: 12px;
    }
    
    .catch-up-box {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 12px;
        padding: 20px;
        line-height: 1.7;
        font-size: 1.02rem;
    }

    .dugout-chat-bubble {
        background: rgba(30, 41, 59, 0.7);
        border-left: 4px solid #3B82F6;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 12px;
        line-height: 1.6;
    }

    .footer-text {
        text-align: center;
        color: #64748B;
        font-size: 0.8rem;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)


def _format_markdown_to_html(text: str) -> str:
    """Converts simple markdown bold to HTML strong tags."""
    formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    return formatted.replace("\n", "<br>")


@st.cache_data
def load_app_data(config_path: str):
    """Loads configuration and parses Cricsheet JSON once."""
    base_dir = Path(config_path).resolve().parent
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    match_file_rel = config.get("match", {}).get("source_file", "data/match.json")
    match_file = base_dir / match_file_rel

    df = parse_cricsheet_json(match_file)
    return config, df


# Determine config path relative to app.py
current_dir = Path(__file__).parent.resolve()
config_file = current_dir / "config.yaml"

if not config_file.exists():
    st.error(f"Config file not found at {config_file}")
    st.stop()

config, df_deliveries = load_app_data(str(config_file))
rules = config.get("rules", {})
user_players_list = config.get("team", {}).get("user_players", [])
total_balls = len(df_deliveries)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "slider_ball" not in st.session_state:
    st.session_state["slider_ball"] = 1

if "is_playing" not in st.session_state:
    st.session_state["is_playing"] = False

if "last_toasted_idx" not in st.session_state:
    st.session_state["last_toasted_idx"] = 0

if "custom_captain" not in st.session_state:
    # Default initial captain
    def_cap = next((p["name"] for p in user_players_list if p.get("multiplier") == 2.0), "V Kohli")
    st.session_state["custom_captain"] = def_cap

if "dugout_response" not in st.session_state:
    st.session_state["dugout_response"] = None

if "dugout_last_query" not in st.session_state:
    st.session_state["dugout_last_query"] = None

# Active Captain from session state
active_captain_name = st.session_state["custom_captain"]
active_vc_name = next((p["name"] for p in user_players_list if p.get("multiplier") == 1.5), "JJ Bumrah")

# Dynamic user team map applying custom captain
dynamic_team_map = {}
for p in user_players_list:
    pname = p["name"]
    if pname == active_captain_name:
        dynamic_team_map[pname] = 2.0
    elif pname == active_vc_name and active_captain_name != active_vc_name:
        dynamic_team_map[pname] = 1.5
    else:
        dynamic_team_map[pname] = 1.0

# ==========================================
# SIDEBAR CONTROLS: TIMELINE & SIMULATION
# ==========================================
st.sidebar.markdown("### 🔴 Live Match Controller")

sim_col1, sim_col2 = st.sidebar.columns(2)
with sim_col1:
    if st.session_state["is_playing"]:
        if st.button("⏸ Pause", use_container_width=True, help="Pause simulation"):
            st.session_state["is_playing"] = False
            st.rerun()
    else:
        if st.button("▶ Start Match", use_container_width=True, help="Simulate live match delivery by delivery"):
            if st.session_state["slider_ball"] >= total_balls:
                st.session_state["slider_ball"] = 1
            st.session_state["is_playing"] = True
            st.rerun()

with sim_col2:
    if st.button("🔄 Reset", use_container_width=True, help="Reset timeline to Ball 1"):
        st.session_state["is_playing"] = False
        st.session_state["slider_ball"] = 1
        st.rerun()

# Playback Speed Selector
speed_option = st.sidebar.radio(
    "⏱️ Playback Speed",
    options=["Fast (1.0s)", "Normal (2.5s)"],
    index=0,
    horizontal=True,
    help="Interval duration between simulated live deliveries."
)
speed_val = 1.0 if "Fast" in speed_option else 2.5

# Manual Timeline Slider
selected_ball_idx = st.sidebar.slider(
    "Manual Timeline Scrub (Ball by Ball)",
    min_value=1,
    max_value=total_balls,
    value=st.session_state["slider_ball"],
    help="Scrub through deliveries manually. Recalculates all fantasy scores."
)
st.session_state["slider_ball"] = selected_ball_idx

# Quick Jump Presets
st.sidebar.markdown("<span style='font-size:0.8rem; color:#94A3B8;'>⚡ Key Moments:</span>", unsafe_allow_html=True)
q_col1, q_col2, q_col3 = st.sidebar.columns(3)
with q_col1:
    if st.button("🏁 Start", use_container_width=True, help="Ball 1"):
        st.session_state["is_playing"] = False
        st.session_state["slider_ball"] = 1
        st.rerun()
with q_col2:
    if st.button("⚡ Wicket", use_container_width=True, help="Bumrah Bowled (Ball 21)"):
        st.session_state["is_playing"] = False
        st.session_state["slider_ball"] = 21
        st.rerun()
with q_col3:
    if st.button("🏆 Final", use_container_width=True, help="Surya Catch & Finish (Ball 37)"):
        st.session_state["is_playing"] = False
        st.session_state["slider_ball"] = 37
        st.rerun()

st.sidebar.markdown("---")

# Global Language Toggle
language = st.sidebar.radio(
    "🌐 Commentary Language / भाषा",
    options=["English", "Hinglish"],
    index=0,
    horizontal=True,
    help="Switch between English commentary and Indian Romanized Hinglish."
)

st.sidebar.markdown("---")

# Expandable User Team Roster
with st.sidebar.expander("👥 User Fantasy XI", expanded=False):
    for p in user_players_list:
        pname = p["name"]
        mult = dynamic_team_map.get(pname, 1.0)
        tag = ""
        if mult == 2.0:
            tag = " 👑 Captain (2.0x)"
        elif mult == 1.5:
            tag = " ⚡ VC (1.5x)"
        else:
            tag = " (1.0x)"
        st.markdown(f"- **{pname}**{tag}")

# AI Engine & Cache Status
with st.sidebar.expander("🤖 AI Engine & Cache Status", expanded=False):
    has_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if has_key:
        st.success("Gemini API Key detected. Live AI Narration active.")
    else:
        st.info("Pre-generated Cache active. Fast 0ms responses with deterministic fallback.")
    custom_key = st.text_input("Set Gemini API Key (optional):", type="password")
    if custom_key:
        os.environ["GEMINI_API_KEY"] = custom_key.strip()
        st.success("API key updated!")

# ==========================================
# DETERMINISTIC CALCULATION UP TO SELECTED BALL
# ==========================================
df_slice = df_deliveries.iloc[:selected_ball_idx]

all_facts: List[Dict[str, Any]] = []
player_base_totals: Dict[str, float] = {p["name"]: 0.0 for p in user_players_list}
player_final_totals: Dict[str, float] = {p["name"]: 0.0 for p in user_players_list}

team_total_points = 0.0
match_state: Dict[str, Any] = {}

for _, row in df_slice.iterrows():
    row_dict = row.to_dict()
    deltas = compute_ball_deltas(row_dict, rules, dynamic_team_map, match_state=match_state)
    for d in deltas:
        d["delivery_index"] = row_dict["delivery_index"]
        d["delivery_display"] = row_dict["delivery_display"]
        d["innings"] = row_dict["innings"]
        d["team_batting"] = row_dict["team_batting"]
        all_facts.append(d)

        p_name = d["player"]
        if d.get("in_user_team", False):
            player_base_totals[p_name] = round(player_base_totals.get(p_name, 0.0) + d["base_points"], 2)
            player_final_totals[p_name] = round(player_final_totals.get(p_name, 0.0) + d["final_points"], 2)
            team_total_points = round(team_total_points + d["final_points"], 2)

# ==========================================
# HEADER & TOP METRICS BAR
# ==========================================
st.markdown('<div class="main-title">🏏 Match Companion — Dream11 Live AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time match broadcast simulation with deterministic fantasy intelligence</div>', unsafe_allow_html=True)

# Live Simulation Indicator Banner
if st.session_state["is_playing"]:
    st.markdown(f"""
    <div class="live-simulation-banner">
        <div>
            <span class="live-pulse-dot">🔴</span>
            <strong>LIVE SIMULATION ACTIVE</strong> — Broadcasting Delivery {selected_ball_idx} of {total_balls}
        </div>
        <div style="color: #94A3B8;">Speed: {speed_option} • Auto-refreshing...</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="live-simulation-banner" style="border-color: rgba(255,255,255,0.1); background: rgba(30,41,59,0.5);">
        <div>
            <span style="color: #F59E0B; margin-right: 6px;">⏸</span>
            <strong>SIMULATION PAUSED</strong> — Replaying Delivery {selected_ball_idx} of {total_balls}
        </div>
        <div style="color: #94A3B8;">Click '▶ Start Match' in sidebar to stream live.</div>
    </div>
    """, unsafe_allow_html=True)

cap_pts = player_final_totals.get(active_captain_name, 0.0)
vc_pts = player_final_totals.get(active_vc_name, 0.0)
current_row = df_slice.iloc[-1]
current_state_str = f"Inn {current_row['innings']} • {current_row['delivery_display']} ({current_row['team_batting']})"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Total Team Points</div>
        <div class="metric-val" style="color: #10B981;">{int(team_total_points) if team_total_points.is_integer() else team_total_points:.1f} pts</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Active Captain (2.0x)</div>
        <div class="metric-val" style="color: #F59E0B;">{active_captain_name}</div>
        <span style="font-size: 0.85rem; color: #94A3B8;">+{int(cap_pts) if cap_pts.is_integer() else cap_pts:.1f} pts</span>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Active Vice-Captain (1.5x)</div>
        <div class="metric-val" style="color: #3B82F6;">{active_vc_name}</div>
        <span style="font-size: 0.85rem; color: #94A3B8;">+{int(vc_pts) if vc_pts.is_integer() else vc_pts:.1f} pts</span>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Match Progress</div>
        <div class="metric-val" style="font-size: 1.4rem; padding-top: 6px;">{current_state_str}</div>
        <span style="font-size: 0.85rem; color: #94A3B8;">Ball {selected_ball_idx} of {total_balls}</span>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Visual Audio Toasts during live simulation
if selected_ball_idx != st.session_state["last_toasted_idx"]:
    curr_ball_facts = [f for f in all_facts if f.get("delivery_index") == selected_ball_idx]
    for bf in curr_ball_facts:
        if "Wicket" in bf.get("event", ""):
            st.toast(f"🚨 WICKET! {bf['player']} strikes with {bf['event']}!", icon="🎯")
        elif "Six" in bf.get("event", ""):
            st.toast(f"💥 SIX! {bf['player']} clears the boundary ropes!", icon="🚀")
    st.session_state["last_toasted_idx"] = selected_ball_idx

# ==========================================
# MAIN CONTENT TABS
# ==========================================
tab_catchup, tab_explain, tab_whatif, tab_dugout = st.tabs([
    "📖 Catch Me Up",
    "⚡ Explain My Points",
    "👑 What-If Captain",
    "💬 Ask Dugout AI"
])

# Compute innings status for all tabs
curr_inn = current_row["innings"]
curr_team = current_row["team_batting"]
curr_over = current_row["delivery_display"]
inn_slice = df_slice[df_slice["innings"] == curr_inn]
total_runs_inn = inn_slice["runs_total"].sum()
wickets_inn = inn_slice["wicket_kind"].dropna().count()
match_status = f"Innings {curr_inn}: {curr_team} stands at {total_runs_inn}/{wickets_inn} ({curr_over})"

# ------------------------------------------
# TAB 1: CATCH ME UP
# ------------------------------------------
with tab_catchup:
    st.subheader("Match Catch-Up Recap")
    st.caption("Catch up on recent match action with your fantasy players prioritized.")

    recent_facts = all_facts[-8:] if all_facts else []

    with st.spinner("Analyzing match state..."):
        recap_text = narrate_catch_up(recent_facts, match_status, language)

    formatted_recap = _format_markdown_to_html(recap_text)
    st.markdown(f"""
    <div class="catch-up-box">
        {formatted_recap}
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.markdown("#### 🌟 Top Team Contributors Up To This Ball")
    active_contributors = [
        {"Player": p, "Base Pts": player_base_totals[p], "Final Pts": player_final_totals[p], "Multiplier": f"{dynamic_team_map[p]}x"}
        for p in dynamic_team_map
        if player_final_totals[p] != 0
    ]
    if active_contributors:
        contrib_df = pd.DataFrame(active_contributors).sort_values("Final Pts", ascending=False)
        st.dataframe(contrib_df, hide_index=True, use_container_width=True)
    else:
        st.info("No fantasy points scored by your players yet up to this delivery.")

# ------------------------------------------
# TAB 2: EXPLAIN MY POINTS
# ------------------------------------------
with tab_explain:
    st.subheader("Point-by-Point Feed")
    st.caption("Reverse-chronological timeline of point-earning deliveries with instant AI commentary.")

    filter_team_only = st.checkbox("Show only events scoring for My Fantasy XI", value=True)

    feed_facts = [f for f in all_facts if not filter_team_only or f.get("in_user_team", False)]
    feed_facts_rev = list(reversed(feed_facts))

    if not feed_facts_rev:
        st.info("No fantasy point events found for the current selection.")
    else:
        for idx, fact in enumerate(feed_facts_rev):
            p_name = fact["player"]
            cat = fact["category"]
            event = fact["event"]
            pts = fact["final_points"]
            base_pts = fact["base_points"]
            mult = fact["multiplier"]
            in_team = fact["in_user_team"]
            d_display = fact.get("delivery_display", "")

            # Badge formatting
            mult_badge = ""
            if in_team:
                if mult == 2.0:
                    mult_badge = '<span class="badge-cap">👑 2.0x C</span>'
                elif mult == 1.5:
                    mult_badge = '<span class="badge-vc">⚡ 1.5x VC</span>'
                else:
                    mult_badge = '<span class="badge-neutral">1.0x</span>'
            else:
                mult_badge = '<span class="badge-neutral">Not in XI</span>'

            cat_icon = "🏏" if cat == "Batting" else ("🎯" if cat == "Bowling" else "🧤")

            if in_team:
                if pts > 0:
                    pts_display = f"+{int(pts) if pts.is_integer() else pts:.1f} pts"
                    badge_bg = "linear-gradient(135deg, #10B981, #059669)"
                    border_color = "#10B981"
                elif pts < 0:
                    pts_display = f"{int(pts) if pts.is_integer() else pts:.1f} pts"
                    badge_bg = "linear-gradient(135deg, #EF4444, #DC2626)"
                    border_color = "#EF4444"
                else:
                    pts_display = "0 pts"
                    badge_bg = "#475569"
                    border_color = "#64748B"
            else:
                pts_display = f"+{int(base_pts) if base_pts.is_integer() else base_pts:.1f} base"
                badge_bg = "#475569"
                border_color = "#64748B"

            explanation = narrate_point_event(fact, language)
            formatted_explanation = _format_markdown_to_html(explanation)

            st.markdown(f"""
            <div class="event-card" style="border-left: 4px solid {border_color};">
                <div style="flex: 1;">
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 2px;">
                        {d_display} • {cat_icon} {cat} • <strong>{p_name}</strong> {mult_badge}
                    </div>
                    <div style="color: #F1F5F9; font-size: 0.96rem;">
                        {formatted_explanation}
                    </div>
                </div>
                <div style="margin-left: 15px; text-align: right;">
                    <span class="badge-points" style="background: {badge_bg};">
                        {pts_display}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 3: WHAT-IF CAPTAIN & ROSTER CUSTOMIZER
# ------------------------------------------
with tab_whatif:
    st.subheader("Dynamic Captain Switcher & What-If Scenarios")
    st.caption("Change your captain in real-time or evaluate historical differentials against optimal picks.")

    # Interactive Captain Selectbox
    all_player_names = [p["name"] for p in user_players_list]
    cap_idx = all_player_names.index(active_captain_name) if active_captain_name in all_player_names else 0

    new_selected_captain = st.selectbox(
        "👑 Switch Active Captain (2.0x Multiplier):",
        options=all_player_names,
        index=cap_idx,
        help="Select any player in your 11 to immediately re-calculate your entire fantasy score."
    )

    if new_selected_captain != active_captain_name:
        st.session_state["custom_captain"] = new_selected_captain
        st.rerun()

    # Differential calculation
    cap_base = player_base_totals.get(active_captain_name, 0.0)
    whatifs = calculate_captain_whatifs(player_base_totals, active_captain_name)

    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.5); padding: 12px 18px; border-radius: 8px; margin-top: 10px; margin-bottom: 16px;">
        Active Captain: <strong>👑 {active_captain_name}</strong> (Base Points: <strong>{int(cap_base) if cap_base.is_integer() else cap_base:.1f}</strong> | Total Team Points: <strong>{int(team_total_points) if team_total_points.is_integer() else team_total_points:.1f}</strong>)
    </div>
    """, unsafe_allow_html=True)

    if whatifs:
        best_pick = whatifs[0]
        if best_pick["net_difference"] > 0:
            st.success(
                f"💡 **Top What-If Insight:** Switching Captain to **{best_pick['player']}** would give you "
                f"**{best_pick['alternate_total_change']}**, elevating your team total to **{team_total_points + best_pick['net_difference']} pts**!"
            )
        elif best_pick["net_difference"] == 0:
            st.info("💡 Your active captain selection matches the best fantasy points outcome up to this ball.")
        else:
            st.info(f"👑 **Optimal Selection!** Active Captain **{active_captain_name}** is outperforming all other teammates.")

        table_rows = []
        for w in whatifs:
            alt_player = w["player"]
            net_diff = w["net_difference"]
            change_str = w["alternate_total_change"]
            new_team_total = round(team_total_points + net_diff, 2)
            alt_base = player_base_totals.get(alt_player, 0.0)

            table_rows.append({
                "Alternative Captain": f"🏏 {alt_player}",
                "Player Base Pts": int(alt_base) if alt_base.is_integer() else alt_base,
                "Net Point Impact": change_str,
                "New Team Total": f"{int(new_team_total) if new_team_total.is_integer() else new_team_total:.1f} pts"
            })

        whatif_df = pd.DataFrame(table_rows)
        st.dataframe(whatif_df, hide_index=True, use_container_width=True)

    # Projected Finish & Milestones
    st.markdown("#### 🎯 Projected Finish & Milestone Tracker")
    st.caption("Upcoming milestone triggers that could swing final contest ranks:")

    # Milestone predictions based on current match stats
    p_cols = st.columns(3)
    with p_cols[0]:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border-left: 3px solid #F59E0B;">
            <strong>🎯 3-Wicket Haul Bonus (+4 pts)</strong><br>
            <span style="font-size:0.85rem; color:#CBD5E1;">
            • <strong>JJ Bumrah</strong>: 2 wickets (Needs 1 more wicket)<br>
            • <strong>Hardik Pandya</strong>: 2 wickets (Needs 1 more wicket)
            </span>
        </div>
        """, unsafe_allow_html=True)
    with p_cols[1]:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border-left: 3px solid #10B981;">
            <strong>🏏 30+ Run Batting Bonus (+4 pts)</strong><br>
            <span style="font-size:0.85rem; color:#CBD5E1;">
            • <strong>Virat Kohli</strong>: 12 runs (18 runs away)<br>
            • <strong>Heinrich Klaasen</strong>: 6 runs (24 runs away)
            </span>
        </div>
        """, unsafe_allow_html=True)
    with p_cols[2]:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
            <strong>🧤 3-Catch Fielding Bonus (+4 pts)</strong><br>
            <span style="font-size:0.85rem; color:#CBD5E1;">
            • <strong>SA Yadav</strong>: 2 catches (Needs 1 catch)<br>
            • <strong>RG Sharma</strong>: 1 catch (Needs 2 catches)
            </span>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 4: ASK DUGOUT AI
# ------------------------------------------
with tab_dugout:
    st.subheader("💬 Ask Dugout AI")
    st.caption("Ask live tactical, field setup, or fantasy scoring questions grounded in the current delivery state.")

    # Snapshot dictionary for Dugout AI
    live_snapshot = {
        "delivery_display": current_row["delivery_display"],
        "innings": current_row["innings"],
        "team_batting": current_row["team_batting"],
        "runs_total_innings": total_runs_inn,
        "wickets_total_innings": wickets_inn,
        "batter": current_row["batter"],
        "bowler": current_row["bowler"],
        "team_points": team_total_points,
        "captain_name": active_captain_name,
        "vc_name": active_vc_name,
        "last_event": all_facts[-1]["event"] if all_facts else "Standard delivery",
    }

    # Quick prompt pills
    st.markdown("<span style='font-size:0.85rem; color:#94A3B8;'>💡 Quick Questions:</span>", unsafe_allow_html=True)
    pill_c1, pill_c2, pill_c3 = st.columns(3)
    
    with pill_c1:
        if st.button("🎯 Why is this bowler bowling?", use_container_width=True):
            st.session_state["dugout_last_query"] = "Why is this bowler bowling right now?"
            st.session_state["dugout_response"] = answer_fan_query(
                "Why is this bowler bowling right now?", live_snapshot, language
            )
    with pill_c2:
        if st.button("🌟 Who has the highest upside?", use_container_width=True):
            st.session_state["dugout_last_query"] = "Who in my lineup has the highest upside this phase?"
            st.session_state["dugout_response"] = answer_fan_query(
                "Who in my lineup has the highest upside this phase?", live_snapshot, language
            )
    with pill_c3:
        if st.button("🛡️ Explain the current field setup.", use_container_width=True):
            st.session_state["dugout_last_query"] = "Explain the current field setup."
            st.session_state["dugout_response"] = answer_fan_query(
                "Explain the current field setup.", live_snapshot, language
            )

    # Free text input query
    with st.form(key="dugout_form", clear_on_submit=False):
        user_query = st.text_input(
            "Or ask any question about this live delivery or fantasy points:",
            placeholder="e.g. Can Bumrah get me into the top rank? What happens if Miller hits a six?",
        )
        submit_btn = st.form_submit_button("Ask Dugout AI ⚡", use_container_width=True)

    if submit_btn and user_query:
        st.session_state["dugout_last_query"] = user_query
        with st.spinner("Analyzing live dugout tactics..."):
            st.session_state["dugout_response"] = answer_fan_query(user_query, live_snapshot, language)

    # Display Dugout AI Response
    if st.session_state["dugout_response"]:
        st.markdown(f"""
        <div class="dugout-chat-bubble">
            <div style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 4px;">
                💬 <strong>Question:</strong> "{st.session_state['dugout_last_query']}"
            </div>
            <div style="color: #F8FAFC; font-size: 1.0rem;">
                🤖 <strong>Dugout AI:</strong> {st.session_state['dugout_response']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("""
<div class="footer-text">
    Demo replays past match events deterministically. Not an odds, betting, or prediction tool.
</div>
""", unsafe_allow_html=True)

# ==========================================
# LIVE SIMULATION STREAMING LOOP
# ==========================================
if st.session_state["is_playing"]:
    if selected_ball_idx < total_balls:
        time.sleep(speed_val)
        st.session_state["slider_ball"] = selected_ball_idx + 1
        st.rerun()
    else:
        st.session_state["is_playing"] = False
        st.toast("🏆 Match Concluded! Final scores calculated.", icon="🎉")
        st.rerun()
