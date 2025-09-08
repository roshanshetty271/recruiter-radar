"""
Lightweight, deterministic resume extraction utilities for the MVP fast path.

Functions here avoid LLM calls and aim to extract the most critical fields
from common resume layouts in milliseconds. Intended to be used BEFORE
any AI-based extraction.
"""

import re
from typing import Dict, Optional, Any, List, Tuple


def normalize_spaced_caps(line: str) -> str:
    """Normalize lines like "K I A N  W O O D S" -> "Kian Woods".

    This function detects sequences of single-uppercase letters separated by
    spaces and collapses them into words, then applies title casing.
    """
    if not line:
        return line

    # If the line is all caps with spaces between many letters, collapse them
    # Example: "K I A N  W O O D S" → "KIANWOODS" → "Kianwoods" → "Kian Woods"
    spaced_caps_pattern = r"^(?:[A-Z]\s+){2,}[A-Z](?:\s+[A-Z]\s*[A-Z]*)*$"
    if re.match(spaced_caps_pattern, line.strip()):
        # Collapse spaces and title-case the result. Do NOT attempt to split
        # into separate words here; downstream logic may derive proper spacing
        # from the email local-part when available.
        collapsed = re.sub(r"\s+", "", line)
        return collapsed.title()

    return line


def derive_name_from_email(email: Optional[str]) -> str:
    """Derive a human-readable name from an email local-part.

    Examples:
        "kianwoods@email.com" -> "Kian Woods"
        "john.smith@x.com" -> "John Smith"
        "mary_jane-doe@x.com" -> "Mary Jane Doe"
    """
    if not email or "@" not in email:
        return ""

    local = email.split("@", 1)[0]
    # Split on common separators
    parts = re.split(r"[._-]+", local)

    # Handle nickname/shortened name patterns for common cases
    if len(parts) == 2:
        part1, part2 = parts[0].lower(), parts[1].lower()

        # Common nickname expansions
        nickname_map = {
            "ros": "roshan",
            "rob": "robert",
            "mike": "michael",
            "dave": "david",
            "jim": "james",
            "tom": "thomas",
            "dan": "daniel",
            "chris": "christopher",
            "nick": "nicholas",
            "alex": "alexander",
        }

        # Check if either part is a nickname that should be expanded
        if part2 in nickname_map:
            # "shetty.ros" -> "Roshan Shetty" (expand nickname, put first)
            return f"{nickname_map[part2].capitalize()} {part1.capitalize()}"
        elif part1 in nickname_map:
            # "ros.shetty" -> "Roshan Shetty" (expand nickname, keep order)
            return f"{nickname_map[part1].capitalize()} {part2.capitalize()}"
    if len(parts) == 1:
        # Try to split concatenated lower/camel case into words
        camel_parts = re.findall(r"[A-Z][a-z]+|[a-z]+", local)
        if camel_parts and len(camel_parts) > 1:
            parts = camel_parts
        else:
            # Robust split for concatenated lowercase names like 'kianwoods'
            s = local
            if len(s) >= 6:
                mid = len(s) // 2
                vowels = set("aeiou")
                candidates = []
                # Consider indices near center first
                for delta in range(0, mid + 1):
                    for idx in (mid - delta, mid + delta):
                        if 2 <= idx <= len(s) - 2:
                            left, right = s[:idx], s[idx:]
                            score = 0
                            # Prefer balanced split
                            score -= abs(idx - mid)
                            # Reasonable part lengths
                            if 3 <= len(left) <= 7:
                                score += 3
                            if 3 <= len(right) <= 10:
                                score += 3
                            # Boundary phonetics
                            if left[-1] in vowels and right[0] not in vowels:
                                score += 2
                            if (
                                len(right) >= 2
                                and right[0] not in vowels
                                and right[1] in vowels
                            ):
                                score += 2
                            # Common first-name endings
                            if left[-1] in {"n", "r", "l", "m", "s", "y"}:
                                score += 1
                            candidates.append((score, idx))
                if candidates:
                    best_idx = max(candidates, key=lambda x: x[0])[1]
                    parts = [s[:best_idx], s[best_idx:]]

    parts = [p for p in parts if p]
    return " ".join(w.capitalize() for w in parts)


def _extract_email(lines: List[str]) -> Optional[str]:
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    for line in lines[:20]:
        m = re.search(email_pattern, line)
        if m:
            return m.group(0).lower()
    return None


def _extract_phone(lines: List[str]) -> Optional[str]:
    phone_pattern = r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    for line in lines[:20]:
        m = re.search(phone_pattern, line)
        if m:
            return m.group(0)
    return None


def _extract_location(lines: List[str]) -> Optional[str]:
    # Simple City, ST pattern
    loc_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b"
    for line in lines[:20]:
        m = re.search(loc_pattern, line)
        if m:
            return f"{m.group(1)}, {m.group(2)}"
    return None


def _looks_like_role(line: str) -> bool:
    role_keywords = (
        "engineer",
        "developer",
        "manager",
        "analyst",
        "designer",
        "scientist",
        "consultant",
        "architect",
    )
    lower = line.lower()
    return any(k in lower for k in role_keywords)


