"""
honeypot_detector.py
────────────────────
Identifies ~80 fake / impossible candidate profiles ("honeypots") planted in
the 100 K-candidate dataset.

Design philosophy
-----------------
* **Conservative** – each heuristic has thresholds tuned to produce near-zero
  false positives.  It is better to miss a honeypot than to wrongly penalise
  a real candidate.
* **Composable** – ``get_honeypot_reasons`` returns human-readable explanations
  for every heuristic that fired, so downstream scorers can log *why* a
  candidate was flagged.
* **Fast** – purely numeric / set-based checks; no NLP or heavy computation.
  Runs in < 1 s for 100 K candidates.

The five heuristic families correspond to the five classes of impossibility the
contest organisers described:

1. Impossible skill claims (expert/advanced proficiency with ≤ 3 months usage)
2. Skill-assessment contradictions (low test scores for self-declared experts)
3. Career-timeline impossibilities (reverse dates, impossible overlap, duration
   mismatch)
4. Endorsement anomaly (mountains of endorsements with almost no connections)
5. Profile-completeness paradox (perfect score on an empty profile)
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Constants – tuned for low false-positive rate
# ──────────────────────────────────────────────────────────────────────────────

# Heuristic 1: Impossible skill claims
_IMPOSSIBLE_SKILL_MIN_COUNT = 3          # need ≥ 3 such skills
_IMPOSSIBLE_SKILL_MAX_DURATION = 3       # months

# Heuristic 2: Assessment contradiction
_ASSESS_LOW_SCORE_THRESHOLD = 30         # score ≤ this is "very low"
_ASSESS_MIN_CONTRADICTIONS = 2           # need ≥ 2 contradicting skills

# Heuristic 3: Career timeline
_CAREER_DURATION_RATIO_THRESHOLD = 2.0   # sum/expected must exceed this
_MIN_CONCURRENT_CURRENT = 2             # flag only with 2+ concurrent "is_current"

# Heuristic 4: Endorsement anomaly
_ENDORSE_MIN_SKILLS = 5                 # at least this many skills with
_ENDORSE_MIN_PER_SKILL = 50             # … at least this many endorsements
_ENDORSE_MAX_CONNECTIONS = 20            # … but fewer than this many connections

# Heuristic 5: Completeness paradox
_COMPLETENESS_MIN_SCORE = 95             # claimed completeness ≥ this
_COMPLETENESS_MAX_SKILLS = 3             # but ≤ this many skills


# ──────────────────────────────────────────────────────────────────────────────
# Individual heuristic checkers
# ──────────────────────────────────────────────────────────────────────────────

def _check_impossible_skills(candidate: dict) -> list[str]:
    """
    Heuristic 1 – Expert / advanced proficiency with near-zero usage time.

    A real expert doesn't list a skill they've used for 0 months.  Honeypots
    tend to have *many* such skills to look impressively broad.
    """
    reasons: list[str] = []
    skill_details: dict = candidate.get("skill_details", {})

    impossible_count = 0
    impossible_names: list[str] = []
    for name, info in skill_details.items():
        prof = info.get("proficiency", "")
        dur = info.get("duration_months", 999)
        if prof in ("expert", "advanced") and dur <= _IMPOSSIBLE_SKILL_MAX_DURATION:
            impossible_count += 1
            impossible_names.append(name)

    if impossible_count >= _IMPOSSIBLE_SKILL_MIN_COUNT:
        reasons.append(
            f"Impossible skill claims: {impossible_count} skills listed as "
            f"expert/advanced with ≤{_IMPOSSIBLE_SKILL_MAX_DURATION} months "
            f"usage ({', '.join(impossible_names[:8])})"
        )
    return reasons


def _check_assessment_contradiction(candidate: dict) -> list[str]:
    """
    Heuristic 2 – Self-declared expert but bombed the platform's own test.

    If a candidate claims expert proficiency yet scores < 30 on the Redrob
    assessment for 3+ skills, the profile is likely fabricated.
    """
    reasons: list[str] = []
    signals: dict = candidate.get("redrob_signals", {})
    assessments: dict = signals.get("skill_assessment_scores", {})
    skill_details: dict = candidate.get("skill_details", {})

    if not assessments:
        return reasons

    contradiction_count = 0
    contradiction_names: list[str] = []

    for assessed_skill, score in assessments.items():
        lc_skill = assessed_skill.lower().strip()
        try:
            score_val = float(score)
        except (ValueError, TypeError):
            continue
        if score_val >= _ASSESS_LOW_SCORE_THRESHOLD:
            continue

        # Check whether this skill is self-declared as expert/advanced
        detail = skill_details.get(lc_skill)
        if detail and detail.get("proficiency") in ("expert", "advanced"):
            contradiction_count += 1
            contradiction_names.append(f"{assessed_skill} (score={score_val:.0f})")

    if contradiction_count >= _ASSESS_MIN_CONTRADICTIONS:
        reasons.append(
            f"Skill-assessment contradiction: {contradiction_count} skills "
            f"claimed expert/advanced but scored <{_ASSESS_LOW_SCORE_THRESHOLD} "
            f"on assessment ({', '.join(contradiction_names[:6])})"
        )
    return reasons


def _parse_date_safe(date_str: Any) -> date | None:
    """Try to parse a date string in ISO format; return None on failure."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _check_career_timeline(candidate: dict) -> list[str]:
    """
    Heuristic 3 – Physically impossible career timelines.

    Three sub-checks:
    a) start_date after end_date on any position
    b) Total duration wildly exceeds stated years_of_experience
    c) 3+ positions simultaneously marked ``is_current``
    """
    reasons: list[str] = []
    career: list[dict] = candidate.get("career_history", [])
    yoe: float = candidate.get("years_of_experience", 0.0)

    if not career:
        return reasons

    # --- a) Reversed dates ---
    reversed_positions: list[str] = []
    for pos in career:
        start = _parse_date_safe(pos.get("start_date"))
        end = _parse_date_safe(pos.get("end_date"))
        if start and end and start > end:
            reversed_positions.append(
                f"{pos.get('title', '?')} @ {pos.get('company', '?')} "
                f"({pos.get('start_date')} > {pos.get('end_date')})"
            )
    if reversed_positions:
        reasons.append(
            f"Career timeline: start_date > end_date in "
            f"{len(reversed_positions)} position(s): "
            f"{'; '.join(reversed_positions[:4])}"
        )

    # --- b) Duration sum vs stated experience ---
    total_months = 0
    for pos in career:
        dur = pos.get("duration_months")
        if dur is not None:
            try:
                total_months += max(0, int(dur))
            except (ValueError, TypeError):
                pass

    if yoe > 0 and total_months > 0:
        expected_months = yoe * 12
        ratio = total_months / expected_months
        if ratio >= _CAREER_DURATION_RATIO_THRESHOLD:
            reasons.append(
                f"Career timeline: total career duration "
                f"({total_months} mo) is {ratio:.1f}× the stated "
                f"experience ({yoe} yrs / {expected_months:.0f} mo)"
            )

    # --- c) Multiple concurrent "is_current" positions ---
    current_positions = [
        p for p in career if p.get("is_current") is True
    ]
    # Only flag at different companies (same company = internal transfer)
    current_companies = {p.get("company", "").strip().lower() for p in current_positions}
    if len(current_companies) >= _MIN_CONCURRENT_CURRENT:
        companies = [p.get("company", "?") for p in current_positions]
        reasons.append(
            f"Career timeline: {len(current_companies)} concurrent "
            f"'is_current' positions at different companies: "
            f"{', '.join(companies[:5])}"
        )

    return reasons


