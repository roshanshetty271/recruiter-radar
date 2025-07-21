"""
Search utility functions for RecruiterRadar backend
"""

from typing import List, Dict, Any, Set, Optional
from difflib import SequenceMatcher
import re
import logging
from fuzzywuzzy import fuzz

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

# 🔒 NEW: Fallback and suggestion constants
DEFAULT_SEARCH_QUERIES = [
    "software engineer with programming experience",
    "developer with technical skills",
    "candidate with technology background",
    "professional with software development experience",
]

POPULAR_SEARCH_SUGGESTIONS = [
    "Python developers with AI experience",
    "React frontend engineers",
    "Senior full-stack developers",
    "DevOps engineers with AWS",
    "Data scientists with machine learning",
    "Backend engineers with Java",
    "Mobile developers iOS Android",
    "Cloud architects with microservices",
]

FALLBACK_FILTERS = {
    "page_size": 20,
    "include_all_experience_levels": True,
    "broad_skill_matching": True,
}

# 🚀 NEW: Advanced negation and query parsing patterns
NEGATION_PATTERNS = [
    r"\b(?:not|no|without|except|excluding|exclude|but not|dont|don\'t|avoid)\s+([^,\.\!]+?)(?:\s*[,\.\!]|\s*$|\s+(?:and|but|or))",
    r"\b([^,\.\!]+?)\s+(?:except|excluding|but not|without)\s+([^,\.\!]+?)(?:\s*[,\.\!]|\s*$)",
    r"\b-([a-zA-Z0-9\+\#]+)\b",  # Dash notation like "-java"
]

# 🎯 Enhanced skill patterns with better recognition
ADVANCED_SKILL_PATTERNS = [
    # Programming languages with variations
    r"\b(python(?:\s*3?)?|py(?:thon)?)\b",
    r"\b(javascript|js|ecmascript|es6|es5|node\.?js|nodejs)\b",
    r"\b(typescript|ts)\b",
    r"\b(java(?:\s*8|11|17)?)\b",  # Java with versions
    r"\b(c\+\+|cpp|c plus plus)\b",
    r"\b(c#|csharp|c sharp|\.net)\b",
    r"\b(golang|go(?:\s+lang)?)\b",
    r"\b(rust|rustlang)\b",
    r"\b(php(?:\s*7|8)?)\b",
    r"\b(ruby(?:\s+on\s+rails)?|ror)\b",
    r"\b(swift|objective[_\s]?c)\b",
    r"\b(kotlin|scala)\b",
    # Frameworks and libraries
    r"\b(react(?:\.?js)?|reactjs)\b",
    r"\b(angular(?:\.?js)?|angularjs)\b",
    r"\b(vue(?:\.?js)?|vuejs)\b",
    r"\b(django|flask|fastapi)\b",
    r"\b(spring(?:\s+boot)?|springboot)\b",
    r"\b(express(?:\.?js)?|expressjs)\b",
    r"\b(nextjs|next\.js)\b",
    r"\b(gatsby|nuxt)\b",
    # Databases
    r"\b(postgresql|postgres|psql)\b",
    r"\b(mysql|mariadb)\b",
    r"\b(mongodb|mongo)\b",
    r"\b(redis|memcached)\b",
    r"\b(elasticsearch|elastic\s+search)\b",
    r"\b(cassandra|dynamodb)\b",
    # Cloud and DevOps
    r"\b(aws|amazon\s+web\s+services|ec2|s3|lambda)\b",
    r"\b(azure|microsoft\s+azure)\b",
    r"\b(gcp|google\s+cloud(?:\s+platform)?)\b",
    r"\b(docker|containerization|kubernetes|k8s)\b",
    r"\b(terraform|ansible|puppet|chef)\b",
    r"\b(jenkins|github\s+actions|gitlab\s+ci)\b",
    # AI/ML/Data
    r"\b(machine\s+learning|ml|artificial\s+intelligence|ai)\b",
    r"\b(tensorflow|pytorch|keras)\b",
    r"\b(pandas|numpy|scikit[_\s]?learn|sklearn)\b",
    r"\b(data\s+science|data\s+scientist|data\s+engineer)\b",
    # Methodologies
    r"\b(agile|scrum|kanban)\b",
    r"\b(devops|dev\s+ops|sre|site\s+reliability)\b",
    r"\b(microservices|micro\s+services)\b",
    r"\b(api|rest(?:ful)?|graphql)\b",
    r"\b(ci\/cd|continuous\s+integration|continuous\s+deployment)\b",
]