def _extract_name(lines: List[str], email: Optional[str]) -> Optional[str]:
    # Accept ALL-CAPS two/three-word line as a likely name if it appears at the very top
    for idx, line in enumerate(lines[:10]):
        normalized = normalize_spaced_caps(line.strip())
        if not normalized:
            continue
        # Skip obvious non-name headers
        if normalized.upper() in {"RESUME", "CURRICULUM VITAE", "CV", "PROFILE"}:
            continue

        words = normalized.split()
        if 1 < len(words) <= 4 and all(len(w) > 1 for w in words):
            if not _looks_like_role(normalized):
                # Permit ALL-CAPS names on the first couple of lines
                if idx <= 2 or not normalized.isupper():
                    return normalized.title() if normalized.isupper() else normalized

        # If we only have a single concatenated token (e.g., "Kianwoods"),
        # prefer deriving from email to avoid returning malformed names.
        if len(words) == 1 and email:
            derived = derive_name_from_email(email)
            if derived:
                return derived

    # Fallback from email local-part
    if email:
        derived = derive_name_from_email(email)
        if derived:
            # Try to improve using top header token if it looks like a concatenated name
            top = lines[0].replace(" ", "") if lines else ""
            top_alpha = re.sub(r"[^A-Za-z]", "", top)
            if top_alpha and top_alpha.isalpha() and len(top_alpha) >= 8:
                parts = derived.lower().split()
                if len(parts) == 2:
                    first_guess, last_guess = parts[0], parts[1]
                    # If the header token ends with last name, split there to recover full first name
                    idx = top_alpha.lower().rfind(last_guess)
                    if idx > 1:
                        first_full = top_alpha[:idx]
                        last_full = top_alpha[idx:]
                        if first_full and last_full:
                            return f"{first_full.capitalize()} {last_full.capitalize()}"
            return derived
    return None


def _extract_skills(lines: List[str]) -> List[str]:
    skills: List[str] = []
    in_skills = False
    for line in lines:
        upper = line.upper().strip()
        if re.match(r"^(SKILLS?|TECHNICAL SKILLS?|CORE COMPETENC)", upper):
            in_skills = True
            continue
        if in_skills:
            # Next section header typically all-caps line
            if re.match(r"^[A-Z][A-Z\s]{2,}$", upper) and len(upper) > 3:
                break
            parts = re.split(r"[,•·\u2022|]\s*", line)
            for p in parts:
                p_clean = p.strip()
                # Keep only short, skill-like tokens (<= 3 words, no periods)
                if (
                    len(p_clean) > 1
                    and "." not in p_clean
                    and len(p_clean.split()) <= 3
                ):
                    skills.append(p_clean)
            if len(skills) >= 30:
                break
    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for s in skills:
        sl = s.lower()
        if sl not in seen:
            seen.add(sl)
            unique.append(s)
    return unique[:30]


