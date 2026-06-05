"""
scorer.py
Multi-dimensional scoring engine for the Redrob Hackathon.
7 scoring components + multiplicative anti-pattern penalties.

All scoring is local, deterministic, and fast.
No LLM calls. No network. CPU-only.
"""

import re
from datetime import datetime, date
from config import (
    SCORING_WEIGHTS, PENALTIES,
    IDEAL_EXPERIENCE_MIN, IDEAL_EXPERIENCE_MAX,
    SWEET_SPOT_MIN, SWEET_SPOT_MAX,
    ABSOLUTE_MIN_EXPERIENCE,
    HIGH_RESPONSE_RATE, LOW_RESPONSE_RATE,
    SHORT_NOTICE_DAYS, LONG_NOTICE_DAYS,
    RECENT_ACTIVITY_DAYS, STALE_ACTIVITY_DAYS,
)
from jd_requirements import (
    MUST_HAVE_SKILLS, NICE_TO_HAVE_SKILLS, AI_CORE_SKILLS,
    SKILL_SYNONYMS,
    HIGHLY_RELEVANT_TITLES, SOMEWHAT_RELEVANT_TITLES, IRRELEVANT_TITLES,
    CONSULTING_FIRMS, NOTABLE_PRODUCT_COMPANIES,
    PREFERRED_CITIES, TIER1_INDIAN_CITIES,
    CV_SPEECH_ROBOTICS_SKILLS, NLP_IR_SKILLS,
    PRODUCTION_KEYWORDS,
    RELEVANT_EDUCATION_FIELDS, IRRELEVANT_EDUCATION_FIELDS,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_skill(name: str) -> str:
    """Normalize a skill name for matching."""
    name = name.lower().strip()
    return SKILL_SYNONYMS.get(name, name)


# Compile regexes for skills/keywords to check with word boundaries (especially short ones)
_SHORT_SKILL_PATTERNS = {}
for s in MUST_HAVE_SKILLS.union(NICE_TO_HAVE_SKILLS).union(AI_CORE_SKILLS):
    if len(s) <= 4:
        _SHORT_SKILL_PATTERNS[s] = re.compile(r"\b" + re.escape(s) + r"\b")

def _has_skill_in_text(skill: str, text: str) -> bool:
    """Check if skill is in text, using word boundaries for short skills/acronyms."""
    if skill not in text:
        return False
    if skill in _SHORT_SKILL_PATTERNS:
        return bool(_SHORT_SKILL_PATTERNS[skill].search(text))
    return True

def _text_contains_any(text: str, keywords: set) -> list[str]:
    """Return which keywords are found in the text with word boundaries for short ones."""
    text_lower = text.lower()
    found = []
    for kw in keywords:
        if kw not in text_lower:
            continue
        if len(kw) <= 4:
            pattern = _SHORT_SKILL_PATTERNS.get(kw)
            if not pattern:
                pattern = re.compile(r"\b" + re.escape(kw) + r"\b")
            if pattern.search(text_lower):
                found.append(kw)
        else:
            found.append(kw)
    return found


def _is_consulting_firm(company: str) -> bool:
    """Check if a company is a known consulting/services firm."""
    company_lower = company.lower().strip()
    for firm in CONSULTING_FIRMS:
        if firm in company_lower or company_lower in firm:
            return True
    return False


def _is_product_company(company: str) -> bool:
    """Check if a company is a known product company."""
    company_lower = company.lower().strip()
    for co in NOTABLE_PRODUCT_COMPANIES:
        if co in company_lower or company_lower in co:
            return True
    return False


def _title_relevance(title: str) -> float:
    """Score 0-1 for how relevant a job title is to this role."""
    title_lower = title.lower().strip()
    
    # Check for junior/intern prefixes
    is_junior = any(w in title_lower for w in ["junior", "jr", "intern", "associate", "trainee", "fresher", "student", "graduate"])
    if "associate" in title_lower and any(w in title_lower for w in ["director", "partner", "professor", "architect", "lead"]):
        is_junior = False

    for t in HIGHLY_RELEVANT_TITLES:
        if t in title_lower:
            return 0.40 if is_junior else 1.0
    for t in SOMEWHAT_RELEVANT_TITLES:
        if t in title_lower:
            return 0.20 if is_junior else 0.5
    for t in IRRELEVANT_TITLES:
        if t in title_lower:
            return 0.0
    return 0.10 if is_junior else 0.25  # Unknown title


def _days_since(date_str: str) -> int:
    """Calculate days since a date string (YYYY-MM-DD)."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (date.today() - d).days
    except (ValueError, TypeError):
        return 9999  # Unknown = treat as very old


def _parse_location(location: str, country: str) -> tuple[bool, bool, bool]:
    """
    Returns (is_india, is_preferred_city, is_tier1_city).
    """
    loc_lower = (location or "").lower().strip()
    country_lower = (country or "").lower().strip()

    is_india = country_lower == "india" or any(
        city in loc_lower for city in TIER1_INDIAN_CITIES
    )

    is_preferred = any(city in loc_lower for city in PREFERRED_CITIES)
    is_tier1 = any(city in loc_lower for city in TIER1_INDIAN_CITIES)

    return is_india, is_preferred, is_tier1


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 1: Technical Skills Match (25%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_skills_match(candidate: dict) -> tuple[float, dict]:
    """
    Score technical skill coverage against JD requirements.
    Returns (score 0-1, details dict).
    """
    skill_names = set(candidate.get("skill_names", []))
    skill_details = candidate.get("skill_details", {})
    all_text = candidate.get("all_text", "")
    career_text = candidate.get("career_descriptions_text", "")

    # Normalize skill names
    normalized_skills = set()
    for s in skill_names:
        normalized_skills.add(_normalize_skill(s))
    # Also check all_text for keywords
    combined_text = all_text + " " + career_text

    # Count must-have skills found
    must_have_found = []
    for skill in MUST_HAVE_SKILLS:
        if skill in normalized_skills or _has_skill_in_text(skill, combined_text):
            must_have_found.append(skill)

    # Deduplicate by canonical form
    must_have_unique = set()
    for s in must_have_found:
        canonical = _normalize_skill(s)
        must_have_unique.add(canonical)

    # Count nice-to-have skills found
    nice_to_have_found = []
    for skill in NICE_TO_HAVE_SKILLS:
        if skill in normalized_skills or _has_skill_in_text(skill, combined_text):
            nice_to_have_found.append(skill)

    nice_to_have_unique = set()
    for s in nice_to_have_found:
        canonical = _normalize_skill(s)
        nice_to_have_unique.add(canonical)

    # Calculate proficiency-weighted score for listed skills
    proficiency_weights = {"expert": 1.0, "advanced": 0.8, "intermediate": 0.5, "beginner": 0.2}
    prof_score = 0.0
    ai_skill_count = 0
    for sname in skill_names:
        norm = _normalize_skill(sname)
        if norm in AI_CORE_SKILLS or sname in AI_CORE_SKILLS:
            ai_skill_count += 1
            details = skill_details.get(sname, {})
            prof = details.get("proficiency", "beginner")
            duration = details.get("duration_months", 0)
            endorsements = details.get("endorsements", 0)

            # Weight by proficiency
            w = proficiency_weights.get(prof, 0.2)
            # Duration bonus (more months = more credible)
            dur_mult = min(1.0, duration / 36)  # 3 years = full credit
            # Endorsement bonus
            end_mult = min(1.0, 0.5 + endorsements / 40)

            prof_score += w * dur_mult * end_mult

    # Skill assessment scores from Redrob platform
    assessment_scores = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    assessment_bonus = 0.0
    if assessment_scores:
        relevant_assessments = []
        for skill_name, score in assessment_scores.items():
            norm = _normalize_skill(skill_name.lower())
            if norm in AI_CORE_SKILLS or skill_name.lower() in AI_CORE_SKILLS:
                relevant_assessments.append(score)
        if relevant_assessments:
            avg_assessment = sum(relevant_assessments) / len(relevant_assessments)
            assessment_bonus = (avg_assessment / 100) * 0.15  # Up to 0.15 bonus

    # Compose final score
    # Must-have coverage is the primary driver
    must_have_coverage = min(1.0, len(must_have_unique) / 8)  # 8 unique must-have categories is full
    nice_to_have_coverage = min(1.0, len(nice_to_have_unique) / 5) * 0.2  # 20% bonus

    # Proficiency depth
    prof_depth = min(0.2, prof_score / 10)  # Normalize, cap at 0.2

    score = min(1.0, must_have_coverage * 0.55 + nice_to_have_coverage + prof_depth + assessment_bonus)

    details = {
        "must_have_found": len(must_have_unique),
        "nice_to_have_found": len(nice_to_have_unique),
        "ai_skill_count": ai_skill_count,
        "assessment_bonus": round(assessment_bonus, 3),
    }

    return round(score, 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 2: Career Trajectory (25%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_career_trajectory(candidate: dict) -> tuple[float, dict]:
    """
    Evaluate career history for relevance, progression, and quality.
    Checks: product vs consulting, role relevance, production deployment signals.
    """
    career = candidate.get("career_history", [])
    if not career:
        return 0.0, {"reason": "no_career_history"}

    career_text = candidate.get("career_descriptions_text", "")

    # 1. Company type analysis
    total_months = 0
    consulting_months = 0
    product_months = 0
    relevant_role_months = 0
    highly_relevant_months = 0
    companies = set()

    for job in career:
        company = job.get("company", "")
        title = job.get("title", "")
        duration = job.get("duration_months", 0)
        companies.add(company.lower().strip())

        total_months += duration

        if _is_consulting_firm(company):
            consulting_months += duration
        elif _is_product_company(company):
            product_months += duration

        relevance = _title_relevance(title)
        if relevance >= 0.8:
            highly_relevant_months += duration
        if relevance >= 0.4:
            relevant_role_months += duration

    # 2. Production deployment signals in career descriptions
    production_signals = _text_contains_any(career_text, PRODUCTION_KEYWORDS)
    production_density = min(1.0, len(production_signals) / 8)

    # 3. Career progression quality
    titles = [job.get("title", "") for job in career]
    has_progression = len(set(titles)) > 1  # Not same title everywhere

    # 4. Company diversity (not stuck at one place)
    company_diversity = min(1.0, len(companies) / 3)

    # 5. Current role relevance (heavily weighted)
    current_title = candidate.get("current_title", "")
    current_relevance = _title_relevance(current_title)

    # Compose score
    # Product company experience
    if total_months > 0:
        product_ratio = product_months / total_months
        consulting_ratio = consulting_months / total_months
        relevant_ratio = relevant_role_months / total_months
    else:
        product_ratio = 0
        consulting_ratio = 0
        relevant_ratio = 0

    score = 0.0
    score += current_relevance * 0.30            # Current role is crucial
    score += relevant_ratio * 0.20               # Time in relevant roles
    score += production_density * 0.20           # Production experience signals
    score += product_ratio * 0.10                # Product company time
    score += company_diversity * 0.05            # Diverse experience
    score += (0.10 if has_progression else 0.0)  # Career progression
    score += min(0.05, highly_relevant_months / 120 * 0.05)  # Deep relevant experience

    # Penalties
    if consulting_ratio > 0.90:
        score *= 0.15  # Almost entirely consulting

    score = min(1.0, max(0.0, score))

    details = {
        "current_title_relevance": current_relevance,
        "product_ratio": round(product_ratio, 2),
        "consulting_ratio": round(consulting_ratio, 2),
        "production_signals": len(production_signals),
        "relevant_months": relevant_role_months,
    }

    return round(score, 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 3: Experience Fit (15%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_experience_fit(candidate: dict) -> tuple[float, dict]:
    """
    Score experience years against the 5-9 year ideal range.
    Sweet spot: 6-8 years.
    """
    years = candidate.get("years_of_experience", 0)

    if years < ABSOLUTE_MIN_EXPERIENCE:
        score = 0.05  # Very unlikely but don't zero out entirely
    elif SWEET_SPOT_MIN <= years <= SWEET_SPOT_MAX:
        score = 1.0  # Perfect sweet spot
    elif IDEAL_EXPERIENCE_MIN <= years <= IDEAL_EXPERIENCE_MAX:
        # Good range, slight discount outside sweet spot
        if years < SWEET_SPOT_MIN:
            score = 0.80 + 0.20 * (years - IDEAL_EXPERIENCE_MIN) / (SWEET_SPOT_MIN - IDEAL_EXPERIENCE_MIN)
        else:
            score = 0.80 + 0.20 * (IDEAL_EXPERIENCE_MAX - years) / (IDEAL_EXPERIENCE_MAX - SWEET_SPOT_MAX)
    elif years < IDEAL_EXPERIENCE_MIN:
        # Under-experienced but possible
        score = max(0.10, 0.70 * years / IDEAL_EXPERIENCE_MIN)
    else:
        # Over-experienced — the JD says 5-9 but signals are strong they want doers
        # 10-12 is still OK, beyond 12 gets more penalized
        overshoot = years - IDEAL_EXPERIENCE_MAX
        score = max(0.20, 0.75 - overshoot * 0.05)

    details = {
        "years": years,
        "in_sweet_spot": SWEET_SPOT_MIN <= years <= SWEET_SPOT_MAX,
        "in_ideal_range": IDEAL_EXPERIENCE_MIN <= years <= IDEAL_EXPERIENCE_MAX,
    }

    return round(score, 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 4: Behavioral Signals (15%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_behavioral_signals(candidate: dict) -> tuple[float, dict]:
    """
    Score Redrob platform behavioral signals.
    These indicate actual availability and responsiveness.
    """
    signals = candidate.get("redrob_signals", {})

    # 1. Recruiter response rate (very important per JD)
    response_rate = signals.get("recruiter_response_rate", 0)
    if response_rate >= HIGH_RESPONSE_RATE:
        response_score = 1.0
    elif response_rate >= LOW_RESPONSE_RATE:
        response_score = 0.3 + 0.7 * (response_rate - LOW_RESPONSE_RATE) / (HIGH_RESPONSE_RATE - LOW_RESPONSE_RATE)
    else:
        response_score = response_rate / LOW_RESPONSE_RATE * 0.3

    # 2. Recent activity
    last_active = signals.get("last_active_date", "")
    days_inactive = _days_since(last_active)
    if days_inactive <= RECENT_ACTIVITY_DAYS:
        activity_score = 1.0
    elif days_inactive <= STALE_ACTIVITY_DAYS:
        activity_score = 0.5
    else:
        activity_score = 0.1

    # 3. Open to work flag
    open_to_work = 1.0 if signals.get("open_to_work_flag", False) else 0.3

    # 4. Interview completion rate
    interview_rate = signals.get("interview_completion_rate", 0)
    interview_score = min(1.0, interview_rate / 0.8)  # 0.8+ is good

    # 5. Notice period (sub-30 preferred, can buy out up to 30)
    notice_days = signals.get("notice_period_days", 90)
    if notice_days <= SHORT_NOTICE_DAYS:
        notice_score = 1.0
    elif notice_days <= 60:
        notice_score = 0.7
    elif notice_days <= LONG_NOTICE_DAYS:
        notice_score = 0.4
    else:
        notice_score = 0.15  # 90+ days is concerning

    # 6. Profile completeness
    completeness = signals.get("profile_completeness_score", 50)
    completeness_score = min(1.0, completeness / 80)  # 80+ is good

    # 7. Response time (faster is better)
    response_time = signals.get("avg_response_time_hours", 200)
    if response_time <= 12:
        time_score = 1.0
    elif response_time <= 48:
        time_score = 0.7
    elif response_time <= 120:
        time_score = 0.4
    else:
        time_score = 0.2

    # 8. Saved by recruiters (social proof)
    saved = signals.get("saved_by_recruiters_30d", 0)
    saved_score = min(1.0, saved / 10)

    # 9. Verified signals
    verified_email = signals.get("verified_email", False)
    verified_phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)
    verification_score = (
        (0.4 if verified_email else 0.0) +
        (0.3 if verified_phone else 0.0) +
        (0.3 if linkedin else 0.0)
    )

    # 10. Offer acceptance rate
    offer_rate = signals.get("offer_acceptance_rate", -1)
    if offer_rate < 0:
        offer_score = 0.5  # No history
    else:
        offer_score = max(0.1, offer_rate)

    # Weighted combination
    score = (
        response_score * 0.20 +
        activity_score * 0.15 +
        open_to_work * 0.12 +
        interview_score * 0.10 +
        notice_score * 0.12 +
        completeness_score * 0.05 +
        time_score * 0.08 +
        saved_score * 0.05 +
        verification_score * 0.05 +
        offer_score * 0.08
    )

    details = {
        "response_rate": response_rate,
        "days_inactive": days_inactive,
        "open_to_work": signals.get("open_to_work_flag", False),
        "notice_days": notice_days,
        "interview_rate": interview_rate,
        "completeness": completeness,
    }

    return round(min(1.0, score), 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 5: Location & Logistics (5%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_location_logistics(candidate: dict) -> tuple[float, dict]:
    """
    Score location alignment with JD (Pune/Noida preferred, India Tier-1 OK).
    """
    location = candidate.get("location", "")
    country = candidate.get("country", "")
    signals = candidate.get("redrob_signals", {})
    willing_to_relocate = signals.get("willing_to_relocate", False)
    work_mode = signals.get("preferred_work_mode", "onsite")

    is_india, is_preferred, is_tier1 = _parse_location(location, country)

    if is_preferred:
        location_score = 1.0
    elif is_tier1:
        location_score = 0.80
    elif is_india:
        location_score = 0.60
    elif willing_to_relocate:
        location_score = 0.30
    else:
        location_score = 0.10  # Outside India, not willing to relocate

    # Work mode alignment (JD says hybrid — flexible cadence)
    mode_scores = {
        "hybrid": 1.0,
        "flexible": 0.90,
        "onsite": 0.70,
        "remote": 0.50,
    }
    mode_score = mode_scores.get(work_mode, 0.5)

    # Relocation willingness bonus for non-preferred locations
    reloc_bonus = 0.10 if willing_to_relocate and not is_preferred else 0.0

    score = location_score * 0.70 + mode_score * 0.20 + reloc_bonus

    details = {
        "location": location,
        "country": country,
        "is_india": is_india,
        "is_preferred_city": is_preferred,
        "willing_to_relocate": willing_to_relocate,
        "work_mode": work_mode,
    }

    return round(min(1.0, score), 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 6: Education & Credentials (5%)
# ═══════════════════════════════════════════════════════════════════════════════

def score_education_credentials(candidate: dict) -> tuple[float, dict]:
    """
    Score education institution tier, field relevance, and certifications.
    """
    education = candidate.get("education", [])
    certifications = candidate.get("certifications", [])

    # Institution tier
    best_tier = "tier_4"
    for edu in education:
        tier = edu.get("tier", "unknown")
        if tier == "tier_1":
            best_tier = "tier_1"
            break
        elif tier == "tier_2" and best_tier in ("tier_3", "tier_4", "unknown"):
            best_tier = "tier_2"
        elif tier == "tier_3" and best_tier in ("tier_4", "unknown"):
            best_tier = "tier_3"

    tier_scores = {"tier_1": 1.0, "tier_2": 0.70, "tier_3": 0.40, "tier_4": 0.20, "unknown": 0.30}
    tier_score = tier_scores.get(best_tier, 0.30)

    # Field of study relevance
    field_score = 0.3  # Default
    for edu in education:
        field = edu.get("field_of_study", "").lower()
        if any(f in field for f in RELEVANT_EDUCATION_FIELDS):
            field_score = max(field_score, 0.9)
        elif any(f in field for f in IRRELEVANT_EDUCATION_FIELDS):
            field_score = max(field_score, 0.1)

    # Degree level
    degree_score = 0.3
    for edu in education:
        degree = edu.get("degree", "").lower()
        if "ph.d" in degree or "phd" in degree:
            degree_score = max(degree_score, 0.9)
        elif "m.tech" in degree or "m.sc" in degree or "m.e." in degree or "ms" in degree or "master" in degree:
            degree_score = max(degree_score, 0.7)
        elif "b.tech" in degree or "b.e." in degree or "b.sc" in degree or "bachelor" in degree:
            degree_score = max(degree_score, 0.5)

    # Certification relevance
    cert_score = 0.0
    relevant_cert_keywords = {
        "aws", "gcp", "azure", "cloud", "ml", "machine learning",
        "ai", "data", "deep learning", "tensorflow", "pytorch",
        "kubernetes", "docker", "devops",
    }
    for cert in certifications:
        cert_name = cert.get("name", "").lower()
        if any(kw in cert_name for kw in relevant_cert_keywords):
            cert_score = min(1.0, cert_score + 0.25)

    # Compose
    score = (
        tier_score * 0.30 +
        field_score * 0.30 +
        degree_score * 0.20 +
        cert_score * 0.20
    )

    details = {
        "best_tier": best_tier,
        "field_relevant": field_score > 0.5,
        "certs_count": len(certifications),
    }

    return round(min(1.0, score), 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Component 7: Anti-Pattern Detection & Positive Signals (10%)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_anti_patterns(candidate: dict) -> tuple[float, float, dict]:
    """
    Detect anti-patterns from the JD's "do not want" section.
    Returns (bonus_score 0-1, penalty_multiplier 0-1, details).
    
    bonus_score: positive signals that go into the weighted sum
    penalty_multiplier: multiplicative penalty on final score (1.0 = no penalty)
    """
    career = candidate.get("career_history", [])
    skill_names = set(candidate.get("skill_names", []))
    all_text = candidate.get("all_text", "")
    career_text = candidate.get("career_descriptions_text", "")
    current_title = candidate.get("current_title", "").lower()
    signals = candidate.get("redrob_signals", {})
    github_score = signals.get("github_activity_score", -1)

    penalty = 1.0
    bonus = 0.0
    reasons = []

    # ── Anti-pattern 1: Consulting-only career ──
    if career:
        consulting_jobs = sum(1 for j in career if _is_consulting_firm(j.get("company", "")))
        if consulting_jobs == len(career):
            penalty *= PENALTIES["consulting_only_career"]
            reasons.append("consulting_only")

    # ── Anti-pattern 2: Completely irrelevant current role ──
    current_relevance = _title_relevance(current_title)
    if current_relevance == 0.0:
        # Check if they have genuine AI skills beyond keyword stuffing
        ai_skills_in_career = _text_contains_any(career_text, AI_CORE_SKILLS)
        if len(ai_skills_in_career) < 3:
            penalty *= PENALTIES["completely_irrelevant_role"]
            reasons.append("irrelevant_role_no_ai_career")

    # ── Anti-pattern 3: Keyword stuffer detection ──
    # Many AI keywords in skills but career descriptions don't mention AI work
    ai_skill_count = sum(1 for s in skill_names if _normalize_skill(s) in AI_CORE_SKILLS or s in AI_CORE_SKILLS)
    ai_in_career = _text_contains_any(career_text, {
        "machine learning", "deep learning", "ml", "ai", "model",
        "neural", "nlp", "embedding", "retrieval", "search",
        "classification", "prediction", "training", "inference",
        "data science", "algorithm",
    })
    if ai_skill_count >= 6 and len(ai_in_career) < 2 and current_relevance < 0.5:
        penalty *= PENALTIES["keyword_stuffer"]
        reasons.append("keyword_stuffer")

    # ── Anti-pattern 4: Title chaser ──
    if len(career) >= 3:
        short_stints = sum(
            1 for j in career
            if j.get("duration_months", 0) < 18 and not j.get("is_current", False)
        )
        if short_stints >= 3:
            penalty *= PENALTIES["title_chaser"]
            reasons.append("title_chaser")

    # ── Anti-pattern 5: CV/Speech/Robotics only, no NLP/IR ──
    cv_speech_skills = _text_contains_any(all_text, CV_SPEECH_ROBOTICS_SKILLS)
    nlp_ir_skills = _text_contains_any(all_text, NLP_IR_SKILLS)
    if len(cv_speech_skills) >= 3 and len(nlp_ir_skills) < 2:
        penalty *= PENALTIES["cv_speech_robotics_only"]
        reasons.append("cv_speech_only")

    # ── Anti-pattern 6: Inactive candidate ──
    last_active = signals.get("last_active_date", "")
    days_inactive = _days_since(last_active)
    if days_inactive > STALE_ACTIVITY_DAYS:
        penalty *= PENALTIES["inactive_candidate"]
        reasons.append("inactive")

    # ── Positive Signals (bonus score) ──

    # GitHub activity
    if github_score >= 70:
        bonus += 0.20
    elif github_score >= 40:
        bonus += 0.10
    elif github_score >= 10:
        bonus += 0.05

    # Product company current
    if _is_product_company(candidate.get("current_company", "")):
        bonus += 0.15

    # Strong production signals
    prod_signals = _text_contains_any(career_text, PRODUCTION_KEYWORDS)
    if len(prod_signals) >= 5:
        bonus += 0.20
    elif len(prod_signals) >= 3:
        bonus += 0.10

    # Open source / community
    if any(kw in all_text for kw in ("open source", "open-source", "contributor", "maintainer")):
        bonus += 0.10

    # Recommendation/search system builder
    if any(kw in career_text for kw in ("recommendation system", "search engine", "ranking system", "retrieval system")):
        bonus += 0.15

    # Mentoring/leadership (JD mentions mentoring next hires)
    if any(kw in career_text for kw in ("mentor", "led team", "team of", "managed")):
        bonus += 0.05

    bonus = min(1.0, bonus)

    details = {
        "penalty_multiplier": round(penalty, 3),
        "anti_patterns": reasons,
        "github_score": github_score,
    }

    return round(bonus, 4), round(penalty, 4), details


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Scoring Function
# ═══════════════════════════════════════════════════════════════════════════════

def score_candidate(candidate: dict) -> tuple[float, dict]:
    """
    Score a single candidate across all dimensions.
    Returns (final_score 0-1, breakdown dict).
    """
    w = SCORING_WEIGHTS

    skills_score, skills_detail = score_skills_match(candidate)
    career_score, career_detail = score_career_trajectory(candidate)
    exp_score, exp_detail = score_experience_fit(candidate)
    behav_score, behav_detail = score_behavioral_signals(candidate)
    loc_score, loc_detail = score_location_logistics(candidate)
    edu_score, edu_detail = score_education_credentials(candidate)
    bonus_score, penalty_mult, pattern_detail = detect_anti_patterns(candidate)

    # Weighted sum of component scores
    weighted_sum = (
        w["skills_match"]          * skills_score +
        w["career_trajectory"]     * career_score +
        w["experience_fit"]        * exp_score +
        w["behavioral_signals"]    * behav_score +
        w["location_logistics"]    * loc_score +
        w["education_credentials"] * edu_score +
        w["anti_pattern_bonus"]    * bonus_score
    )

    # Apply multiplicative penalty for anti-patterns
    final_score = weighted_sum * penalty_mult

    breakdown = {
        "skills_score": skills_score,
        "career_score": career_score,
        "experience_score": exp_score,
        "behavioral_score": behav_score,
        "location_score": loc_score,
        "education_score": edu_score,
        "bonus_score": bonus_score,
        "penalty_factor": penalty_mult,
        "anti_patterns": pattern_detail.get("anti_patterns", []),
        "skills_detail": skills_detail,
        "career_detail": career_detail,
        "exp_detail": exp_detail,
        "behavioral_detail": behav_detail,
        "location_detail": loc_detail,
    }

    return round(final_score, 4), breakdown


# ═══════════════════════════════════════════════════════════════════════════════
#  Batch Scoring (for 100K candidates)
# ═══════════════════════════════════════════════════════════════════════════════

def score_all_candidates(candidates: list[dict], honeypot_ids: set[str] = None) -> list[dict]:
    """
    Score all candidates and return sorted list.
    Honeypots are scored as 0.
    
    Returns list of dicts sorted by score descending, each with:
    - candidate_id, score, breakdown, and all original candidate fields
    """
    if honeypot_ids is None:
        honeypot_ids = set()

    scored = []
    total = len(candidates)

    for i, candidate in enumerate(candidates):
        cid = candidate.get("candidate_id", "")

        if cid in honeypot_ids:
            scored.append({
                **candidate,
                "score": 0.0,
                "breakdown": {"honeypot": True, "penalty_factor": 0.0, "anti_patterns": ["honeypot"]},
            })
            continue

        final_score, breakdown = score_candidate(candidate)
        scored.append({
            **candidate,
            "score": final_score,
            "breakdown": breakdown,
        })

        # Progress reporting
        if (i + 1) % 10000 == 0:
            print(f"   📊 Scored {i+1}/{total} candidates...")

    # Sort by score descending, tie-break by candidate_id ascending
    scored.sort(key=lambda x: (-x["score"], x.get("candidate_id", "")))

    print(f"   ✅ Scoring complete: {total} candidates scored.")
    return scored
