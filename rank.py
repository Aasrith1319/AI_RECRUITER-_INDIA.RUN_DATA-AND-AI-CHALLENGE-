#!/usr/bin/env python3
"""
rank.py
Main entry point for the Redrob Hackathon AI Candidate Ranking System.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Constraints:
    - Runs on CPU only, no GPU
    - 16 GB RAM max
    - 5 minutes wall-clock max
    - No network / no LLM API calls
"""

import argparse
import os
import sys
import time

# Fix Windows encoding issues
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from data_loader import load_all_candidates
from honeypot_detector import detect_honeypots
from scorer import score_all_candidates
from reasoning_generator import generate_reasoning
from output_writer import write_submission_csv, validate_output
from config import TOP_N, OUTPUT_FILE


def print_banner():
    print("""
================================================================
  AI Candidate Ranking System - Redrob Hackathon
  Senior AI Engineer - Founding Team
  100% Local Scoring | No LLM Calls | CPU Only
================================================================
    """)


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(
        description="AI Candidate Ranking System — ranks candidates for the Senior AI Engineer role at Redrob AI."
    )
    parser.add_argument(
        "--candidates",
        default="candidates.jsonl",
        help="Path to the candidates JSONL file (default: candidates.jsonl)"
    )
    parser.add_argument(
        "--out",
        default=OUTPUT_FILE,
        help=f"Output file path for ranked candidates CSV (default: {OUTPUT_FILE})"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=TOP_N,
        help=f"Number of top candidates to output (default: {TOP_N})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed scoring info for top candidates"
    )
    args = parser.parse_args()

    print_banner()

    # ── Step 0: Validate input ──
    if not os.path.exists(args.candidates):
        print(f"❌ Candidates file not found: {args.candidates}")
        sys.exit(1)

    # ── Step 1: Load candidates ──
    print("📂 Loading candidates...")
    t1 = time.time()
    candidates = load_all_candidates(args.candidates)
    print(f"   ✅ Loaded {len(candidates)} candidates in {time.time()-t1:.1f}s")

    # ── Step 2: Detect honeypots ──
    print("\n🔍 Detecting honeypot candidates...")
    t2 = time.time()
    honeypot_ids = detect_honeypots(candidates)
    print(f"   ✅ Flagged {len(honeypot_ids)} potential honeypots in {time.time()-t2:.1f}s")
    if honeypot_ids and len(honeypot_ids) <= 20:
        print(f"   🍯 IDs: {', '.join(sorted(list(honeypot_ids))[:10])}{'...' if len(honeypot_ids) > 10 else ''}")

    # ── Step 3: Score all candidates ──
    print(f"\n📊 Scoring {len(candidates)} candidates across 7 dimensions...")
    t3 = time.time()
    scored = score_all_candidates(candidates, honeypot_ids)
    print(f"   ✅ Scoring complete in {time.time()-t3:.1f}s")

    # ── Step 4: Select top N ──
    top_n = min(args.top_n, len(scored))
    top_candidates = scored[:top_n]
    print(f"\n🏆 Selected top {top_n} candidates")

    # Verify no honeypots in top 100
    top_honeypots = [c for c in top_candidates if c["candidate_id"] in honeypot_ids]
    if top_honeypots:
        print(f"   ⚠️  WARNING: {len(top_honeypots)} honeypot(s) in top {top_n}!")
        for h in top_honeypots:
            print(f"      🍯 {h['candidate_id']} (score: {h['score']:.4f})")
    else:
        print(f"   ✅ No honeypots in top {top_n}")

    # ── Step 5: Generate reasoning ──
    print(f"\n💬 Generating reasoning for {top_n} candidates...")
    t5 = time.time()
    output_candidates = []
    for i, c in enumerate(top_candidates):
        rank = i + 1
        reasoning = generate_reasoning(c, rank, c["score"], c.get("breakdown", {}))
        output_candidates.append({
            "candidate_id": c["candidate_id"],
            "score": c["score"],
            "reasoning": reasoning,
        })
    print(f"   ✅ Reasoning generated in {time.time()-t5:.1f}s")

    # ── Step 6: Write submission CSV ──
    print(f"\n📄 Writing submission to: {args.out}")
    write_submission_csv(output_candidates, args.out)

    # ── Step 7: Validate ──
    print("\n🔍 Validating submission format...")
    errors = validate_output(args.out)
    if errors:
        print(f"   ❌ Validation errors:")
        for e in errors:
            print(f"      - {e}")
    else:
        print(f"   ✅ Submission format is valid!")

    # ── Step 8: Print summary ──
    elapsed = time.time() - start_time
    print(f"\n{'='*65}")
    print(f"  🏆  TOP 10 CANDIDATES")
    print(f"{'='*65}")
    for c in top_candidates[:10]:
        bd = c.get("breakdown", {})
        title = c.get("current_title", "N/A")
        years = c.get("years_of_experience", 0)
        loc = c.get("location", "")
        name = c.get("name", "")
        ap = bd.get("anti_patterns", [])

        print(f"\n  #{top_candidates.index(c)+1}  {name}")
        print(f"      {title} | {years} yrs | {loc}")
        print(f"      Score: {c['score']:.4f}  "
              f"[Skills: {bd.get('skills_score', 0):.2f}  "
              f"Career: {bd.get('career_score', 0):.2f}  "
              f"Exp: {bd.get('experience_score', 0):.2f}  "
              f"Behav: {bd.get('behavioral_score', 0):.2f}  "
              f"Penalty: {bd.get('penalty_factor', 1):.2f}]")
        if ap:
            print(f"      ⚠️  Flags: {', '.join(ap)}")
    print(f"\n{'='*65}")

    if args.verbose:
        print(f"\n  Top 100 score range: {top_candidates[0]['score']:.4f} → {top_candidates[-1]['score']:.4f}")
        print(f"  Median score (top 100): {top_candidates[49]['score']:.4f}")

        # Title distribution in top 100
        from collections import Counter
        title_dist = Counter(c.get("current_title", "Unknown") for c in top_candidates)
        print(f"\n  Title distribution in top 100:")
        for title, count in title_dist.most_common(10):
            print(f"    {title}: {count}")

    print(f"\n⏱️  Total time: {elapsed:.1f}s")
    print(f"📄 Output: {args.out}")
    print(f"✅ Done!")


if __name__ == "__main__":
    main()
