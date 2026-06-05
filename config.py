"""
Configuration for AI Recruiter Pipeline — Redrob Hackathon
All scoring is local/rule-based. No LLM calls. No network.
Must complete in <5 min on CPU with 16GB RAM.
"""

# ─── Scoring Weights (must sum to 1.0) ───────────────────────────────────────
SCORING_WEIGHTS = {
    "skills_match":          0.25,   # Technical skill coverage vs JD requirements
    "career_trajectory":     0.25,   # Product-company experience, role relevance, progression
    "experience_fit":        0.15,   # Years of experience vs 5-9 year sweet spot
    "behavioral_signals":    0.15,   # Redrob platform engagement & availability
    "location_logistics":    0.05,   # India-based, Tier-1 city, relocation willingness
    "education_credentials": 0.05,   # Institution tier, field relevance, certifications
    "anti_pattern_bonus":    0.10,   # Positive signal boost (not a penalty — penalty is multiplicative)
}

# ─── Anti-Pattern Penalty Multipliers ─────────────────────────────────────────
# These are applied as multipliers on the final score
PENALTIES = {
    "consulting_only_career":    0.08,   # Entire career at TCS/Infosys/Wipro etc.
    "completely_irrelevant_role": 0.05,  # Accountant, civil engineer, etc. with no AI
    "keyword_stuffer":           0.10,   # Many AI keywords but no matching career
    "title_chaser":              0.60,   # Frequent job hopping for titles
    "cv_speech_robotics_only":   0.40,   # Primary CV/speech/robotics without NLP/IR
    "inactive_candidate":        0.50,   # Last active >6 months ago
    "honeypot":                  0.00,   # Confirmed honeypot = zero score
}

# ─── Experience Parameters ────────────────────────────────────────────────────
IDEAL_EXPERIENCE_MIN = 5.0
IDEAL_EXPERIENCE_MAX = 9.0
SWEET_SPOT_MIN = 6.0
SWEET_SPOT_MAX = 8.0
ABSOLUTE_MIN_EXPERIENCE = 2.0   # Below this, very unlikely to be considered

# ─── Behavioral Signal Thresholds ─────────────────────────────────────────────
HIGH_RESPONSE_RATE = 0.60
LOW_RESPONSE_RATE = 0.20
SHORT_NOTICE_DAYS = 30
LONG_NOTICE_DAYS = 90
RECENT_ACTIVITY_DAYS = 90   # Active within last 90 days = good
STALE_ACTIVITY_DAYS = 180   # Not active in 180+ days = concerning

# ─── Output ───────────────────────────────────────────────────────────────────
TOP_N = 100                 # Submission requires exactly 100 candidates
OUTPUT_FILE = "submission.csv"
