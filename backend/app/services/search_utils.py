"""
Search utility functions for RecruiterRadar backend
"""

from typing import List, Dict, Any, Set, Optional
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)

# Skill synonyms and related skills
SKILL_GROUPS: List[Set[str]] = [
    {"python", "py", "python3", "python2"},
    {"javascript", "js", "ecmascript", "es6", "es5"},
    {"typescript", "ts"},
    {"react", "reactjs", "react.js"},
    {"node", "nodejs", "node.js"},
    {"machine learning", "ml", "ai", "artificial intelligence", "deep learning"},
    {"postgresql", "postgres", "psql"},
    {"mongodb", "mongo"},
    {"docker", "containerization", "containers"},
    {"kubernetes", "k8s"},
    {"amazon web services", "aws", "ec2", "s3", "lambda"},
    {"google cloud", "gcp", "google cloud platform"},
    {"continuous integration", "ci", "ci/cd", "continuous deployment"},
    {"dev ops", "devops", "sre", "site reliability"},
    {"front end", "frontend", "ui", "user interface"},
    {"back end", "backend", "server side"},
    {"full stack", "fullstack", "full-stack"},
    {"rest", "restful", "rest api", "restful api"},
    {"sql", "structured query language", "database"},
    {"nosql", "no sql", "non relational"},
    {"agile", "scrum", "kanban"},
    {"tdd", "test driven development", "testing"},
    {"api", "apis", "web services"},
]


def normalize_skill(skill: str) -> str:
    """Normalize skill for comparison - handles variations."""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r"[^a-zA-Z0-9\s\.\+\#]", "", skill.lower().strip())

    # Common replacements
    replacements = {
        "javascript": "js",
        "typescript": "ts",
        "nodejs": "node",
        "node.js": "node",
        "react.js": "react",
        "vue.js": "vue",
        "angular.js": "angular",
        "postgresql": "postgres",
        "numpy": "np",
        "pandas": "pd",
        "scikit-learn": "sklearn",
        "scikit learn": "sklearn",
        "ml": "machine learning",
        "ai": "artificial intelligence",
        "ai/ml": "machine learning",
        "devops": "dev ops",
        "fullstack": "full stack",
        "full-stack": "full stack",
        "backend": "back end",
        "frontend": "front end",
        "sr": "senior",
        "jr": "junior",
    }

    # Apply replacements
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized


def skills_match_fuzzy(
    required_skills: List[str], candidate_skills: List[str], threshold: float = 0.8
) -> bool:
    """
    Fuzzy skill matching with synonyms and variations.
    Returns True if all required skills have a match (fuzzy or exact).
    """
    # Normalize all skills
    normalized_required = [normalize_skill(s) for s in required_skills]
    normalized_candidate = [normalize_skill(s) for s in candidate_skills]

    logger.info(
        f"🔍 Skills matching: Required: {required_skills} → {normalized_required}"
    )
    logger.info(f"   Candidate skills: {candidate_skills} → {normalized_candidate}")

    # Build expanded candidate skills including synonyms
    expanded_candidate_skills = set(normalized_candidate)
    for skill in normalized_candidate:
        for group in SKILL_GROUPS:
            if skill in group:
                expanded_candidate_skills.update(group)

    # Skills that should NOT match as substrings (common conflicts)
    CONFLICTING_SKILLS = {
        "java": ["javascript", "js"],  # java should not match javascript
        "c": ["c++", "c#"],  # c should not match c++ or c#
        "go": ["golang"],  # go might conflict but golang is ok
        "r": ["react", "ruby"],  # R language should not match React
    }

    # Check each required skill
    for req_skill in normalized_required:
        found = False
        match_reason = "No match"

        # First check if it's in expanded skills (includes synonyms)
        if req_skill in expanded_candidate_skills:
            found = True
            match_reason = "Exact/Synonym match"
        else:
            # Check fuzzy matching
            for cand_skill in expanded_candidate_skills:
                # Use SequenceMatcher for fuzzy matching
                similarity = SequenceMatcher(None, req_skill, cand_skill).ratio()
                if similarity >= threshold:
                    found = True
                    match_reason = f"Fuzzy match with '{cand_skill}' (similarity: {similarity:.2f})"
                    break

                # Check substring matches, but exclude known conflicts
                is_conflicting = False
                if req_skill in CONFLICTING_SKILLS:
                    conflicting_skills = CONFLICTING_SKILLS[req_skill]
                    if cand_skill in conflicting_skills:
                        is_conflicting = True
                        logger.info(
                            f"   ⚠️  Blocked conflicting match: '{req_skill}' vs '{cand_skill}'"
                        )

                if not is_conflicting:
                    # Only allow substring matching for non-conflicting skills
                    # And require minimum length to avoid false matches
                    if len(req_skill) >= 3 and len(cand_skill) >= 3:
                        if req_skill in cand_skill or cand_skill in req_skill:
                            found = True
                            match_reason = f"Substring match with '{cand_skill}'"
                            break

        logger.info(
            f"   🎯 '{req_skill}': {match_reason} → {'✅ MATCH' if found else '❌ NO MATCH'}"
        )

        if not found:
            logger.info(
                f"   🚫 Candidate rejected: Missing required skill '{req_skill}'"
            )
            return False

    logger.info(f"   ✅ Candidate accepted: All required skills found")
    return True


