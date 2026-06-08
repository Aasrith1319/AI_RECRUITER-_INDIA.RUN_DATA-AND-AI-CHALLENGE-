---
title: Redrob Candidate Ranker
emoji: 🏆
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.36.1
app_file: app.py
pinned: false
python_version: 3.10
---

# AI Candidate Ranking System — Redrob Hackathon

> **The Data & AI Challenge — Intelligent Candidate Discovery & Ranking**
> Ranks candidates the way a great recruiter would — not by matching keywords, but by actually understanding who fits the role.

---

## Architecture

```
candidates.jsonl (100K)
        |
        v
+-------------------------+
|  1. Load & Parse JSONL  |  Stream-parse, normalize to feature dicts
+----------+--------------+
           |
           v
+-------------------------+
|  2. Honeypot Detector   |  Flag impossible profiles (remove from pool)
+----------+--------------+
           |
           v
+---------------------------------------------------------------+
|  3. Multi-Dimensional Scoring Engine (7 components)           |
|                                                               |
|  (1) Technical Skills Match         -- 25%                    |
|      * Must-have skill coverage (fuzzy + synonym matching)    |
|      * Proficiency-weighted, endorsement-validated            |
|      * Skill assessment scores from Redrob platform           |
|                                                               |
|  (2) Career Trajectory Score        -- 25%                    |
|      * Product-company vs consulting-firm detection           |
|      * Career progression quality                             |
|      * Production deployment signals in descriptions          |
|                                                               |
|  (3) Experience Fit Score           -- 15%                    |
|      * Years vs 5-9 year range (sweet spot: 6-8)              |
|                                                               |
|  (4) Behavioral Signals Score       -- 15%                    |
|      * Recruiter response rate, recent activity               |
|      * Open to work, interview completion, notice period      |
|                                                               |
|  (5) Location & Logistics           -- 5%                     |
|      * India-based, Tier-1 cities, relocation willingness     |
|                                                               |
|  (6) Education & Credentials        -- 5%                     |
|      * Institution tier, field relevance, certifications      |
|                                                               |
|  (7) Anti-Pattern Penalty (multiplicative)                    |
|      * Consulting-only career penalty                         |
|      * Keyword-stuffer detection                              |
|      * Title-chaser pattern detection                         |
|      * CV/Speech/Robotics without NLP/IR penalty              |
+----------+----------------------------------------------------+
           |
           v
+----------------------------+
|  4. Rank & Select Top 100  |  Sort by final_score desc, tiebreak by ID
+----------+-----------------+
           |
           v
+----------------------------+
|  5. Reasoning Generator    |  Fact-based, per-candidate, no hallucination
+----------+-----------------+
           |
           v
+----------------------------+
|  6. CSV Output & Validate  |  submission.csv + format validation
+----------------------------+
```

### Why This Works Better Than Keyword Matching

| Keyword Filter | This System |
|---|---|
| Sees "Python" or not | Understands depth of Python usage via proficiency + duration |
| Misses implicit skills | Reads career descriptions for production ML signals |
| No context about seniority | Aligns candidate level to 5-9 year ideal range |
| No reasoning | Explains WHY each candidate is ranked with profile-specific facts |
| Fooled by keyword stuffers | Detects skill-list-vs-career mismatch, penalizes heavily |
| Ignores availability | Weighs behavioral signals (response rate, activity, notice period) |
| Ranks honeypots highly | Detects impossible profiles (zero-duration expert skills, timeline anomalies) |

---

## Quick Start

### 1. Prerequisites

- Python 3.10+ (standard library only — no external packages required)
- The `candidates.jsonl` file from the challenge bundle

### 2. Run the ranker

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

### 3. Validate the submission

```bash
python validate_submission.py submission.csv
```

### 4. Options

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv --verbose
```

### 5. Run the Sandbox UI Locally

If you'd like to test the sandbox app locally before deploying or submitting:

1. Install sandbox dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the Gradio app:
   ```bash
   python app.py
   ```
3. Open `http://127.0.0.1:7860` in your web browser to interact with the premium UI.

---

## Project Structure

```
ai_recruiter/
├── rank.py                    # CLI entry point (main command)
├── app.py                     # Gradio web app (Hugging Face Space sandbox entrypoint)
├── config.py                  # Scoring weights, thresholds, constants
├── jd_requirements.py         # Hardcoded JD analysis, skill dictionaries
├── data_loader.py             # JSONL/JSON stream parser, feature normalization
├── honeypot_detector.py       # Impossible profile detection
├── scorer.py                  # 7-component scoring engine
├── reasoning_generator.py     # Per-candidate reasoning generation
├── output_writer.py           # CSV output + format validation
├── requirements.txt           # Dependencies (Gradio & Pandas for sandbox)
├── submission_metadata.yaml   # Submission metadata template
├── sample_candidates.json     # Pre-loaded 300KB dataset for sandbox demo
└── README.md
```

---

## Compute Constraints (all satisfied)

| Constraint | Limit | Our System |
|---|---|---|
| Runtime | ≤ 5 minutes | ~60-90 seconds |
| Memory | ≤ 16 GB RAM | ~2 GB peak |
| Compute | CPU only | Pure Python, no GPU |
| Network | Off | Zero API calls |
| Disk | ≤ 5 GB | ~10 MB output |

---

## Design Decisions

- **No LLM calls** — The competition explicitly forbids network calls during ranking. Our scoring is 100% local, deterministic, and fast.
- **7-component weighted scoring** — Each dimension captures a different aspect of candidate fit, avoiding over-reliance on any single signal.
- **Multiplicative anti-pattern penalties** — Instead of just boosting good candidates, we actively penalize candidates the JD explicitly says NOT to hire (consulting-only careers, keyword stuffers, inactive candidates).
- **Honeypot detection** — Conservative detection of impossible profiles using 5 independent heuristics (impossible skill claims, assessment contradictions, timeline anomalies, endorsement anomalies, completeness paradoxes).
- **Career description NLP** — We don't just look at skill lists; we analyze career descriptions for production ML keywords (deployed, at scale, latency, A/B testing) to distinguish real practitioners from keyword listers.
- **Fact-grounded reasoning** — Every reasoning sentence references actual profile data. No hallucination. Tone matches rank position.

---

## Methodology Summary

Rule-based ranker with explicit reasoning capture. Seven scoring components (skills match, career trajectory, experience fit, behavioral signals, location, education, anti-pattern bonus) combined with multiplicative anti-pattern penalties. The career-trajectory component is the decisive signal against keyword-stuffer traps; skill-proficiency-duration-endorsement triangulation catches lazy keyword stuffing. Honeypot detection uses 5 independent heuristics for impossible profiles. Runtime is ~60-90 seconds for 100K candidates on CPU.