def try_fast_extraction(text: str) -> Optional[Dict[str, Any]]:
    """Attempt deterministic extraction from the first ~30 lines of text.

    Returns a dict with keys: name, email, phone, location, skills, confidence,
    fast_path. Returns None if minimum viable data (name+email) cannot be found.
    """
    if not text:
        return None

    # Consider only the top of the document where contact info typically resides
    raw_lines = [ln.strip() for ln in text.splitlines()][:30]
    lines = [normalize_spaced_caps(ln) for ln in raw_lines if ln]

    email = _extract_email(lines)
    phone = _extract_phone(lines)
    location = _extract_location(lines)
    name = _extract_name(lines, email)

    # Verbose diagnostics (optional)
    from app.core.config import settings

    if settings.app_verbose_extraction:
        import logging

        logging.getLogger(__name__).info(
            {
                "verbose_fast_extraction": True,
                "top_lines": lines[:8],
                "email": email,
                "phone": phone,
                "location": location,
                "name_candidate": name,
                # Note: work_experience will be extracted after basic validation
            }
        )
    if not (name and email):
        return None

    skills = _extract_skills(lines)

    # Extract structured data for better experience calculation and UI display
    work_experience = extract_work_experience(text)
    education = extract_education(text)
    certifications = extract_certifications(text)
    current_title = extract_current_title(text)

    # 🚀 ENHANCED: Calculate experience from structured work data with better parsing
    total_experience_years = 0.0  # Default to 0.0 to avoid validation errors
    if work_experience:
        total_months = 0
        from datetime import datetime
        import re as _re

        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # Month name to number mapping
        month_map = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }

        for w in work_experience:
            dur = (w.get("duration") or "").lower().strip()
            months_in_role = 0

            # 🚀 ENHANCED: Try multiple parsing strategies

            # Strategy 1: Full month-year format (Jan 2025 - May 2025)
            month_year_match = _re.search(
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(20\d{2})\s*[-–]\s*(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(20\d{2})|present|current)",
                dur,
                _re.IGNORECASE,
            )

            if month_year_match:
                start_month_str = month_year_match.group(1).lower()
                start_year = int(month_year_match.group(2))
                start_month = month_map.get(start_month_str, 1)

                if month_year_match.group(3):  # End month specified
                    end_month_str = month_year_match.group(3).lower()
                    end_year = int(month_year_match.group(4))
                    end_month = month_map.get(end_month_str, 12)
                else:  # Present/current
                    end_year = current_year
                    end_month = current_month

                # Calculate months difference
                months_in_role = (end_year - start_year) * 12 + (
                    end_month - start_month
                )
                if months_in_role < 0:
                    months_in_role = 0

            # Strategy 2: Year-only patterns (2021-2023)
            elif not month_year_match:
                year_match = _re.search(
                    r"(20\d{2}|19\d{2})\s*[-–]\s*(?:(20\d{2}|19\d{2})|present|current)",
                    dur,
                )

                if year_match:
                    start_year = int(year_match.group(1))
                    end_year = (
                        int(year_match.group(2))
                        if (year_match.group(2) and year_match.group(2).isdigit())
                        else current_year
                    )
                    if (
                        1990 <= start_year <= end_year <= current_year + 1
                    ):  # Allow future dates
                        months_in_role = (end_year - start_year) * 12

            # Strategy 3: Handle abbreviated years ('25 format)
            if months_in_role == 0:
                abbrev_match = _re.search(
                    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+['\"]?(\d{2})\s*[-–]\s*(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+['\"]?(\d{2})|present|current)",
                    dur,
                    _re.IGNORECASE,
                )

                if abbrev_match:
                    start_month_str = abbrev_match.group(1).lower()
                    start_year_abbrev = int(abbrev_match.group(2))
                    # Convert 2-digit year to 4-digit (assuming 20xx for years 00-50, 19xx for 51-99)
                    start_year = (
                        2000 + start_year_abbrev
                        if start_year_abbrev <= 50
                        else 1900 + start_year_abbrev
                    )
                    start_month = month_map.get(start_month_str, 1)

                    if abbrev_match.group(3):  # End month specified
                        end_month_str = abbrev_match.group(3).lower()
                        end_year_abbrev = int(abbrev_match.group(4))
                        end_year = (
                            2000 + end_year_abbrev
                            if end_year_abbrev <= 50
                            else 1900 + end_year_abbrev
                        )
                        end_month = month_map.get(end_month_str, 12)
                    else:  # Present/current
                        end_year = current_year
                        end_month = current_month

                    months_in_role = (end_year - start_year) * 12 + (
                        end_month - start_month
                    )
                    if months_in_role < 0:
                        months_in_role = 0

            # Add debug logging for experience calculation
            if settings.app_verbose_extraction and months_in_role > 0:
                import logging

                logging.getLogger(__name__).info(
                    f"🧮 ENHANCED EXP: '{dur}' → {months_in_role} months ({months_in_role/12:.1f} years)"
                )

            total_months += months_in_role

        if total_months > 0:
            total_experience_years = round(total_months / 12, 1)
            if settings.app_verbose_extraction:
                import logging

                logging.getLogger(__name__).info(
                    f"🎯 FINAL ENHANCED EXPERIENCE: {total_experience_years} years (computed from {total_months} total months)"
                )
        else:
            # If no structured experience found, try to estimate conservatively
            if len(work_experience) > 0:
                # Conservative estimate: 1-2 years per role
                total_experience_years = min(len(work_experience) * 1.5, 5.0)
                if settings.app_verbose_extraction:
                    import logging

                    logging.getLogger(__name__).info(
                        f"🧮 FALLBACK EXP: No dates parsed, using conservative estimate: {total_experience_years} years"
                    )

    confidence = 0.9 if (phone and location) else 0.75

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "skills": skills,
        "work_experience": work_experience,
        "education": education,
        "certifications": certifications,
        "current_title": current_title,
        "total_experience_years": total_experience_years,
        "confidence": confidence,
        "fast_path": True,
    }


# -------------------------
# Global section extraction
# -------------------------

_UPPER_HEADER_RE = re.compile(r"^[A-Z][A-Z\s&/\-]{2,}$")


def _find_section(lines: List[str], header_keywords: Tuple[str, ...]) -> List[str]:
    """Return the block of lines under a header until the next ALL-CAPS header."""
    start = None
    for i, ln in enumerate(lines):
        txt = ln.strip()
        if not txt:
            continue
        txt_upper = txt.upper()
        if any(k in txt_upper for k in header_keywords) and _UPPER_HEADER_RE.match(
            txt_upper
        ):
            start = i + 1
            break
    if start is None:
        return []
    block: List[str] = []
    for ln in lines[start:]:
        t = ln.strip()
        if not t:
            block.append("")
            continue
        if _UPPER_HEADER_RE.match(t):
            break
        block.append(ln)
    return block


def extract_skills_section(text: str) -> List[str]:
    lines = [ln.rstrip() for ln in text.splitlines()]
    block = _find_section(lines, ("SKILLS", "TECHNICAL SKILLS", "CORE COMPETENC"))
    if not block:
        return []
    skills: List[str] = []
    for ln in block:
        t = ln.strip().strip("•·•|")
        if not t:
            continue
        parts = re.split(r"[,•·\u2022|]\s*", t)
        for p in parts:
            p = p.strip()
            if not p or "." in p or len(p.split()) > 3:
                continue
            skills.append(p)
    # Dedup
    seen = set()
    uniq: List[str] = []
    for s in skills:
        sl = s.lower()
        if sl not in seen:
            seen.add(sl)
            uniq.append(s)
    return uniq[:50]


_MONTHS = r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"

# Enhanced date pattern to match various formats
_DATE_LINE_RE = re.compile(
    rf"(?:\b({_MONTHS})\s+)?(?:20\d{{2}}|19\d{{2}})\s*[-–]\s*(?:(?:({_MONTHS})\s+)?(?:20\d{{2}}|19\d{{2}})|present|current)",
    re.IGNORECASE,
)