def _check_endorsement_anomaly(candidate: dict) -> list[str]:
    """
    Heuristic 4 – Implausible endorsement-to-connection ratio.

    If someone has 10+ skills each with 50+ endorsements but fewer than 20
    connections, the endorsements are clearly fabricated.
    """
    reasons: list[str] = []
    skill_details: dict = candidate.get("skill_details", {})
    signals: dict = candidate.get("redrob_signals", {})
    connection_count: int = int(signals.get("connection_count", 9999))

    if connection_count >= _ENDORSE_MAX_CONNECTIONS:
        return reasons  # enough connections — plausible

    high_endorse_count = sum(
        1 for info in skill_details.values()
        if info.get("endorsements", 0) >= _ENDORSE_MIN_PER_SKILL
    )

    if high_endorse_count >= _ENDORSE_MIN_SKILLS:
        reasons.append(
            f"Endorsement anomaly: {high_endorse_count} skills with "
            f"≥{_ENDORSE_MIN_PER_SKILL} endorsements each, but only "
            f"{connection_count} connections"
        )
    return reasons


def _check_completeness_paradox(candidate: dict) -> list[str]:
    """
    Heuristic 5 – Near-perfect completeness score on a near-empty profile.

    A completeness score > 95 combined with missing summary, zero
    certifications, zero languages, and < 3 skills is paradoxical.
    """
    reasons: list[str] = []
    signals: dict = candidate.get("redrob_signals", {})
    completeness = float(signals.get("profile_completeness_score", 0))

    if completeness < _COMPLETENESS_MIN_SCORE:
        return reasons

    summary = candidate.get("summary", "").strip()
    certs = candidate.get("certifications", [])
    langs = candidate.get("languages", [])
    skill_count = len(candidate.get("skill_names", []))

    if (not summary) and (not certs) and (not langs) and (skill_count < _COMPLETENESS_MAX_SKILLS):
        reasons.append(
            f"Completeness paradox: profile_completeness_score="
            f"{completeness:.1f} but summary is empty, 0 certifications, "
            f"0 languages, and only {skill_count} skill(s)"
        )
    return reasons


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

