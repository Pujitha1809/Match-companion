# Assignment Submission Note (Under 200 Words)

**Problem:**  
Fantasy fans watching live matches see their points change but rarely understand why. Fans who join mid-match also feel lost. Both moments make the experience feel opaque exactly when excitement peaks.

**Solution:**  
Match Companion has two core features. *Catch Me Up* provides a 30-second recap focused on the fan's own fantasy players. *Explain My Points* turns each point delta into a concise sentence (e.g., "Captain Kohli struck a boundary: 5 × 2 = 10 pts") and provides a *What-If Captain* analysis. Both features support English and Hinglish, matching how fans naturally discuss cricket.

**Design Choice:**  
Points are computed by a deterministic mathematical engine using official Dream11 T20 rules. The AI strictly narrates structured facts, guaranteeing that numbers are never hallucinated. There are zero predictions or betting-style tips.

**AI Tools:**  
Gemini 1.5 Flash for contextual commentary narration; Antigravity for pair-programming assistance.

**Demo Note:**  
Replays the 2024 ICC T20 World Cup Final (IND vs SA) using Cricsheet ball-by-ball data, featuring an offline cache to guarantee zero-latency evaluation without API keys.