# Additional fallback pattern for month-year formats - FIXED VERSION
_MONTH_YEAR_RE = re.compile(
    rf"({_MONTHS})\s+(20\d{{2}}|19\d{{2}})\s*[-–]\s*(?:({_MONTHS})\s+(20\d{{2}}|19\d{{2}})|present|current)",
    re.IGNORECASE,
)

# 🚀 NEW: More comprehensive date patterns to catch edge cases
_DATE_PATTERNS = [
    # Primary patterns
    re.compile(
        rf"({_MONTHS})\s+(20\d{{2}})\s*[-–]\s*({_MONTHS})\s+(20\d{{2}})", re.IGNORECASE
    ),
    re.compile(rf"({_MONTHS})\s+(20\d{{2}})\s*[-–]\s*(present|current)", re.IGNORECASE),
    # Year-only patterns
    re.compile(
        r"(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|19\d{2}|present|current)", re.IGNORECASE
    ),
    # Short year patterns (abbreviated '25)
    re.compile(
        rf"({_MONTHS})\s*['\"]?(\d{{2}})\s*[-–]\s*(?:({_MONTHS})\s*['\"]?(\d{{2}})|present|current)",
        re.IGNORECASE,
    ),
]

# 🚀 NEW: Company+Location+Dates parsing patterns
_COMPANY_LOCATION_DATE_PATTERNS = [
    # Pattern 1: "Company, City, State/Country Dates"
    re.compile(
        r"^(.+?),\s*([^,]+,\s*[A-Za-z\s]+?)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE
    ),
    # Pattern 2: "Company, Location Dates" (more flexible location)
    re.compile(r"^(.+?),\s*([^,]+)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE),
    # Pattern 3: "Company Location Dates" (no commas)
    re.compile(
        r"^(.+?)\s+([A-Z][a-z]+(?:,\s*[A-Z]{2})?)\s+(" + _MONTHS + r".*?)$",
        re.IGNORECASE,
    ),
    # Pattern 4: Just "Company Dates" (no location)
    re.compile(r"^(.+?)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE),
]


def _parse_company_location_dates_line(line: str) -> Optional[Dict[str, str]]:
    """
    Parse a line containing company, location, and dates information.

    Examples:
    - "Aosenuma, Texas, USA Jan 2025 - May 2025"
    - "Capgemini, Navi Mumbai, India Nov 2020 - Jun 2023"
    - "Google Inc, Mountain View, CA 2019 - Present"
    - "Microsoft Seattle, WA 2018 - 2020"

    Returns dict with keys: company, location, duration
    Or None if line doesn't match expected patterns.
    """
    if not line or not line.strip():
        return None

    line = line.strip()

    # 🚀 ENHANCED: Try comprehensive date detection first
    date_match = None
    date_start = None

    for pattern in _DATE_PATTERNS:
        match = pattern.search(line)
        if match:
            date_match = match
            date_start = match.start()
            break

    # If no date found, try original patterns
    if not date_match:
        date_match = _DATE_LINE_RE.search(line) or _MONTH_YEAR_RE.search(line)
        if date_match:
            date_start = date_match.start()

    if date_match and date_start is not None:
        # Split line at date boundary
        pre_date = line[:date_start].strip()
        duration = line[date_start:].strip()

        # Parse company and location from pre-date part
        company = ""
        location = ""

        # Look for comma-separated parts (company, location)
        if "," in pre_date:
            parts = [p.strip() for p in pre_date.split(",")]
            if len(parts) >= 2:
                company = parts[0]
                # Combine remaining parts as location
                location = ", ".join(parts[1:])
            else:
                company = parts[0]
        else:
            # No comma - might be "Company Location" format
            # Try to detect if last word(s) look like location
            words = pre_date.split()
            if len(words) >= 2:
                # Look for state abbreviations or common location patterns
                last_word = words[-1]
                if (
                    len(last_word) == 2 and last_word.isupper()
                ) or last_word.lower() in ["usa", "india", "canada", "uk"]:
                    # Last word is likely location
                    company = " ".join(words[:-1])
                    location = last_word
                elif len(words) >= 3 and words[-2].endswith(","):
                    # Pattern like "Company, City State"
                    company = " ".join(words[:-2]).rstrip(",")
                    location = " ".join(words[-2:])
                else:
                    # Default: treat all as company
                    company = pre_date
            else:
                company = pre_date

        if company:  # Only return if we found a company
            return {
                "company": company.strip(),
                "location": location.strip(),
                "duration": duration.strip(),
            }

    # Fallback: Try original pattern matching
    for i, pattern in enumerate(_COMPANY_LOCATION_DATE_PATTERNS):
        match = pattern.match(line)
        if match:
            groups = match.groups()

            if len(groups) == 3:  # Company, Location, Dates
                company = groups[0].strip()
                location = groups[1].strip()
                duration = groups[2].strip()

                # Validate that we actually found a date in the duration part
                date_found = any(p.search(duration) for p in _DATE_PATTERNS)
                if (
                    date_found
                    or _DATE_LINE_RE.search(duration)
                    or _MONTH_YEAR_RE.search(duration)
                ):
                    return {
                        "company": company,
                        "location": location,
                        "duration": duration,
                    }

            elif len(groups) == 2:  # Company, Dates (no location)
                company = groups[0].strip()
                duration = groups[1].strip()

                # Validate that we actually found a date in the duration part
                date_found = any(p.search(duration) for p in _DATE_PATTERNS)
                if (
                    date_found
                    or _DATE_LINE_RE.search(duration)
                    or _MONTH_YEAR_RE.search(duration)
                ):
                    return {"company": company, "location": "", "duration": duration}

    return None


def extract_work_experience(text: str) -> List[Dict[str, str]]:
    """Parse work experience entries with robust pattern recognition for various resume formats."""
    lines = [ln.strip() for ln in text.splitlines()]

    # Add verbose logging for section detection
    from app.core.config import settings

    if settings.app_verbose_extraction:
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 WORK EXP: Looking for section headers in {len(lines)} lines")
        # Show first 20 lines to debug
        for i, line in enumerate(lines[:20]):
            if line.strip():
                logger.info(f"  Line {i}: '{line.strip()}'")

    block = _find_section(
        lines, ("WORK EXPERIENCE", "EXPERIENCE", "PROFESSIONAL EXPERIENCE")
    )

    if settings.app_verbose_extraction:
        if not block:
            logger.info(
                "🚨 WORK EXP: No section found with headers: WORK EXPERIENCE, EXPERIENCE, PROFESSIONAL EXPERIENCE"
            )
            # Try to find any lines that might be experience headers
            for i, line in enumerate(lines):
                line_upper = line.strip().upper()
                if any(
                    keyword in line_upper
                    for keyword in [
                        "WORK",
                        "EXPERIENCE",
                        "PROFESSIONAL",
                        "EMPLOYMENT",
                        "CAREER",
                    ]
                ):
                    logger.info(
                        f"  Found potential header at line {i}: '{line.strip()}'"
                    )
        else:
            logger.info(f"✅ WORK EXP: Found section with {len(block)} lines")
            for i, line in enumerate(block[:10]):
                logger.info(f"  Block line {i}: '{line.strip()}'")

    if not block:
        return []

    entries: List[Dict[str, str]] = []

    # Common job title patterns (not exhaustive, but covers most roles)
    job_title_patterns = [
        r"\b(?:senior|lead|principal|chief|head of|director of)?\s*(?:software|web|mobile|backend|frontend|full.?stack|data|machine learning|ai|ml)?\s*(?:engineer|developer|scientist|analyst|architect|manager|consultant|specialist|intern|associate)\b",
        r"\b(?:product|project|program|technical|engineering)?\s*(?:manager|lead|director|coordinator|assistant)\b",
        r"\b(?:business|systems?|data|financial|marketing|sales|hr|human resources)?\s*(?:analyst|associate|specialist|coordinator|manager)\b",
        r"\b(?:ui/ux|ux|ui)?\s*(?:designer|design|researcher)\b",
        r"\b(?:devops|sre|site reliability)\s*(?:engineer|specialist)\b",
        r"\b(?:qa|quality assurance|test|testing)\s*(?:engineer|analyst|specialist)\b",
    ]

    # Compile job title regex
    job_title_regex = re.compile("|".join(job_title_patterns), re.IGNORECASE)

    # Method 1: Enhanced dual-direction parsing
    i = 0
    while i < len(block):
        line = block[i].strip()
        if not line or line.startswith("•") or line.startswith("-"):
            i += 1
            continue

        # 🚀 NEW: Check for line pairs (current + next) in both directions
        if i < len(block) - 1:
            next_line = block[i + 1].strip()
            if (
                next_line
                and not next_line.startswith("•")
                and not next_line.startswith("-")
            ):

                # Direction A: Company+Location+Dates first, then Job Title
                company_date_entry = _parse_company_location_dates_line(line)
                if company_date_entry and job_title_regex.search(next_line):
                    entries.append(
                        {
                            "title": next_line.strip(),
                            "company": company_date_entry["company"],
                            "duration": company_date_entry["duration"],
                            "location": company_date_entry.get("location", ""),
                        }
                    )

                    if settings.app_verbose_extraction:
                        logger.info(f"✅ DIRECTION A: Found company+title pair:")
                        logger.info(
                            f"   Line {i}: '{line}' → Company: '{company_date_entry['company']}', Location: '{company_date_entry['location']}'"
                        )
                        logger.info(f"   Line {i+1}: '{next_line}' → Job Title")
                        logger.info(
                            f"   🚀 SIMPLIFIED: No duration extraction needed for individual entries"
                        )

                    i += 2  # Skip both lines since we processed them
                    continue

                # Direction B: Traditional Job Title first, then Company+Dates
                if job_title_regex.search(line):
                    company_date_entry = _parse_company_location_dates_line(next_line)
                    if company_date_entry:
                        entries.append(
                            {
                                "title": line.strip(),
                                "company": company_date_entry["company"],
                                "duration": company_date_entry["duration"],
                                "location": company_date_entry.get("location", ""),
                            }
                        )

                        if settings.app_verbose_extraction:
                            logger.info(
                                f"✅ DIRECTION B: Found title+company+dates pair:"
                            )
                            logger.info(f"   Line {i}: '{line}' → Job Title")
                            logger.info(
                                f"   Line {i+1}: '{next_line}' → {company_date_entry}"
                            )

                        i += 2  # Skip both lines since we processed them
                        continue

        # Fallback: Original single-line job title detection
        title_match = job_title_regex.search(line)
        if title_match:
            title = line.strip()
            company = ""
            duration = ""

            # Look ahead for company and duration in next few lines
            for j in range(i + 1, min(i + 4, len(block))):
                next_line = block[j].strip()
                if (
                    not next_line
                    or next_line.startswith("•")
                    or next_line.startswith("-")
                ):
                    continue

                # Check if this line contains a date pattern
                date_match = _DATE_LINE_RE.search(next_line) or _MONTH_YEAR_RE.search(
                    next_line
                )
                if date_match:
                    # Add debug logging
                    from app.core.config import settings

                    if settings.app_verbose_extraction:
                        import logging

                        logging.getLogger(__name__).info(
                            f"🔍 Found date line: '{next_line}'"
                        )

                    # This line likely contains company + duration
                    # Common patterns:
                    # "Company Name, Location     Jan 2020 - Dec 2022"
                    # "Company Name               2020-2022"
                    # "Company, City, State       Jan 2020 - Present"

                    # Split on multiple spaces or tabs (common formatting)
                    parts = re.split(r"\s{2,}|\t+", next_line)
                    if len(parts) >= 2:
                        company = parts[0].strip()
                        duration = parts[-1].strip()
                        if settings.app_verbose_extraction:
                            logging.getLogger(__name__).info(
                                f"🏢 Split method: company='{company}', duration='{duration}'"
                            )
                    else:
                        # Try to separate company from date in single line
                        # Look for date pattern and split there
                        date_start = date_match.start()
                        company = next_line[:date_start].strip()
                        duration = next_line[date_start:].strip()
                        if settings.app_verbose_extraction:
                            logging.getLogger(__name__).info(
                                f"🏢 Pattern method: company='{company}', duration='{duration}'"
                            )
                    break
                elif not company:
                    # This might be the company line (no dates)
                    # Skip obvious bullet points or description lines
                    if (
                        len(next_line) < 150
                        and not next_line.startswith(("•", "-", "●", "*", "◦"))
                        and not next_line.lower().startswith(
                            (
                                "responsible",
                                "led",
                                "managed",
                                "developed",
                                "created",
                                "built",
                                "designed",
                                "implemented",
                                "achieved",
                                "improved",
                                "collaborated",
                                "worked",
                                "utilized",
                                "maintained",
                            )
                        )
                        and
                        # Look for company-like patterns (contains common company indicators)
                        any(
                            indicator in next_line.lower()
                            for indicator in [
                                "inc",
                                "corp",
                                "ltd",
                                "llc",
                                "company",
                                "technologies",
                                "systems",
                                "solutions",
                                "services",
                                "consulting",
                                "university",
                                "college",
                                "institute",
                                ",",
                            ]
                        )
                    ):
                        company = next_line

            # Clean up extracted data
            title = re.sub(r"\s+", " ", title)
            company = re.sub(r"\s+", " ", company) if company else ""
            duration = re.sub(r"\s+", " ", duration) if duration else ""

            # Remove common suffixes from company names
            if company:
                company = re.sub(
                    r",?\s*(?:Inc\.?|LLC|Corp\.?|Ltd\.?|Co\.?)?\s*$",
                    "",
                    company,
                    flags=re.IGNORECASE,
                )
                # Remove location info (City, State pattern at end)
                company = re.sub(
                    r",\s*[A-Z][a-z]+,?\s*[A-Z]{2}(?:\s+\d{5})?$", "", company
                )

            if title:  # Only add if we found a title
                entries.append(
                    {
                        "title": title,
                        "company": company or "Company",
                        "duration": duration or "Duration not specified",
                    }
                )

            # Skip ahead to avoid processing the same entry
            i = j if "j" in locals() else i + 1
        else:
            i += 1

    # Method 2: Enhanced fallback - Look for company + date patterns
    if not entries:
        # Look for lines that contain company names with location and dates
        for i, line in enumerate(block):
            line = line.strip()
            if not line or line.startswith(("•", "-", "●")):
                continue

            # Pattern: "Company Name, Location   Date Range"
            # Example: "Capgemini, Navi Mumbai, India   Nov 2020 - Jun 2023"
            date_match = _DATE_LINE_RE.search(line) or _MONTH_YEAR_RE.search(line)
            if date_match:
                # Add debug logging
                from app.core.config import settings

                if settings.app_verbose_extraction:
                    import logging

                    logging.getLogger(__name__).info(
                        f"🎯 Method 2 found date line: '{line}'"
                    )
                    date_start = date_match.start()
                    company_part = line[:date_start].strip()
                    duration_part = line[date_start:].strip()

                    # Clean up company name (remove location)
                    company_clean = re.sub(
                        r",\s*[A-Z][a-z]+(?:,?\s*[A-Z]{2,})?(?:\s+\d{5})?$",
                        "",
                        company_part,
                    )

                    # Look backwards for a job title
                    title = "Position"  # Default
                    for j in range(i - 1, max(i - 4, -1), -1):
                        if j >= 0:
                            prev_line = block[j].strip()
                            if (
                                prev_line
                                and not prev_line.startswith(("•", "-", "●"))
                                and job_title_regex.search(prev_line)
                            ):
                                title = prev_line
                                break

                    if company_clean:
                        entries.append(
                            {
                                "title": title,
                                "company": company_clean,
                                "duration": duration_part,
                            }
                        )

        # Method 3: Last resort - inline patterns
        if not entries:
            for line in block:
                line = line.strip()
                if not line or line.startswith(("•", "-", "●")):
                    continue

                # Pattern: "Position at Company (dates)" or "Position, Company (dates)"
                patterns = [
                    r"(.+?)\s+at\s+(.+?)\s*[\(\[](.+?)[\)\]]",
                    r"(.+?),\s*(.+?)\s*[\(\[](.+?)[\)\]]",
                    r"(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)",  # Title | Company | Dates
                ]

                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match and job_title_regex.search(match.group(1)):
                        title = match.group(1).strip()
                        company = match.group(2).strip()
                        duration = match.group(3).strip()

                        entries.append(
                            {"title": title, "company": company, "duration": duration}
                        )
                        break

    return entries


def _parse_degree_and_field(degree_line: str) -> tuple[str, str]:
    """
    Enhanced degree and field parsing with multiple patterns.

    Examples:
    - "Master of Science in Information Systems" → ("Master of Science", "Information Systems")
    - "Master's in Computer Science" → ("Master's", "Computer Science")
    - "B.S. Computer Science" → ("B.S.", "Computer Science")
    - "PhD Computer Science" → ("PhD", "Computer Science")

    Returns tuple: (degree, field)
    """
    if not degree_line or not degree_line.strip():
        return "", ""

    degree_line = degree_line.strip()

    # 🚀 ENHANCED PATTERNS (in order of preference):
    patterns = [
        # Pattern 1: "Master of Science in Information Systems" (complete degree + field)
        re.compile(
            r"((?:Master|Bachelor|Associate|Doctorate|PhD|Ph\.D)\s+of\s+[^,]+?)\s+in\s+(.+?)(?:\s+GPA.*)?$",
            re.IGNORECASE,
        ),
        # Pattern 2: "Master's in Computer Science"
        re.compile(
            r"((?:Master|Bachelor|Associate|Doctorate|PhD|Ph\.D)'?s?)\s+in\s+(.+?)(?:\s+GPA.*)?$",
            re.IGNORECASE,
        ),
        # Pattern 3: "B.S. Computer Science", "M.S. Information Systems" (abbreviations)
        re.compile(
            r"([BMPA]\.?[SAM]\.?(?:\s+\w+)?)\s+(.+?)(?:\s+GPA.*)?$", re.IGNORECASE
        ),
        # Pattern 4: "PhD Computer Science", "Doctorate Engineering" (no connecting words)
        re.compile(
            r"(PhD|Ph\.D|Doctorate|Masters?|Bachelors?)\s+(.+?)(?:\s+GPA.*)?$",
            re.IGNORECASE,
        ),
        # Pattern 5: Original fallback - generic "X in/of Y" or "X Y"
        re.compile(r"(.*?)\s+(?:in|of)\s+(.*?)(?:\s+GPA.*)?$", re.IGNORECASE),
    ]

    # Try each pattern in order
    for i, pattern in enumerate(patterns):
        match = pattern.match(degree_line)
        if match:
            degree = match.group(1).strip()
            field = match.group(2).strip()

            # Basic validation - make sure we got reasonable results
            if degree and field and len(degree) > 1 and len(field) > 1:
                # Clean up common issues
                degree = degree.replace("  ", " ")  # Remove double spaces
                field = field.replace("  ", " ")

                from app.core.config import settings

                if settings.app_verbose_extraction:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"🎓 PATTERN {i+1} SUCCESS: '{degree_line}' → degree='{degree}', field='{field}'"
                    )

                return degree, field

    # Final fallback: Use manual field extraction for known patterns
    field = ""
    degree = degree_line

    # Extract common fields
    degree_lower = degree_line.lower()
    if "information systems" in degree_lower:
        field = "Information Systems"
        degree = (
            degree_line.replace("Information Systems", "")
            .replace("information systems", "")
            .strip()
        )
    elif "computer science" in degree_lower:
        field = "Computer Science"
        degree = (
            degree_line.replace("Computer Science", "")
            .replace("computer science", "")
            .strip()
        )
    elif "engineering" in degree_lower:
        field = "Engineering"
        degree = (
            degree_line.replace("Engineering", "").replace("engineering", "").strip()
        )
    elif "business" in degree_lower:
        field = "Business"
        degree = degree_line.replace("Business", "").replace("business", "").strip()
    elif "mathematics" in degree_lower:
        field = "Mathematics"
        degree = (
            degree_line.replace("Mathematics", "").replace("mathematics", "").strip()
        )

    # Clean up degree
    degree = re.sub(r"\s+", " ", degree).strip()  # Remove extra whitespace
    degree = re.sub(r"\s+GPA.*$", "", degree, flags=re.IGNORECASE)  # Remove GPA

    from app.core.config import settings

    if settings.app_verbose_extraction:
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"🎓 FALLBACK: '{degree_line}' → degree='{degree}', field='{field}'"
        )

    return degree, field