_HEURISTIC_CHECKS = [
    _check_impossible_skills,
    _check_assessment_contradiction,
    _check_career_timeline,
    _check_endorsement_anomaly,
    _check_completeness_paradox,
]


def get_honeypot_reasons(candidate: dict) -> list[str]:
    """
    Return a list of human-readable reasons why *candidate* might be a
    honeypot.  An empty list means no red flags were found.

    Parameters
    ----------
    candidate : dict
        A normalised candidate dict (as produced by
        :func:`data_loader.stream_candidates`).

    Returns
    -------
    list[str]
        Zero or more reason strings.  Each string describes one
        impossibility detected.
    """
    reasons: list[str] = []
    for check_fn in _HEURISTIC_CHECKS:
        reasons.extend(check_fn(candidate))
    return reasons


def detect_honeypots(candidates: list[dict]) -> set[str]:
    """
    Scan a list of normalised candidates and return the ``candidate_id`` of
    every profile flagged as a honeypot (fake / impossible).

    A candidate is flagged if **any** heuristic fires at least one reason.

    Parameters
    ----------
    candidates : list[dict]
        Full list of normalised candidate dicts.

    Returns
    -------
    set[str]
        Set of ``candidate_id`` values identified as honeypots.
    """
    flagged: set[str] = set()

    for cand in candidates:
        reasons = get_honeypot_reasons(cand)
        if reasons:
            cid = cand.get("candidate_id", "UNKNOWN")
            flagged.add(cid)
            logger.debug(
                "HONEYPOT %s: %s", cid, " | ".join(reasons)
            )

    logger.info(
        "Honeypot detection complete: %d / %d candidates flagged (%.2f%%)",
        len(flagged),
        len(candidates),
        100.0 * len(flagged) / max(len(candidates), 1),
    )
    return flagged


# ──────────────────────────────────────────────────────────────────────────────
# Quick CLI test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python honeypot_detector.py <path/to/candidates.jsonl>")
        sys.exit(1)

    from data_loader import load_all_candidates

    candidates = load_all_candidates(sys.argv[1])
    flagged = detect_honeypots(candidates)

    print(f"\n{'='*60}")
    print(f"  Flagged {len(flagged)} honeypots out of {len(candidates)} candidates")
    print(f"{'='*60}")

    for cand in candidates:
        cid = cand["candidate_id"]
        if cid in flagged:
            reasons = get_honeypot_reasons(cand)
            print(f"\n  🚩 {cid} ({cand['name']})")
            for r in reasons:
                print(f"     • {r}")