# 🌍 Enhanced location patterns with international support
ENHANCED_LOCATION_PATTERNS = [
    # US Cities and States
    r"\b(san francisco|sf|bay area|silicon valley|palo alto|mountain view|cupertino|santa clara)\b",
    r"\b(new york|nyc|manhattan|brooklyn|queens|bronx)\b",
    r"\b(los angeles|la|hollywood|santa monica|beverly hills)\b",
    r"\b(chicago|windy city)\b",
    r"\b(seattle|emerald city)\b",
    r"\b(austin|atx)\b",
    r"\b(boston|cambridge)\b",
    r"\b(denver|boulder)\b",
    r"\b(washington|dc|dmv)\b",
    r"\b(miami|fort lauderdale)\b",
    r"\b(dallas|houston|san antonio)\b",
    r"\b(atlanta|phoenix|portland|minneapolis)\b",
    # International
    r"\b(london|manchester|birmingham|uk|united kingdom)\b",
    r"\b(toronto|vancouver|montreal|ottawa|canada)\b",
    r"\b(berlin|munich|hamburg|germany|deutschland)\b",
    r"\b(paris|lyon|france)\b",
    r"\b(amsterdam|netherlands|holland)\b",
    r"\b(stockholm|gothenburg|sweden)\b",
    r"\b(copenhagen|denmark)\b",
    r"\b(zurich|geneva|switzerland)\b",
    r"\b(dublin|ireland)\b",
    r"\b(sydney|melbourne|brisbane|australia)\b",
    r"\b(tokyo|osaka|japan)\b",
    r"\b(singapore|hong kong|taipei)\b",
    r"\b(bangalore|mumbai|delhi|pune|hyderabad|india)\b",
    # Work arrangements
    r"\b(remote|work\s+from\s+home|wfh|distributed|anywhere)\b",
    r"\b(hybrid|flexible|on[_\s]?site|onsite|in[_\s]?person)\b",
]