def extract_education(text: str) -> List[Dict[str, Optional[str]]]:
    lines = [ln.strip() for ln in text.splitlines()]
    block = _find_section(lines, ("EDUCATION",))
    if not block:
        return []

    entries = []

    # Enhanced parsing for multiple education entries
    for i, line in enumerate(block):
        line = line.strip()
        if not line:
            continue

        line_lower = line.lower()

        # Look for university/school lines first
        if any(
            keyword in line_lower
            for keyword in ["university", "college", "institute", "school"]
        ):
            school_line = line
            degree_line = ""
            graduation_year = None
            field = ""

            # 🚀 ENHANCED: Look FORWARD for degree line (common resume format)
            # Many resumes have: University line first, then Degree line
            for j in range(i + 1, min(i + 4, len(block))):
                if j < len(block):
                    next_line = block[j].strip()
                    if next_line and any(
                        deg_kw in next_line.lower()
                        for deg_kw in [
                            "bachelor",
                            "master",
                            "b.s",
                            "m.s",
                            "b.a",
                            "m.a",
                            "phd",
                            "ph.d",
                            "doctorate",
                        ]
                    ):
                        degree_line = next_line
                        break

            # If not found forward, try backwards (fallback)
            if not degree_line:
                for j in range(i - 1, max(i - 3, -1), -1):
                    if j >= 0:
                        prev_line = block[j].strip()
                        if prev_line and any(
                            deg_kw in prev_line.lower()
                            for deg_kw in [
                                "bachelor",
                                "master",
                                "b.s",
                                "m.s",
                                "b.a",
                                "m.a",
                                "phd",
                                "ph.d",
                                "doctorate",
                            ]
                        ):
                            degree_line = prev_line
                            break

            # 🚀 SIMPLIFIED: No graduation year extraction needed
            graduation_year = None  # User doesn't need individual graduation years

            # Simple debug logging
            from app.core.config import settings

            if settings.app_verbose_extraction:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"🎓 SIMPLIFIED: Processing school line: '{school_line}' (no date extraction needed)"
                )

            # Parse degree and field
            if degree_line:
                # Add debug logging
                from app.core.config import settings

                if settings.app_verbose_extraction:
                    import logging

                    logging.getLogger(__name__).info(
                        f"🎓 PARSING: degree_line='{degree_line}'"
                    )

                # 🚀 ENHANCED: Multi-pattern degree parsing
                degree, field = _parse_degree_and_field(degree_line)

                if settings.app_verbose_extraction:
                    logging.getLogger(__name__).info(
                        f"🎓 ENHANCED PARSING: degree='{degree}', field='{field}'"
                    )
            else:
                degree = ""

            # 🚀 SIMPLIFIED: Basic school name cleanup (remove dates since we don't need them)
            school_clean = school_line

            # Remove common trailing date patterns to keep school name clean
            school_clean = re.sub(
                r"\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*['\"]?\d{2}$",
                "",
                school_clean,
                flags=re.IGNORECASE,
            )
            school_clean = re.sub(r"\s+(19|20)\d{2}$", "", school_clean)
            school_clean = re.sub(r"\s+", " ", school_clean).strip()

            if settings.app_verbose_extraction:
                logger.info(
                    f"🎓 SIMPLIFIED CLEANUP: '{school_line}' → '{school_clean}'"
                )

            if school_clean or degree:
                # Add comprehensive debug logging
                if settings.app_verbose_extraction:
                    logger.info(f"🎓 EDUCATION SUMMARY:")
                    logger.info(f"   Original school line: '{school_line}'")
                    logger.info(f"   Cleaned school: '{school_clean}'")
                    logger.info(f"   Degree line found: '{degree_line}'")
                    logger.info(f"   Parsed degree: '{degree}'")
                    logger.info(f"   Parsed field: '{field}'")
                    logger.info(f"   Graduation year: '{graduation_year}'")
                    logger.info(f"   Entry will be added: Yes")

                entries.append(
                    {
                        "degree": degree,
                        "field": field,
                        "school": school_clean,
                        "graduation_year": graduation_year,
                    }
                )
            elif settings.app_verbose_extraction:
                logger.info(f"🎓 EDUCATION SKIPPED:")
                logger.info(f"   School line: '{school_line}'")
                logger.info(
                    f"   Reason: No school_clean ('{school_clean}') or degree ('{degree}') found"
                )

    return entries


