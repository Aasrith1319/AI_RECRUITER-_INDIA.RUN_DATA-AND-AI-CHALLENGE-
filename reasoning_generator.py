"""
Reasoning Generator for Redrob Hackathon AI Recruiter.

Generates specific, fact-based 1-2 sentence justifications for each top-100 candidate.
Every claim maps to actual profile data — no hallucination.
Tone adapts to rank tier (top-10 praise, mid-range balanced, bottom-10 honest limitations).
"""

# ---------------------------------------------------------------------------
# JD constants (Senior AI Engineer — Founding Team, Redrob AI)
# ---------------------------------------------------------------------------
MUST_HAVE_SKILLS = {
    "embeddings", "embedding", "retrieval", "vector database", "vector db",
    "pinecone", "weaviate", "qdrant", "milvus", "faiss", "elasticsearch",
    "ndcg", "mrr", "map", "ranking", "learning to rank", "ltr",
    "python", "information retrieval",
}

NICE_TO_HAVE_SKILLS = {
    "llm", "large language model", "fine-tuning", "fine tuning",
    "lora", "qlora", "peft", "rlhf",
    "distributed systems", "kubernetes", "docker",
    "nlp", "natural language processing", "transformers", "bert", "gpt",
    "tensorflow", "pytorch", "torch",
    "open source", "open-source",
    "hr tech", "hr-tech", "talent", "recruiting",
}

PREFERRED_LOCATIONS = {"pune", "noida"}
GOOD_LOCATIONS = {"bangalore", "bengaluru", "hyderabad", "mumbai", "delhi", "gurgaon", "gurugram", "chennai"}

IDEAL_EXP_MIN = 5.0
IDEAL_EXP_MAX = 9.0


# ---------------------------------------------------------------------------
# Helper: safe getters
# ---------------------------------------------------------------------------