def extract_negations_from_query(query: str) -> Dict[str, List[str]]:
    """
    🚫 ADVANCED NEGATION EXTRACTION - Find what the user explicitly wants to avoid

    Returns:
        Dict with 'excluded_skills', 'excluded_locations', etc.
    """
    negations = {"excluded_skills": [], "excluded_locations": [], "excluded_terms": []}

    query_lower = query.lower()

    for pattern in NEGATION_PATTERNS:
        matches = re.finditer(pattern, query_lower, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 1:
                excluded_term = match.group(1).strip()
                if excluded_term:
                    # Check if it's a skill
                    if any(
                        re.search(skill_pattern, excluded_term, re.IGNORECASE)
                        for skill_pattern in ADVANCED_SKILL_PATTERNS
                    ):
                        negations["excluded_skills"].append(excluded_term)
                    # Check if it's a location
                    elif any(
                        re.search(loc_pattern, excluded_term, re.IGNORECASE)
                        for loc_pattern in ENHANCED_LOCATION_PATTERNS
                    ):
                        negations["excluded_locations"].append(excluded_term)
                    else:
                        negations["excluded_terms"].append(excluded_term)

    if any(negations.values()):
        logger.info(f"🚫 Extracted negations: {negations}")

    return negations


def extract_skills_from_query_advanced(query: str) -> Dict[str, List[str]]:
    """
    🎯 ADVANCED SKILL EXTRACTION with pattern matching and context awareness

    Returns:
        Dict with 'required_skills', 'preferred_skills', 'skill_categories'
    """
    skills_data = {
        "required_skills": [],
        "preferred_skills": [],
        "skill_categories": set(),
    }

    query_lower = query.lower()

    # Extract skills using advanced patterns
    for pattern in ADVANCED_SKILL_PATTERNS:
        matches = re.finditer(pattern, query_lower, re.IGNORECASE)
        for match in matches:
            skill = match.group(0).strip()
            normalized_skill = normalize_skill(skill)

            # Determine if required or preferred based on context
            match_start = match.start()
            context_before = query_lower[max(0, match_start - 20) : match_start]
            context_after = query_lower[match.end() : match.end() + 20]

            # Check for requirement indicators
            requirement_indicators = [
                "must",
                "required",
                "need",
                "essential",
                "mandatory",
            ]
            preference_indicators = ["prefer", "nice", "bonus", "plus", "would like"]

            is_required = any(
                indicator in context_before for indicator in requirement_indicators
            )
            is_preferred = any(
                indicator in context_before or indicator in context_after
                for indicator in preference_indicators
            )

            if is_required or (not is_preferred and not is_required):
                # Default to required if not explicitly preferred
                skills_data["required_skills"].append(normalized_skill)
            else:
                skills_data["preferred_skills"].append(normalized_skill)

            # Categorize skills
            if any(
                term in normalized_skill
                for term in [
                    "frontend",
                    "react",
                    "angular",
                    "vue",
                    "javascript",
                    "typescript",
                ]
            ):
                skills_data["skill_categories"].add("frontend")
            elif any(
                term in normalized_skill
                for term in [
                    "backend",
                    "api",
                    "server",
                    "database",
                    "python",
                    "java",
                    "node",
                ]
            ):
                skills_data["skill_categories"].add("backend")
            elif any(
                term in normalized_skill
                for term in ["devops", "docker", "kubernetes", "aws", "cloud"]
            ):
                skills_data["skill_categories"].add("devops")
            elif any(
                term in normalized_skill
                for term in ["ml", "machine learning", "ai", "data"]
            ):
                skills_data["skill_categories"].add("ai_ml")

    # Remove duplicates while preserving order
    skills_data["required_skills"] = list(dict.fromkeys(skills_data["required_skills"]))
    skills_data["preferred_skills"] = list(
        dict.fromkeys(skills_data["preferred_skills"])
    )
    skills_data["skill_categories"] = list(skills_data["skill_categories"])

    if skills_data["required_skills"] or skills_data["preferred_skills"]:
        logger.info(f"🎯 Advanced skill extraction: {skills_data}")

    return skills_data


def extract_location_from_query_advanced(query: str) -> Dict[str, Any]:
    """
    🌍 ADVANCED LOCATION EXTRACTION with international support and work arrangements
    """
    location_data = {
        "primary_location": None,
        "work_arrangement": None,
        "location_flexibility": None,
        "normalized_location": None,
    }

    query_lower = query.lower()

    # Work arrangement patterns first (remote, hybrid, etc.)
    work_arrangement_map = {
        "remote": ["remote", "work from home", "wfh", "distributed", "anywhere"],
        "hybrid": ["hybrid", "flexible"],
        "onsite": ["onsite", "on-site", "in-person", "office"],
    }

    for arrangement, patterns in work_arrangement_map.items():
        if any(pattern in query_lower for pattern in patterns):
            location_data["work_arrangement"] = arrangement
            break

    # Extract specific locations
    for pattern in ENHANCED_LOCATION_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            raw_location = match.group(0).strip()
            normalized = normalize_location(raw_location)
            if normalized:
                location_data["primary_location"] = raw_location
                location_data["normalized_location"] = normalized
                break

    # Detect location flexibility
    flexibility_indicators = ["willing to relocate", "open to", "flexible", "anywhere"]
    if any(indicator in query_lower for indicator in flexibility_indicators):
        location_data["location_flexibility"] = "flexible"

    if any(location_data.values()):
        logger.info(f"🌍 Advanced location extraction: {location_data}")

    return location_data


def normalize_location(location: str) -> Optional[str]:
    """
    🗺️ NORMALIZE LOCATION with comprehensive mapping
    """
    location_lower = location.lower().strip()

    # Comprehensive location mapping
    location_mapping = {
        # US Major Tech Hubs
        "sf": "San Francisco, CA",
        "san francisco": "San Francisco, CA",
        "bay area": "San Francisco Bay Area, CA",
        "silicon valley": "Silicon Valley, CA",
        "palo alto": "Palo Alto, CA",
        "mountain view": "Mountain View, CA",
        "cupertino": "Cupertino, CA",
        "santa clara": "Santa Clara, CA",
        "nyc": "New York, NY",
        "new york": "New York, NY",
        "manhattan": "New York, NY",
        "brooklyn": "Brooklyn, NY",
        "la": "Los Angeles, CA",
        "los angeles": "Los Angeles, CA",
        "hollywood": "Los Angeles, CA",
        "santa monica": "Santa Monica, CA",
        "chicago": "Chicago, IL",
        "seattle": "Seattle, WA",
        "austin": "Austin, TX",
        "atx": "Austin, TX",
        "boston": "Boston, MA",
        "denver": "Denver, CO",
        "washington": "Washington, DC",
        "dc": "Washington, DC",
        # International
        "london": "London, UK",
        "uk": "United Kingdom",
        "united kingdom": "United Kingdom",
        "toronto": "Toronto, Canada",
        "vancouver": "Vancouver, Canada",
        "montreal": "Montreal, Canada",
        "canada": "Canada",
        "berlin": "Berlin, Germany",
        "munich": "Munich, Germany",
        "germany": "Germany",
        "paris": "Paris, France",
        "france": "France",
        "amsterdam": "Amsterdam, Netherlands",
        "netherlands": "Netherlands",
        "holland": "Netherlands",
        "stockholm": "Stockholm, Sweden",
        "sweden": "Sweden",
        "copenhagen": "Copenhagen, Denmark",
        "denmark": "Denmark",
        "zurich": "Zurich, Switzerland",
        "switzerland": "Switzerland",
        "dublin": "Dublin, Ireland",
        "ireland": "Ireland",
        "sydney": "Sydney, Australia",
        "melbourne": "Melbourne, Australia",
        "australia": "Australia",
        "singapore": "Singapore",
        "hong kong": "Hong Kong",
        "tokyo": "Tokyo, Japan",
        "japan": "Japan",
        "bangalore": "Bangalore, India",
        "mumbai": "Mumbai, India",
        "delhi": "Delhi, India",
        "pune": "Pune, India",
        "hyderabad": "Hyderabad, India",
        "india": "India",
        # Work arrangements
        "remote": "Remote",
        "work from home": "Remote",
        "wfh": "Remote",
        "anywhere": "Remote",
        "distributed": "Remote",
        "hybrid": "Hybrid",
        "flexible": "Hybrid",
        "onsite": "On-site",
        "on-site": "On-site",
        "in-person": "On-site",
    }

    return location_mapping.get(location_lower, location.title())


def get_fallback_query_for_empty_search() -> str:
    """
    🔄 FALLBACK: Get a reasonable default query for empty searches

    Returns:
        str: A generic query that will return diverse candidates
    """
    import random

    fallback_query = random.choice(DEFAULT_SEARCH_QUERIES)
    logger.info(f"🔄 Using fallback query for empty search: '{fallback_query}'")
    return fallback_query


def generate_search_suggestions_for_empty_results(
    original_query: str, applied_filters: Dict[str, Any]
) -> List[str]:
    """
    💡 SUGGESTIONS: Generate helpful search suggestions when no results found

    Args:
        original_query: The original search query that returned no results
        applied_filters: The filters that were applied

    Returns:
        List of suggested alternative searches
    """
    suggestions = []

    # If query was very specific, suggest broader terms
    if len(original_query.split()) > 5:
        suggestions.append("Try a shorter, more general search")

    # If specific skills were mentioned, suggest alternatives
    query_lower = original_query.lower()
    skill_alternatives = {
        "react": "frontend developer",
        "python": "backend developer",
        "java": "enterprise developer",
        "ai": "machine learning engineer",
        "devops": "infrastructure engineer",
    }

    for skill, alternative in skill_alternatives.items():
        if skill in query_lower:
            suggestions.append(f"Try '{alternative}' instead of '{skill}'")

    # Location-based suggestions
    if applied_filters.get("location"):
        suggestions.append("Try searching without location filter")
        suggestions.append("Try 'Remote' for location")

    # Experience-based suggestions
    if applied_filters.get("min_experience"):
        suggestions.append("Try reducing minimum experience requirement")

    # Add some popular alternatives if we don't have enough suggestions
    if len(suggestions) < 3:
        suggestions.extend(POPULAR_SEARCH_SUGGESTIONS[:3])

    return suggestions[:5]  # Limit to 5 suggestions


def get_query_quality_assessment(query: str) -> Dict[str, Any]:
    """
    📊 ANALYSIS: Assess query quality and provide improvement suggestions

    Args:
        query: The search query to analyze

    Returns:
        Dict containing quality assessment and suggestions
    """
    assessment = {
        "quality_score": 0.5,  # 0.0 to 1.0
        "issues": [],
        "suggestions": [],
        "strengths": [],
    }

    if not query.strip():
        assessment["quality_score"] = 0.0
        assessment["issues"].append("Query is empty")
        assessment["suggestions"].append(
            "Try describing the type of candidate you need"
        )
        return assessment

    words = query.split()
    word_count = len(words)

    # Assess based on length
    if word_count < 2:
        assessment["issues"].append("Query is very short")
        assessment["suggestions"].append("Add more details about skills or role")
        assessment["quality_score"] -= 0.2
    elif word_count > 15:
        assessment["issues"].append("Query might be too long")
        assessment["suggestions"].append("Try focusing on key requirements")
        assessment["quality_score"] -= 0.1
    else:
        assessment["strengths"].append("Good query length")
        assessment["quality_score"] += 0.2

    # Check for specific skills
    detected_skills = extract_skills_from_query(query)
    if detected_skills:
        assessment["strengths"].append(
            f"Mentions specific skills: {', '.join(detected_skills[:3])}"
        )
        assessment["quality_score"] += 0.2
    else:
        assessment["suggestions"].append("Consider adding specific technical skills")

    # Check for role level
    if any(
        level in query.lower() for level in ["senior", "junior", "lead", "principal"]
    ):
        assessment["strengths"].append("Specifies experience level")
        assessment["quality_score"] += 0.1
    else:
        assessment["suggestions"].append(
            "Consider specifying experience level (junior/senior)"
        )

    # Check for generic terms
    generic_terms = ["developer", "engineer", "programmer", "person", "candidate"]
    if any(term in query.lower() for term in generic_terms) and word_count <= 2:
        assessment["issues"].append("Query is very generic")
        assessment["suggestions"].append("Add specific technologies or requirements")
        assessment["quality_score"] -= 0.1

    # Ensure score is in valid range
    assessment["quality_score"] = max(0.0, min(1.0, assessment["quality_score"]))

    return assessment


def validate_and_sanitize_query(query: str) -> Dict[str, Any]:
    """
    🔒 VALIDATION: Validate and sanitize search query input

    Args:
        query: Raw query string from user

    Returns:
        Dict containing sanitized query and any issues found
    """
    result = {
        "original": query,
        "sanitized": query,
        "issues": [],
        "was_modified": False,
    }

    if not query:
        return result

    # Remove potentially problematic characters
    dangerous_patterns = [
        (r"<script[^>]*>.*?</script>", ""),
        (r"javascript:", ""),
        (r"data:", ""),
        (r"vbscript:", ""),
        (r"on\w+\s*=", ""),
    ]

    sanitized = query
    for pattern, replacement in dangerous_patterns:
        new_sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        if new_sanitized != sanitized:
            result["issues"].append(f"Removed potentially unsafe content")
            result["was_modified"] = True
            sanitized = new_sanitized

    # Normalize whitespace
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if sanitized != query.strip():
        result["was_modified"] = True

    # Check for excessive special characters
    special_char_count = len(re.findall(r"[^\w\s\-\.,]", sanitized))
    if special_char_count > 10:
        result["issues"].append("Query contains many special characters")

    result["sanitized"] = sanitized
    return result


def normalize_skill(skill: str) -> str:
    """Normalize skill for comparison - handles variations."""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r"[^a-zA-Z0-9\s\.\+\#]", "", skill.lower().strip())

    # Common replacements - USE WORD BOUNDARIES to prevent substring issues
    replacements = {
        r"\bjavascript\b": "js",
        r"\btypescript\b": "ts",
        r"\bnodejs\b": "node",
        r"\bnode\.js\b": "node",
        r"\breact\.js\b": "react",
        r"\bvue\.js\b": "vue",
        r"\bangular\.js\b": "angular",
        r"\bpostgresql\b": "postgres",
        r"\bnumpy\b": "np",
        r"\bpandas\b": "pd",
        r"\bscikit-learn\b": "sklearn",
        r"\bscikit learn\b": "sklearn",
        r"\b(?<!ht)ml\b": "machine learning",  # Match 'ml' but not when preceded by 'ht' (html)
        r"\bai\b": "artificial intelligence",
        r"\bai/ml\b": "machine learning",
        r"\bdevops\b": "dev ops",
        r"\bfullstack\b": "full stack",
        r"\bfull-stack\b": "full stack",
        r"\bbackend\b": "back end",
        r"\bfrontend\b": "front end",
        r"\bsr\b": "senior",
        r"\bjr\b": "junior",
    }

    # Apply replacements using regex with word boundaries
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized)

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
    candidate_data: Dict[str, Any],
    query_terms: List[str],
    extracted_query_skills: Optional[List[str]] = None,
) -> float:
    """Enhanced relevance score calculation with skill-based boosting."""
    base_score = 1.0 - float(candidate_data.get("distance", 1.0))
    boost = 0.0

    resume_text = candidate_data.get("document", "").lower()
    candidate_name = candidate_data.get("metadata", {}).get("name", "").lower()
    candidate_skills = candidate_data.get("metadata", {}).get("skills", "").lower()
    candidate_title = (
        candidate_data.get("metadata", {}).get("current_title", "").lower()
    )

    # Use pre-extracted skills or extract once if not provided
    if extracted_query_skills is None:
        query_text = " ".join(query_terms)
        extracted_query_skills = extract_skills_from_query(query_text)

    # Convert to lowercase for comparison
    query_skills_lower = [skill.lower() for skill in extracted_query_skills]
    candidate_skills_list = [
        s.strip().lower() for s in candidate_skills.split(",") if s.strip()
    ]

    # 🎯 HIGH BOOST: Exact skill matches (highest priority)
    skill_match_count = 0
    for query_skill in query_skills_lower:
        for candidate_skill in candidate_skills_list:
            # Exact match or substring match for skills
            if (
                query_skill == candidate_skill
                or query_skill in candidate_skill
                or candidate_skill in query_skill
            ):
                skill_match_count += 1
                boost += 0.15  # High boost for skill matches
                logger.debug(
                    f"🎯 Skill match: '{query_skill}' ↔ '{candidate_skill}' (+0.15)"
                )
                break

    # 🏆 EXTRA BOOST: Multiple skill matches (compound effect)
    if skill_match_count > 1:
        compound_boost = min(skill_match_count * 0.05, 0.15)  # Cap at 0.15
        boost += compound_boost
        logger.debug(
            f"🏆 Multiple skills bonus: {skill_match_count} skills (+{compound_boost:.2f})"
        )

    # 🎯 MEDIUM BOOST: Role/title relevance
    role_terms = [
        "developer",
        "engineer",
        "programmer",
        "architect",
        "manager",
        "analyst",
        "scientist",
    ]
    query_roles = [
        term for term in query_terms if any(role in term for role in role_terms)
    ]

    for role_term in query_roles:
        if role_term in candidate_title or role_term in resume_text:
            boost += 0.08
            logger.debug(f"🎯 Role match: '{role_term}' in title/resume (+0.08)")

    # 📝 STANDARD BOOST: General term matches in resume
    for term in query_terms:
        term_lower = term.lower()
        if len(term_lower) > 2:  # Skip very short terms
            # Boost for exact skill matches
            if term_lower in candidate_skills:
                boost += 0.05
                logger.debug(f"📝 Term in skills: '{term_lower}' (+0.05)")
            # Boost for terms in resume text
            elif term_lower in resume_text:
                boost += 0.03
                logger.debug(f"📝 Term in resume: '{term_lower}' (+0.03)")

    # 👤 SMALL BOOST: Name matches (useful for specific searches)
    for term in query_terms:
        term_lower = term.lower()
        if term_lower in candidate_name:
            boost += 0.10
            logger.debug(f"👤 Name match: '{term_lower}' (+0.10)")

    # 🔥 SPECIAL BOOST: High-demand technology combinations
    high_demand_combos = [
        ["react", "javascript"],
        ["python", "machine learning"],
        ["aws", "docker"],
        ["kubernetes", "devops"],
        ["node.js", "javascript"],
        ["tensorflow", "python"],
    ]

    query_text_lower = " ".join(query_terms).lower()
    for combo in high_demand_combos:
        if all(tech.lower() in candidate_skills for tech in combo):
            if any(tech.lower() in query_text_lower for tech in combo):
                boost += 0.06
                logger.debug(f"🔥 High-demand combo: {combo} (+0.06)")

    # 🎓 EDUCATION BOOST: Degree relevance
    education_keywords = ["bachelor", "master", "phd", "doctorate", "degree"]
    for edu_term in education_keywords:
        if edu_term in resume_text:
            boost += 0.02
            logger.debug(f"🎓 Education keyword: '{edu_term}' (+0.02)")

    # ⭐ EXPERIENCE BOOST: Years of experience keywords
    if any(exp_term in resume_text for exp_term in ["years", "experience", "senior"]):
        boost += 0.02
        logger.debug("⭐ Experience keywords found (+0.02)")

    # Calculate final score with reasonable bounds
    final_score = max(0.0, min(1.0, base_score + boost))

    # Log significant boosts for debugging
    if boost > 0.3:
        logger.debug(
            f"🚀 High relevance boost: {boost:.3f} → final score: {final_score:.3f}"
        )

    return final_score


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