def boost_relevance_score(
    candidate_data: Dict[str, Any], query_terms: List[str]
) -> float:
    """Boost relevance score based on exact matches in resume text."""
    base_score = 1.0 - float(candidate_data.get("distance", 1.0))
    boost = 0.0

    resume_text = candidate_data.get("document", "").lower()
    candidate_name = candidate_data.get("metadata", {}).get("name", "").lower()

    for term in query_terms:
        term_lower = term.lower()
        # Boost for exact skill matches
        if term_lower in resume_text:
            boost += 0.05
        # Extra boost for name matches
        if term_lower in candidate_name:
            boost += 0.1

    # Cap the boost to prevent over-inflation
    return min(base_score + boost, 1.0)


def extract_location_from_query(query: str) -> Optional[str]:
    """🧠 SMART LOCATION EXTRACTION from natural language queries"""
    query_lower = query.lower()

    location_patterns = [
        r"\b(?:in|at|from|near|around|based\s+in)\s+([A-Za-z\s,]+?)(?:\s*$|\s+(?:with|and|or|who|that|looking|seeking))",
        r"\b([A-Za-z\s,]+?)\s+(?:based|located|area|region)\b",
        r"\b(san francisco|sf|bay area|silicon valley|new york|nyc|los angeles|la|chicago|seattle|austin|boston|denver|washington dc|dc)\b",
    ]

    location_mapping = {
        "sf": "San Francisco",
        "bay area": "San Francisco",
        "silicon valley": "San Francisco",
        "palo alto": "San Francisco",
        "nyc": "New York",
        "new york city": "New York",
        "manhattan": "New York",
        "brooklyn": "New York",
        "la": "Los Angeles",
        "los angeles": "Los Angeles",
        "hollywood": "Los Angeles",
        "chi": "Chicago",
        "chicago": "Chicago",
        "windy city": "Chicago",
        "atx": "Austin",
        "austin": "Austin",
        "sea": "Seattle",
        "seattle": "Seattle",
        "emerald city": "Seattle",
        "bos": "Boston",
        "boston": "Boston",
        "bean town": "Boston",
        "den": "Denver",
        "denver": "Denver",
        "mile high": "Denver",
        "dc": "Washington",
        "washington dc": "Washington",
        "dmv": "Washington",
        "remote": "Remote",
        "wfh": "Remote",
        "work from home": "Remote",
        "onsite": "On-site",
        "hybrid": "Hybrid",
    }

    for pattern in location_patterns:
        match = re.search(pattern, query_lower)
        if match:
            location = (
                match.group(1).strip()
                if len(match.groups()) > 0
                else match.group(0).strip()
            )
            mapped_location = location_mapping.get(location, location.title())
            logger.info(
                f"🧠 Backend extracted location: '{mapped_location}' from '{location}'"
            )
            return mapped_location

    return None