def extract_certifications(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    block = _find_section(lines, ("CERTIFICATIONS",))
    if not block:
        return []
    certs: List[str] = []
    for ln in block:
        t = ln.strip().strip("•·|")
        if not t:
            continue
        if len(t) > 2 and len(t.split()) <= 12:
            certs.append(t)
    return certs[:20]


def extract_headline(text: str, name: Optional[str]) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines()[:15]]
    # Find the first non-empty line after the name that is short and not a section header
    name_idx = None
    if name:
        n_upper = name.upper()
        for i, ln in enumerate(lines):
            if ln.replace(" ", "").upper() == n_upper.replace(" ", ""):
                name_idx = i
                break
    start = 0 if name_idx is None else name_idx + 1
    for ln in lines[start : start + 5]:
        if not ln or _UPPER_HEADER_RE.match(ln):
            continue
        # Skip contact-like lines
        lower = ln.lower()
        if any(
            k in lower for k in ("@", "linkedin", "http", "www.", ".com", ".io", ".org")
        ):
            continue
        if any(ch.isdigit() for ch in ln):
            continue
        if len(ln.split()) <= 6:
            return ln.title() if ln.isupper() else ln
    return None


def extract_current_title(text: str) -> Optional[str]:
    """Extract current job title from the most recent work experience entry."""
    work_entries = extract_work_experience(text)
    if not work_entries:
        return None

    # Look for the most recent role (first entry or one with "present"/"current")
    for entry in work_entries:
        duration = entry.get("duration", "").lower()
        if "present" in duration or "current" in duration:
            return entry.get("title")

    # If no "current" role found, return the first entry (assumed most recent)
    if work_entries:
        return work_entries[0].get("title")

    return None