def _safe_get(d: dict, *keys, default=None):
    """Nested safe dict access."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            return default
    return cur if cur is not None else default


def _fmt(val, decimals=1) -> str:
    """Format a number for display."""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


# ---------------------------------------------------------------------------
# Fragment builders — each returns a string fragment or empty string
# ---------------------------------------------------------------------------

def _title_and_experience_fragment(candidate: dict) -> str:
    """e.g. 'Senior ML Engineer with 7.2 years'"""
    title = candidate.get("current_title", "")
    yoe = candidate.get("years_of_experience")
    if title and yoe is not None:
        return f"{title} with {_fmt(yoe)} years"
    if title:
        return title
    if yoe is not None:
        return f"Professional with {_fmt(yoe)} years of experience"
    return "Candidate"


def _company_context_fragment(candidate: dict) -> str:
    """e.g. 'at a mid-size product company' or 'at TechCorp (Series B startup)'"""
    company = candidate.get("current_company", "")
    size = candidate.get("current_company_size", "")
    industry = candidate.get("current_industry", "")

    parts = []
    if company:
        parts.append(f"at {company}")
    if size:
        parts.append(f"({size})")
    elif industry:
        parts.append(f"in {industry}")
    return " ".join(parts)


def _matched_skills_fragment(candidate: dict) -> str:
    """Identifies which JD-critical skills the candidate actually has."""
    skills = candidate.get("skills", [])
    if not skills:
        return ""

    skill_names_lower = set()
    for s in skills:
        name = s if isinstance(s, str) else (s.get("name", "") if isinstance(s, dict) else "")
        skill_names_lower.add(name.lower().strip())

    must_hits = []
    nice_hits = []
    for sn in skill_names_lower:
        for mh in MUST_HAVE_SKILLS:
            if mh in sn or sn in mh:
                # Use original-cased name for display
                display = _find_original_skill_name(candidate, sn)
                if display and display not in must_hits:
                    must_hits.append(display)
                break
        else:
            for nh in NICE_TO_HAVE_SKILLS:
                if nh in sn or sn in nh:
                    display = _find_original_skill_name(candidate, sn)
                    if display and display not in nice_hits:
                        nice_hits.append(display)
                    break

    # Keep it concise: top 3-4 must-have, top 2 nice-to-have
    must_hits = must_hits[:4]
    nice_hits = nice_hits[:2]

    if must_hits and nice_hits:
        return f"strong {', '.join(must_hits)} experience plus {', '.join(nice_hits)}"
    if must_hits:
        return f"strong {', '.join(must_hits)} experience"
    if nice_hits:
        return f"relevant {', '.join(nice_hits)} background"
    return ""


def _find_original_skill_name(candidate: dict, lower_name: str) -> str:
    """Recover the original-cased skill name for display."""
    skills = candidate.get("skills", [])
    for s in skills:
        if isinstance(s, str):
            if s.lower().strip() == lower_name:
                return s.strip()
        elif isinstance(s, dict):
            n = s.get("name", "")
            if n.lower().strip() == lower_name:
                return n.strip()
    return lower_name.title()


def _career_highlight_fragment(candidate: dict) -> str:
    """Pull the most relevant career detail — product company history, retrieval work, etc."""
    career = candidate.get("career_history", [])
    if not career:
        return ""

    # Count product-company stints
    product_stints = 0
    retrieval_mention = False
    longest_role = None
    longest_dur = 0

    for role in career:
        desc = (role.get("description") or "").lower()
        dur = role.get("duration_months") or 0

        # Track longest role
        if dur > longest_dur:
            longest_dur = dur
            longest_role = role

        # Check for retrieval / embedding / vector mentions in descriptions
        for kw in ("retrieval", "embedding", "vector", "search", "ranking", "faiss", "pinecone"):
            if kw in desc:
                retrieval_mention = True
                break

        # Heuristic: non-consulting companies
        company = (role.get("company") or "").lower()
        consulting_flags = {"tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
                            "deloitte", "consulting", "services"}
        if not any(cf in company for cf in consulting_flags):
            product_stints += 1

    fragments = []
    if retrieval_mention:
        fragments.append("building retrieval systems at product companies")
    elif product_stints >= 2:
        fragments.append(f"across {product_stints} product-company roles")
    elif longest_role:
        co = longest_role.get("company", "")
        title = longest_role.get("title", "")
        dur_y = longest_dur / 12
        if co and dur_y >= 1:
            fragments.append(f"including {_fmt(dur_y)} years as {title} at {co}" if title else
                             f"including {_fmt(dur_y)} years at {co}")

    return "; ".join(fragments)


def _location_fragment(candidate: dict) -> str:
    """e.g. 'Pune-based' or 'currently in Bangalore with willingness to relocate'"""
    loc = (candidate.get("location") or "").strip()
    country = (candidate.get("country") or "").strip()
    willing = candidate.get("willing_to_relocate")
    loc_lower = loc.lower()

    for p in PREFERRED_LOCATIONS:
        if p in loc_lower:
            return f"{loc}-based"

    for g in GOOD_LOCATIONS:
        if g in loc_lower:
            if willing:
                return f"currently in {loc} with willingness to relocate"
            return f"based in {loc}"

    if loc and country:
        if willing:
            return f"located in {loc}, {country} (willing to relocate)"
        return f"located in {loc}, {country}"
    if loc:
        if willing:
            return f"located in {loc} (willing to relocate)"
        return f"located in {loc}"
    return ""


def _behavioral_fragment(candidate: dict) -> str:
    """Behavioral signals: response rate, open-to-work, activity."""
    parts = []
    rr = candidate.get("recruiter_response_rate")
    otw = candidate.get("open_to_work_flag")
    last_active = candidate.get("last_active_date", "")
    notice = candidate.get("notice_period_days")
    github = candidate.get("github_activity_score")
    interview_rate = candidate.get("interview_completion_rate")

    if rr is not None:
        if rr >= 0.8:
            pct = int(rr * 100)
            parts.append(f"{pct}% recruiter response rate")
        elif rr >= 0.5:
            parts.append(f"moderate response rate ({_fmt(rr, 2)})")
        elif rr < 0.3:
            parts.append(f"low response rate ({_fmt(rr, 2)})")

    if otw is True:
        parts.append("open to work")

    if github is not None and github > 0.7:
        parts.append(f"active GitHub (score {_fmt(github, 2)})")

    if interview_rate is not None and interview_rate >= 0.9:
        parts.append(f"strong interview completion ({_fmt(interview_rate, 2)})")

    return ", ".join(parts)


def _concern_fragment(candidate: dict, score_breakdown: dict) -> str:
    """Honestly surface gaps/concerns."""
    concerns = []

    # Notice period
    notice = candidate.get("notice_period_days")
    if notice is not None and notice > 30:
        concerns.append(f"notice period ({notice} days)")
    elif notice is not None and notice > 60:
        concerns.append(f"extended notice period ({notice} days)")

    # Experience outside ideal range
    yoe = candidate.get("years_of_experience")
    if yoe is not None:
        if yoe < IDEAL_EXP_MIN:
            concerns.append(f"experience below ideal range ({_fmt(yoe)} years)")
        elif yoe > IDEAL_EXP_MAX:
            concerns.append(f"over-experienced vs. ideal range ({_fmt(yoe)} years)")

    # Low skills score
    skills_score = score_breakdown.get("skills_score", 1.0)
    if skills_score < 0.3:
        concerns.append("limited production retrieval experience")
    elif skills_score < 0.5:
        concerns.append("partial overlap with must-have skill requirements")

    # Low behavioral score
    behavioral = score_breakdown.get("behavioral_score", 1.0)
    if behavioral < 0.3:
        concerns.append("weak behavioral signals")

    # Penalty factor
    penalty = score_breakdown.get("penalty_factor", 1.0)
    if penalty < 0.8:
        concerns.append("consulting-heavy background")

    # Response rate
    rr = candidate.get("recruiter_response_rate")
    if rr is not None and rr < 0.3:
        if "low response rate" not in " ".join(concerns):
            concerns.append(f"low recruiter engagement ({_fmt(rr, 2)})")

    # Location
    loc = (candidate.get("location") or "").lower()
    country = (candidate.get("country") or "").lower()
    if country and "india" not in country:
        willing = candidate.get("willing_to_relocate")
        if not willing:
            concerns.append("international location without relocation willingness")

    return concerns


def _education_fragment(candidate: dict) -> str:
    """Brief education note for noteworthy backgrounds."""
    education = candidate.get("education", [])
    if not education:
        return ""

    for edu in education:
        tier = edu.get("tier", "")
        inst = edu.get("institution", "")
        degree = edu.get("degree", "")
        field = edu.get("field_of_study", "")

        if tier and ("tier 1" in str(tier).lower() or "tier_1" in str(tier).lower() or str(tier) == "1"):
            if inst:
                return f"{degree} from {inst}" if degree else f"educated at {inst}"

    return ""


# ---------------------------------------------------------------------------
# Tone calibration
# ---------------------------------------------------------------------------

def _get_tone_tier(rank: int) -> str:
    """Determine tone bucket based on rank."""
    if rank <= 10:
        return "top"
    if rank <= 30:
        return "strong"
    if rank <= 60:
        return "moderate"
    if rank <= 85:
        return "included"
    return "borderline"


def _opening_phrase(tone: str, rank: int) -> str:
    """Rank-appropriate opening connectors — varied to avoid repetition."""
    if tone == "top":
        options = [
            "Excellent match:",
            "Highly qualified:",
            "Outstanding fit:",
            "Top-tier candidate:",
            "Exceptional profile:",
        ]
    elif tone == "strong":
        options = [
            "Strong candidate:",
            "Well-qualified:",
            "Solid match:",
            "Competitive profile:",
        ]
    elif tone == "moderate":
        options = [
            "Competent match with notable strengths:",
            "Good potential:",
            "Relevant background:",
            "Reasonable fit:",
        ]
    elif tone == "included":
        options = [
            "Included based on select strengths:",
            "Partial match:",
            "Considered for:",
            "Relevant adjacent skills:",
        ]
    else:  # borderline
        options = [
            "Marginal inclusion:",
            "Borderline candidate:",
            "Included at threshold:",
            "Edge-case inclusion:",
        ]
    return options[rank % len(options)]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_reasoning(candidate: dict, rank: int, score: float, score_breakdown: dict) -> str:
    """
    Generate a 1-2 sentence reasoning for why this candidate is ranked here.

    candidate: the flat candidate dict (has all fields from data_loader)
    rank: 1-100
    score: final composite score
    score_breakdown: dict with keys like 'skills_score', 'career_score', 'experience_score',
                     'behavioral_score', 'location_score', 'education_score', 'penalty_factor'

    Returns a concise, fact-grounded justification string.
    """
    tone = _get_tone_tier(rank)

    # ---- Gather fragments ----
    title_exp = _title_and_experience_fragment(candidate)
    company_ctx = _company_context_fragment(candidate)
    skills_frag = _matched_skills_fragment(candidate)
    career_frag = _career_highlight_fragment(candidate)
    location_frag = _location_fragment(candidate)
    behavioral_frag = _behavioral_fragment(candidate)
    education_frag = _education_fragment(candidate)
    concerns = _concern_fragment(candidate, score_breakdown)

    # ---- Compose sentence 1: strengths ----
    strength_parts = []

    # Core identity
    core = title_exp
    if company_ctx:
        core += f" {company_ctx}"
    strength_parts.append(core)

    # Skills
    if skills_frag:
        strength_parts.append(skills_frag)

    # Career highlight (if adds new info)
    if career_frag and career_frag not in core:
        strength_parts.append(career_frag)

    # Education (only for top tiers or if noteworthy)
    if education_frag and tone in ("top", "strong"):
        strength_parts.append(education_frag)

    # Location
    if location_frag:
        strength_parts.append(location_frag)

    # Behavioral (top-tier: inline; others: only if strong)
    if behavioral_frag:
        if tone in ("top", "strong") or candidate.get("recruiter_response_rate", 0) >= 0.7:
            strength_parts.append(behavioral_frag)

    # Build sentence 1
    sentence1 = "; ".join(strength_parts) + "."

    # ---- Compose sentence 2: concerns / qualifiers ----
    sentence2 = ""
    if concerns:
        if tone in ("top", "strong"):
            # Mild qualifier
            if len(concerns) == 1:
                sentence2 = f" Minor concern on {concerns[0]}."
            else:
                sentence2 = f" Minor concerns: {', '.join(concerns[:3])}."
        elif tone == "moderate":
            sentence2 = f" Gaps noted: {', '.join(concerns[:3])}."
        else:
            # included / borderline: be direct
            if len(concerns) == 1:
                sentence2 = f" Key limitation: {concerns[0]}."
            else:
                sentence2 = f" Limitations: {', '.join(concerns[:3])}."
    elif tone in ("included", "borderline"):
        # Even if no explicit concerns, note the moderate score
        sentence2 = f" Included primarily on behavioral signals and adjacent skill relevance."

    # If both sentences are very short, append behavioral as bonus context
    combined = sentence1 + sentence2
    if len(combined) < 80 and behavioral_frag and behavioral_frag not in combined:
        combined = combined.rstrip(".") + f"; {behavioral_frag}."

    # Final cleanup: collapse double spaces, ensure single period at end
    combined = combined.replace("  ", " ").replace("..", ".").strip()

    return combined