SKILL_CATEGORIES = {
    "web developer": [
        "html",
        "css",
        "javascript",
        "react",
        "vue",
        "angular",
        "typescript",
        "node.js",
        "frontend",
        "backend",
        "full-stack",
    ],
    "cloud developer": [
        "aws",
        "azure",
        "gcp",
        "kubernetes",
        "docker",
        "terraform",
        "serverless",
        "cloud architecture",
        "devops",
    ],
    "data scientist": [
        "python",
        "r",
        "sql",
        "tensorflow",
        "pytorch",
        "machine learning",
        "data analysis",
    ],
    # Add more as needed
}


def extract_skills_from_query(query: str) -> List[str]:
    """Extract skills from query using simple keyword matching"""
    logger.info(f"🔍 Extracting skills from query: '{query}'")
    query_lower = query.lower()
    extracted = []

    # Check for categories first
    for category, skills in SKILL_CATEGORIES.items():
        if category in query_lower:
            extracted.extend(skills)
            logger.info(f"🎯 Found category '{category}' → Added skills: {skills}")

    # Existing keyword extraction
    keywords = [
        "python",
        "java",
        "javascript",
        "react",
        "vue",
        "angular",
        "node",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "sql",
        "nosql",
        "mongodb",
        "postgres",
        "fastapi",
        "django",
        "flask",
        "spring",
        "tensorflow",
        "pytorch",
        "scikit-learn",
        "html",
        "css",
        "typescript",
        "go",
        "rust",
    ]
    for keyword in keywords:
        if keyword in query_lower:
            extracted.append(keyword)
            logger.info(f"🎯 Extracted skill: '{keyword}'")

    extracted = list(set(extracted))  # Remove duplicates
    logger.info(f"✅ Extracted {len(extracted)} unique skills")
    return extracted


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
    """🚀 SUPERCHARGED QUERY ENHANCEMENT with advanced AI-powered parsing"""
    enhancements = {
        "original_query": query,
        "cleaned_query": query,
        "extracted_location": None,
        "extracted_skills": [],
        "extracted_experience": None,
        "enhanced_filters": existing_filters.copy(),
        "used_fallback": False,
        "query_quality": None,
        "suggestions": [],
        # 🚀 NEW: Advanced extraction results
        "negations": {},
        "advanced_skills": {},
        "advanced_location": {},
        "intelligence_level": "advanced",
    }

    # 🔒 NEW: Validate and sanitize query
    validation_result = validate_and_sanitize_query(query)
    if validation_result["was_modified"]:
        logger.warning(
            f"🔒 Query was sanitized: '{query}' → '{validation_result['sanitized']}'"
        )
        query = validation_result["sanitized"]
        enhancements["original_query"] = query

    # 🧹 VALIDATE AND CLEAN EXISTING LOCATION FILTER
    existing_location = existing_filters.get("location")
    if existing_location:
        # Filter out invalid/meaningless location values
        invalid_locations = [
            "me",
            "you",
            "us",
            "here",
            "there",
            "none",
            "null",
            "undefined",
        ]
        if (
            len(existing_location.strip()) < 2
            or existing_location.lower().strip() in invalid_locations
        ):
            logger.warning(
                f"🚫 Ignoring invalid location filter: '{existing_location}'"
            )
            enhancements["enhanced_filters"]["location"] = None
        else:
            logger.info(f"✅ Using valid location filter: '{existing_location}'")

    # 🔄 NEW: Handle empty queries with fallback
    if not query.strip():
        fallback_query = get_fallback_query_for_empty_search()
        enhancements["cleaned_query"] = fallback_query
        enhancements["used_fallback"] = True
        enhancements["suggestions"] = [
            "Try specific skills like 'Python' or 'React'",
            "Specify experience level like 'Senior' or 'Junior'",
        ]
        logger.info(f"🔄 Applied fallback for empty query: '{fallback_query}'")
        return enhancements

    # 📊 NEW: Assess query quality
    enhancements["query_quality"] = get_query_quality_assessment(query)

    # 🚫 NEW: Extract negations (what to avoid)
    enhancements["negations"] = extract_negations_from_query(query)

    # 🎯 NEW: Advanced skill extraction with context awareness
    enhancements["advanced_skills"] = extract_skills_from_query_advanced(query)

    # Use advanced skills if available, fallback to basic extraction
    if not existing_filters.get("skills"):
        if enhancements["advanced_skills"]["required_skills"]:
            all_skills = (
                enhancements["advanced_skills"]["required_skills"]
                + enhancements["advanced_skills"]["preferred_skills"]
            )
            enhancements["extracted_skills"] = all_skills
            enhancements["enhanced_filters"]["skills"] = ",".join(all_skills)
            # Also store skill priorities for ranking
            enhancements["enhanced_filters"]["required_skills"] = enhancements[
                "advanced_skills"
            ]["required_skills"]
            enhancements["enhanced_filters"]["preferred_skills"] = enhancements[
                "advanced_skills"
            ]["preferred_skills"]
        else:
            # Fallback to basic extraction
            skills = extract_skills_from_query(query)
            if skills:
                enhancements["extracted_skills"] = skills
                enhancements["enhanced_filters"]["skills"] = ",".join(skills)

    # 🌍 NEW: Advanced location extraction with work arrangements
    enhancements["advanced_location"] = extract_location_from_query_advanced(query)

    # Use advanced location if available, fallback to basic extraction
    if not existing_filters.get("location"):
        if enhancements["advanced_location"]["normalized_location"]:
            enhancements["extracted_location"] = enhancements["advanced_location"][
                "normalized_location"
            ]
            enhancements["enhanced_filters"]["location"] = enhancements[
                "advanced_location"
            ]["normalized_location"]
            # Also store work arrangement preferences
            if enhancements["advanced_location"]["work_arrangement"]:
                enhancements["enhanced_filters"]["work_arrangement"] = enhancements[
                    "advanced_location"
                ]["work_arrangement"]
        else:
            # Fallback to basic extraction
            location = extract_location_from_query(query)
            if location:
                enhancements["extracted_location"] = location
                enhancements["enhanced_filters"]["location"] = location

    # Extract experience level (keeping existing logic)
    if not existing_filters.get("min_experience"):
        experience = extract_experience_level(query)
        if experience and experience.get("min_years") is not None:
            enhancements["extracted_experience"] = experience
            enhancements["enhanced_filters"]["min_experience"] = experience["min_years"]

    # 🧹 ADVANCED: Clean query for better embedding (remove extracted info)
    cleaned_query = query

    # Remove location info if extracted
    if enhancements["extracted_location"]:
        cleaned_query = clean_query_for_embedding(
            cleaned_query, enhancements["extracted_location"]
        )

    # Remove negated terms for embedding (but keep them for filtering)
    for excluded_term in enhancements["negations"].get("excluded_terms", []):
        # Remove negation patterns but keep the core query
        negation_removal_patterns = [
            rf"\b(?:not|no|without|except|excluding|exclude|but not|dont|don\'t|avoid)\s+{re.escape(excluded_term)}\b",
            rf"\b{re.escape(excluded_term)}\s+(?:except|excluding|but not|without)\b",
            rf"\b-{re.escape(excluded_term)}\b",
        ]
        for pattern in negation_removal_patterns:
            cleaned_query = re.sub(pattern, " ", cleaned_query, flags=re.IGNORECASE)

    # Final cleaning
    cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()
    enhancements["cleaned_query"] = cleaned_query

    # 💡 Generate intelligent suggestions based on what was extracted
    suggestions = []
    if enhancements["advanced_skills"]["skill_categories"]:
        categories = enhancements["advanced_skills"]["skill_categories"]
        if "frontend" in categories and "backend" in categories:
            suggestions.append("Consider searching for 'Full Stack' developers")
        elif len(categories) == 1:
            suggestions.append(
                f"Try broadening to related {categories[0]} technologies"
            )

    if enhancements["negations"]["excluded_skills"]:
        suggestions.append(
            "Using exclusions - results will avoid mentioned technologies"
        )

    if (
        not enhancements["extracted_location"]
        and not enhancements["advanced_location"]["work_arrangement"]
    ):
        suggestions.append("Consider adding location or 'Remote' to refine results")

    enhancements["suggestions"] = suggestions

    logger.info(
        f"🚀 Query enhanced: {len(enhancements['extracted_skills'])} skills extracted"
    )

    return enhancements


def apply_fuzzy_skills_filter(
    candidates: List[Dict[str, Any]],
    required_skills: List[str],
    preferred_skills: List[str] = None,
    fuzzy_threshold: float = 0.8,
) -> List[Dict[str, Any]]:
    """Apply fuzzy skills filtering with required and preferred skills"""
    preferred_skills = preferred_skills or []
    filtered = []
    for candidate in candidates:
        candidate_skills = [s.lower() for s in candidate.get("skills", [])]
        candidate_text = " ".join(candidate_skills)

        # Check required skills - all must match
        required_matches = sum(
            1
            for req in required_skills
            if any(
                fuzz.ratio(req.lower(), cand.lower()) >= fuzzy_threshold
                for cand in candidate_skills
            )
        )
        if required_matches < len(required_skills):
            continue

        # Preferred skills - count matches for scoring (but not filtering out)
        preferred_matches = sum(
            1
            for pref in preferred_skills
            if any(
                fuzz.ratio(pref.lower(), cand.lower()) >= fuzzy_threshold
                for cand in candidate_skills
            )
        )
        candidate["preferred_match_score"] = preferred_matches / max(
            1, len(preferred_skills)
        )

        filtered.append(candidate)
    return filtered