def extract_skills_from_query(query: str) -> List[str]:
    """🎯 SMART SKILL EXTRACTION from natural language queries"""
    query_lower = query.lower()

    skill_keywords = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "angular",
        "vue",
        "node",
        "nodejs",
        "django",
        "flask",
        "fastapi",
        "spring",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "machine learning",
        "ml",
        "ai",
        "data science",
        "frontend",
        "backend",
        "fullstack",
        "full stack",
        "devops",
        "database",
        "sql",
        "nosql",
        "mongodb",
        "postgresql",
        "redis",
        "elasticsearch",
        "microservices",
        "api",
        "rest",
        "graphql",
        "git",
        "ci/cd",
        "terraform",
    ]

    found_skills = []
    for skill in skill_keywords:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, query_lower):
            found_skills.append(skill)

    if found_skills:
        logger.info(f"🎯 Backend extracted skills: {found_skills}")

    return found_skills


def extract_experience_level(query: str) -> Optional[Dict[str, Any]]:
    """👨‍💼 SMART EXPERIENCE LEVEL EXTRACTION"""
    query_lower = query.lower()

    experience_patterns = [
        (r"\b(junior|jr|entry.?level|new.?grad|graduate|intern)\b", "junior", 0),
        (r"\b(senior|sr|lead|principal|staff|expert)\b", "senior", 7),
        (r"\b(mid.?level|intermediate|experienced)\b", "mid", 3),
        (r"\b(\d+).?(year|yr)s?\s+(experience|exp)\b", "numeric", None),
    ]

    for pattern, level, min_years in experience_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if level == "numeric":
                years = int(re.search(r"\d+", match.group()).group())
                if years <= 2:
                    result = {
                        "level": "junior",
                        "min_years": 0,
                        "extracted_years": years,
                    }
                elif years <= 5:
                    result = {"level": "mid", "min_years": 3, "extracted_years": years}
                else:
                    result = {
                        "level": "senior",
                        "min_years": years,
                        "extracted_years": years,
                    }
            else:
                result = {
                    "level": level,
                    "min_years": min_years,
                    "extracted_years": None,
                }

            logger.info(f"👨‍💼 Backend extracted experience: {result}")
            return result

    return None


def clean_query_for_embedding(
    query: str, extracted_location: Optional[str] = None
) -> str:
    """🧹 CLEAN QUERY for better semantic search"""
    cleaned = query

    if extracted_location:
        location_patterns = [
            r"\b(?:in|at|from|near|around|based\s+in)\s+[A-Za-z\s,]+?(?:\s*$|\s+(?:with|and|or|who|that|looking|seeking))",
            r"\b[A-Za-z\s,]+?\s+(?:based|located|area|region)\b",
        ]

        for pattern in location_patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned != query:
        logger.info(f"🧹 Backend cleaned query: '{query}' → '{cleaned}'")

    return cleaned


def enhance_search_query(
    query: str, existing_filters: Dict[str, Any]
) -> Dict[str, Any]:
    """🚀 COMPREHENSIVE QUERY ENHANCEMENT"""
    enhancements = {
        "original_query": query,
        "cleaned_query": query,
        "extracted_location": None,
        "extracted_skills": [],
        "extracted_experience": None,
        "enhanced_filters": existing_filters.copy(),
    }

    # Handle empty queries - just return with filters intact
    if not query.strip():
        enhancements["cleaned_query"] = ""
        return enhancements

    # Extract location
    if not existing_filters.get("location"):
        location = extract_location_from_query(query)
        if location:
            enhancements["extracted_location"] = location
            enhancements["enhanced_filters"]["location"] = location

    # Extract skills
    if not existing_filters.get("skills"):
        skills = extract_skills_from_query(query)
        if skills:
            enhancements["extracted_skills"] = skills
            enhancements["enhanced_filters"]["skills"] = ",".join(skills)

    # Extract experience level
    if not existing_filters.get("min_experience"):
        experience = extract_experience_level(query)
        if experience and experience.get("min_years") is not None:
            enhancements["extracted_experience"] = experience
            enhancements["enhanced_filters"]["min_experience"] = experience["min_years"]

    # Clean query for better embedding
    enhancements["cleaned_query"] = clean_query_for_embedding(
        query, enhancements["extracted_location"]
    )

    return enhancements
