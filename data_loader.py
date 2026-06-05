"""
data_loader.py
──────────────
Memory-efficient JSONL loader for the Redrob Hackathon candidate dataset.

Design choices
--------------
* **Stream parsing** – reads one line at a time so peak memory stays ~1 candidate
  even for the 487 MB / 100K-candidate file.
* **Flat dict normalisation** – every candidate is projected into a dict with
  well-known keys so downstream scorers never have to dig into nested JSON.
* **Pre-computed text blobs** – `career_descriptions_text` and `all_text` are
  built once during load so keyword matching is a single `in` check later.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Generator, Iterator

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_str(val: Any) -> str:
    """Convert *val* to a stripped string; ``None`` becomes ``""``."""
    if val is None:
        return ""
    return str(val).strip()


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Best-effort cast to float, falling back to *default*."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_list(val: Any) -> list:
    """Return *val* if it is a list, else ``[]``."""
    return val if isinstance(val, list) else []


def _safe_dict(val: Any) -> dict:
    """Return *val* if it is a dict, else ``{}``."""
    return val if isinstance(val, dict) else {}


# ──────────────────────────────────────────────────────────────────────────────
# Core normaliser (one candidate at a time)
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_candidate(raw: dict) -> dict:
    """
    Transform a raw JSON object from the JSONL file into a flat,
    consistently-typed dict used by every downstream component.

    Parameters
    ----------
    raw : dict
        A single parsed JSON line from the candidate dataset.

    Returns
    -------
    dict
        Flat candidate dict with the following keys:

        - **candidate_id** (*str*)
        - **name** (*str*) – ``profile.anonymized_name``
        - **headline** (*str*)
        - **summary** (*str*)
        - **location** (*str*)
        - **country** (*str*)
        - **years_of_experience** (*float*)
        - **current_title** (*str*)
        - **current_company** (*str*)
        - **current_company_size** (*str*)
        - **current_industry** (*str*)
        - **career_history** (*list[dict]*) – kept as-is
        - **education** (*list[dict]*) – kept as-is
        - **skills** (*list[dict]*) – kept as-is
        - **skill_names** (*list[str]*) – lowercased skill names
        - **skill_details** (*dict*) – ``{lc_name: {proficiency, endorsements, duration_months}}``
        - **certifications** (*list[dict]*) – kept as-is
        - **languages** (*list[dict]*) – kept as-is
        - **redrob_signals** (*dict*) – kept as-is
        - **career_descriptions_text** (*str*) – all descriptions concatenated, lowercased
        - **all_text** (*str*) – headline + summary + descriptions + skills + certs, lowercased
    """
    profile: dict = _safe_dict(raw.get("profile"))
    career_history: list[dict] = _safe_list(raw.get("career_history"))
    education: list[dict] = _safe_list(raw.get("education"))
    skills: list[dict] = _safe_list(raw.get("skills"))
    certifications: list[dict] = _safe_list(raw.get("certifications"))
    languages: list[dict] = _safe_list(raw.get("languages"))
    redrob_signals: dict = _safe_dict(raw.get("redrob_signals"))

    # --- Flat profile fields ---
    headline = _safe_str(profile.get("headline"))
    summary = _safe_str(profile.get("summary"))

    # --- Skill helpers ---
    skill_names: list[str] = []
    skill_details: dict[str, dict] = {}
    for sk in skills:
        name_lc = _safe_str(sk.get("name")).lower()
        if name_lc:
            skill_names.append(name_lc)
            skill_details[name_lc] = {
                "proficiency": _safe_str(sk.get("proficiency")).lower(),
                "endorsements": int(_safe_float(sk.get("endorsements"))),
                "duration_months": int(_safe_float(sk.get("duration_months"))),
            }

    # --- Pre-computed text blobs (lowercased once, used many times) ---
    career_descs: list[str] = []
    for ch in career_history:
        desc = _safe_str(ch.get("description"))
        if desc:
            career_descs.append(desc)
    career_descriptions_text = " ".join(career_descs).lower()

    cert_names = [_safe_str(c.get("name")).lower() for c in certifications if c.get("name")]

    all_text_parts: list[str] = [
        headline.lower(),
        summary.lower(),
        career_descriptions_text,
        " ".join(skill_names),
        " ".join(cert_names),
    ]
    all_text = " ".join(all_text_parts)

    return {
        "candidate_id":             _safe_str(raw.get("candidate_id")),
        "name":                     _safe_str(profile.get("anonymized_name")),
        "headline":                 headline,
        "summary":                  summary,
        "location":                 _safe_str(profile.get("location")),
        "country":                  _safe_str(profile.get("country")),
        "years_of_experience":      _safe_float(profile.get("years_of_experience")),
        "current_title":            _safe_str(profile.get("current_title")),
        "current_company":          _safe_str(profile.get("current_company")),
        "current_company_size":     _safe_str(profile.get("current_company_size")),
        "current_industry":         _safe_str(profile.get("current_industry")),
        "career_history":           career_history,
        "education":                education,
        "skills":                   skills,
        "skill_names":              skill_names,
        "skill_details":            skill_details,
        "certifications":           certifications,
        "languages":                languages,
        "redrob_signals":           redrob_signals,
        "career_descriptions_text": career_descriptions_text,
        "all_text":                 all_text,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def stream_candidates(path: str | Path) -> Generator[dict, None, None]:
    """
    Lazily stream normalised candidate dicts from a JSONL file.

    Parameters
    ----------
    path : str | Path
        Path to the ``candidates.jsonl`` file.

    Yields
    ------
    dict
        One normalised candidate dict per valid line. Malformed lines are
        logged as warnings and skipped.

    Examples
    --------
    >>> for cand in stream_candidates("candidates.jsonl"):
    ...     print(cand["candidate_id"], cand["skill_names"][:3])
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Candidate file not found: {path}")

    skipped = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                skipped += 1
                logger.warning(
                    "Skipping malformed JSON on line %d: %s", line_no, exc
                )
                continue

            if not isinstance(raw, dict):
                skipped += 1
                logger.warning(
                    "Skipping line %d: expected dict, got %s",
                    line_no,
                    type(raw).__name__,
                )
                continue

            try:
                yield _normalise_candidate(raw)
            except Exception as exc:
                skipped += 1
                cid = raw.get("candidate_id", "UNKNOWN")
                logger.warning(
                    "Skipping candidate %s (line %d) due to normalisation "
                    "error: %s",
                    cid,
                    line_no,
                    exc,
                )

    if skipped:
        logger.info("Total skipped lines: %d", skipped)


def load_all_candidates(path: str | Path) -> list[dict]:
    """
    Load **all** normalised candidates into memory at once.

    This calls :func:`stream_candidates` internally and materialises the
    generator into a list.  For 100 K candidates (~487 MB on disk) this
    will use roughly 2-4 GB of RAM — well within the 16 GB budget.

    Parameters
    ----------
    path : str | Path
        Path to the ``candidates.jsonl`` file.

    Returns
    -------
    list[dict]
        List of normalised candidate dicts.
    """
    candidates = list(stream_candidates(path))
    logger.info("Loaded %d candidates from %s", len(candidates), path)
    return candidates


# ──────────────────────────────────────────────────────────────────────────────
# Quick sanity check when run as a script
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python data_loader.py <path/to/candidates.jsonl>")
        sys.exit(1)

    jsonl_path = sys.argv[1]
    count = 0
    for cand in stream_candidates(jsonl_path):
        count += 1
        if count <= 3:
            print(
                f"  [{cand['candidate_id']}] {cand['name']} | "
                f"{cand['current_title']} @ {cand['current_company']} | "
                f"skills={len(cand['skill_names'])} | "
                f"yrs={cand['years_of_experience']}"
            )
    print(f"\nTotal candidates streamed: {count}")
