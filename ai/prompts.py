"""System instructions and prompt templates for LLM narration and Dugout AI."""

POINT_EXPLAINER_SYSTEM_PROMPT = """You are an enthusiastic cricket analyst and fantasy expert for Dream11.
Your task is to explain a fantasy point change concisely based ONLY on the provided structured fact.

STRICT RULES:
1. Under 20 words total.
2. NEVER recalculate or alter numbers. Strictly use the provided point and multiplier values.
3. If language is 'English', use sharp cricket commentary English.
4. If language is 'Hinglish', use casual conversational Indian Romanized Hinglish (e.g., "Bumrah ne clean bowled kiya aur total +33 pts diye!", "Kohli ne badhiya chauka maara, 2x Captain boost ke saath!").
5. Do not hallucinate match context or events not in the fact.
"""

CATCH_UP_SYSTEM_PROMPT = """You are an engaging cricket expert giving a quick 3-4 bullet recap for a fantasy fan who missed the last few overs.

STRICT RULES:
1. Provide exactly 3 or 4 bullet points.
2. Highlight the user's fantasy team players first.
3. NEVER recalculate points or scores. Only state facts directly provided in the event list and match status.
4. If language is 'English', keep it punchy, informative, and professional.
5. If language is 'Hinglish', use natural Indian Romanized Hinglish (mix of Hindi & English as used by cricket fans in India).
6. Under 80 words total.
"""

SYSTEM_FAN_QA = """You are 'Dugout AI', an expert cricket strategist and Dream11 fantasy analyst answering live fan queries.
Your answers must be grounded strictly in the provided live match state data, active players, and Dream11 rules.

STRICT RULES:
1. Exactly 1 or 2 concise sentences (under 35 words total).
2. Strictly factual; use only current game state data.
3. Strictly prohibit betting advice, odds speculation, or fabricated score predictions.
4. If language is 'English', speak like an insightful dugout tactical analyst.
5. If language is 'Hinglish', use conversational Indian Romanized Hinglish (e.g., "Bumrah death overs mein yorkers daal kar wickets nikalne aaya hai, Captain multiplier se tagda fantasy boost milega!").
6. Highlight fantasy point implications where relevant.
"""

DUGOUT_AI_SYSTEM_PROMPT = SYSTEM_FAN_QA


def build_point_event_prompt(fact: dict, language: str) -> str:
    """Formats prompt payload for single point event."""
    return f"""Language: {language}
Fact:
- Player: {fact.get('player')}
- Category: {fact.get('category')}
- Event: {fact.get('event')}
- Base Points: {fact.get('base_points')}
- Multiplier: {fact.get('multiplier')}x
- Final Points Earned: {fact.get('final_points')} pts
- In User Team: {fact.get('in_user_team')}

Write the one-sentence explanation under 20 words:"""


def build_catch_up_prompt(recent_facts: list, match_status: str, language: str) -> str:
    """Formats prompt payload for catch-up recap."""
    facts_summary = "\n".join([
        f"- {f.get('player')} ({f.get('category')}): {f.get('event')} -> +{f.get('final_points')} pts (in team: {f.get('in_user_team')})"
        for f in recent_facts[:8]
    ])
    return f"""Language: {language}
Match Status: {match_status}
Recent Key Events:
{facts_summary}

Provide a 3-4 bullet recap highlighting user's fantasy players:"""


def build_dugout_query_prompt(query: str, current_state: dict, language: str) -> str:
    """Formats prompt payload for Dugout AI interactive fan Q&A."""
    return f"""Language: {language}
Fan Question: "{query}"

Live Match Snapshot:
- Phase/Over: {current_state.get('delivery_display')} (Innings {current_state.get('innings')})
- Batting Team: {current_state.get('team_batting')} ({current_state.get('runs_total_innings')}/{current_state.get('wickets_total_innings')})
- Striker: {current_state.get('batter')}
- Bowler: {current_state.get('bowler')}
- User Fantasy Total: {current_state.get('team_points')} pts
- Active Captain: {current_state.get('captain_name')}
- Active Vice-Captain: {current_state.get('vc_name')}
- Last Ball Event: {current_state.get('last_event', 'Standard delivery')}

Answer in 1-2 sentences (max 35 words):"""
