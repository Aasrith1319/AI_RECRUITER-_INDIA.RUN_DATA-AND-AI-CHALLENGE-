"""
Output Writer for Redrob Hackathon AI Recruiter.

Writes the final submission CSV with:
- Header: candidate_id,rank,score,reasoning
- Exactly 100 rows, ranks 1-100
- Non-increasing scores with tie-breaking on candidate_id (ascending)
- 4 decimal place score formatting
- Proper CSV escaping (reasoning may contain commas/quotes)
- UTF-8 encoding
"""

import csv
import os
from typing import List


def write_submission_csv(ranked_candidates: list, output_path: str) -> None:
    """
    Write the submission CSV file.

    ranked_candidates: list of dicts, already sorted by score descending, each with:
        - candidate_id (str or int)
        - score (float)
        - reasoning (str)
    output_path: path to write CSV

    The function handles:
    1. Re-sorting with tie-breaking (score desc, then candidate_id asc)
    2. Truncation to exactly 100 rows
    3. Score formatting to 4 decimal places
    4. Proper CSV escaping of reasoning text
    """
    if not ranked_candidates:
        raise ValueError("ranked_candidates is empty — nothing to write.")

    # ---- Step 1: Sort with tie-breaking ----
    # Primary: score descending. Secondary: candidate_id ascending (for ties).
    sorted_candidates = sorted(
        ranked_candidates,
        key=lambda c: (-c["score"], str(c["candidate_id"]))
    )

    # ---- Step 2: Take top 100 ----
    top_100 = sorted_candidates[:100]

    if len(top_100) < 100:
        print(f"WARNING: Only {len(top_100)} candidates available, expected 100.")

    # ---- Step 3: Ensure output directory exists ----
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # ---- Step 4: Write CSV ----
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

        # Header
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        # Data rows
        for rank_idx, cand in enumerate(top_100, start=1):
            candidate_id = cand["candidate_id"]
            score = cand["score"]
            reasoning = cand.get("reasoning", "")

            # Clean reasoning: collapse newlines, strip excess whitespace
            reasoning = " ".join(reasoning.split())

            # Format score to 4 decimal places
            score_str = f"{score:.4f}"

            writer.writerow([candidate_id, rank_idx, score_str, reasoning])

    print(f"Submission CSV written: {output_path} ({len(top_100)} candidates)")


def validate_output(output_path: str) -> List[str]:
    """
    Run comprehensive validation checks on the submission CSV.
    Returns list of error strings (empty list if fully valid).
    """
    errors = []

    # ---- Check file exists ----
    if not os.path.exists(output_path):
        errors.append(f"File does not exist: {output_path}")
        return errors

    # ---- Read and parse ----
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception as e:
        errors.append(f"Failed to read CSV: {e}")
        return errors

    # ---- Check header ----
    if not rows:
        errors.append("CSV file is empty.")
        return errors

    header = rows[0]
    expected_header = ["candidate_id", "rank", "score", "reasoning"]
    if header != expected_header:
        errors.append(f"Header mismatch. Expected {expected_header}, got {header}")

    data_rows = rows[1:]

    # ---- Check row count ----
    if len(data_rows) != 100:
        errors.append(f"Expected exactly 100 data rows, found {len(data_rows)}.")

    # ---- Parse and validate each row ----
    seen_ranks = set()
    seen_ids = set()
    prev_score = float("inf")
    prev_id = ""

    for i, row in enumerate(data_rows):
        row_num = i + 2  # 1-indexed, accounting for header

        if len(row) < 4:
            errors.append(f"Row {row_num}: Expected at least 4 columns, got {len(row)}.")
            continue

        candidate_id, rank_str, score_str, reasoning = row[0], row[1], row[2], row[3]

        # Validate candidate_id
        if not candidate_id.strip():
            errors.append(f"Row {row_num}: Empty candidate_id.")

        # Check for duplicate candidate_ids
        if candidate_id in seen_ids:
            errors.append(f"Row {row_num}: Duplicate candidate_id '{candidate_id}'.")
        seen_ids.add(candidate_id)

        # Validate rank
        try:
            rank_val = int(rank_str)
            expected_rank = i + 1
            if rank_val != expected_rank:
                errors.append(f"Row {row_num}: Rank is {rank_val}, expected {expected_rank}.")
            if rank_val in seen_ranks:
                errors.append(f"Row {row_num}: Duplicate rank {rank_val}.")
            seen_ranks.add(rank_val)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid rank '{rank_str}' (not an integer).")

        # Validate score
        try:
            score_val = float(score_str)

            # Check 4 decimal places
            if "." in score_str:
                decimal_part = score_str.split(".")[1]
                if len(decimal_part) != 4:
                    errors.append(
                        f"Row {row_num}: Score '{score_str}' does not have exactly 4 decimal places."
                    )

            # Check non-increasing order
            if score_val > prev_score:
                errors.append(
                    f"Row {row_num}: Score {score_val} > previous score {prev_score} "
                    f"(scores must be non-increasing)."
                )

            # Check tie-breaking: if same score, candidate_id should be ascending
            if score_val == prev_score and candidate_id < prev_id:
                errors.append(
                    f"Row {row_num}: Tie-break violation. Score {score_val} tied with previous, "
                    f"but candidate_id '{candidate_id}' < '{prev_id}' (should be ascending)."
                )

            prev_score = score_val
            prev_id = candidate_id

        except ValueError:
            errors.append(f"Row {row_num}: Invalid score '{score_str}' (not a float).")

        # Validate reasoning
        if not reasoning.strip():
            errors.append(f"Row {row_num}: Empty reasoning for candidate '{candidate_id}'.")

    # ---- Check all ranks 1-100 present ----
    expected_ranks = set(range(1, 101))
    missing_ranks = expected_ranks - seen_ranks
    if missing_ranks and len(data_rows) == 100:
        errors.append(f"Missing ranks: {sorted(missing_ranks)}")

    # ---- Summary ----
    if not errors:
        print(f"Validation PASSED: {output_path}")
    else:
        print(f"Validation FAILED with {len(errors)} error(s): {output_path}")

    return errors
