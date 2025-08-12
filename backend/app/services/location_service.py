"""
Smart Location Mapping Service for RecruiterRadar MVP.

Handles location normalization, expansion, and intelligent matching for search filters.
Solves the critical issue where "California" searches fail to match "San Francisco, CA" candidates.
"""

from typing import Dict, List, Optional, Set, Tuple
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class LocationMappingService:
    """
    🗺️ SMART LOCATION MAPPING SERVICE

    Provides intelligent location matching, normalization, and expansion
    to fix critical location filtering issues in candidate search.
    """

    def __init__(self):
        """Initialize the location mapping service with comprehensive data."""
        self.state_abbreviations = self._build_state_abbreviations()
        self.city_to_state = self._build_city_to_state_mapping()
        self.location_aliases = self._build_location_aliases()
        self.region_mappings = self._build_region_mappings()

    def _build_state_abbreviations(self) -> Dict[str, str]:
        """Build comprehensive US state abbreviation mapping."""
        return {
            # US States - Full name to abbreviation
            "alabama": "AL",
            "alaska": "AK",
            "arizona": "AZ",
            "arkansas": "AR",
            "california": "CA",
            "colorado": "CO",
            "connecticut": "CT",
            "delaware": "DE",
            "florida": "FL",
            "georgia": "GA",
            "hawaii": "HI",
            "idaho": "ID",
            "illinois": "IL",
            "indiana": "IN",
            "iowa": "IA",
            "kansas": "KS",
            "kentucky": "KY",
            "louisiana": "LA",
            "maine": "ME",
            "maryland": "MD",
            "massachusetts": "MA",
            "michigan": "MI",
            "minnesota": "MN",
            "mississippi": "MS",
            "missouri": "MO",
            "montana": "MT",
            "nebraska": "NE",
            "nevada": "NV",
            "new hampshire": "NH",
            "new jersey": "NJ",
            "new mexico": "NM",
            "new york": "NY",
            "north carolina": "NC",
            "north dakota": "ND",
            "ohio": "OH",
            "oklahoma": "OK",
            "oregon": "OR",
            "pennsylvania": "PA",
            "rhode island": "RI",
            "south carolina": "SC",
            "south dakota": "SD",
            "tennessee": "TN",
            "texas": "TX",
            "utah": "UT",
            "vermont": "VT",
            "virginia": "VA",
            "washington": "WA",
            "west virginia": "WV",
            "wisconsin": "WI",
            "wyoming": "WY",
            "district of columbia": "DC",
            "washington dc": "DC",
            # Reverse mapping - Abbreviation to full name
            "al": "Alabama",
            "ak": "Alaska",
            "az": "Arizona",
            "ar": "Arkansas",
            "ca": "California",
            "co": "Colorado",
            "ct": "Connecticut",
            "de": "Delaware",
            "fl": "Florida",
            "ga": "Georgia",
            "hi": "Hawaii",
            "id": "Idaho",
            "il": "Illinois",
            "in": "Indiana",
            "ia": "Iowa",
            "ks": "Kansas",
            "ky": "Kentucky",
            "la": "Louisiana",
            "me": "Maine",
            "md": "Maryland",
            "ma": "Massachusetts",
            "mi": "Michigan",
            "mn": "Minnesota",
            "ms": "Mississippi",
            "mo": "Missouri",
            "mt": "Montana",
            "ne": "Nebraska",
            "nv": "Nevada",
            "nh": "New Hampshire",
            "nj": "New Jersey",
            "nm": "New Mexico",
            "ny": "New York",
            "nc": "North Carolina",
            "nd": "North Dakota",
            "oh": "Ohio",
            "ok": "Oklahoma",
            "or": "Oregon",
            "pa": "Pennsylvania",
            "ri": "Rhode Island",
            "sc": "South Carolina",
            "sd": "South Dakota",
            "tn": "Tennessee",
            "tx": "Texas",
            "ut": "Utah",
            "vt": "Vermont",
            "va": "Virginia",
            "wa": "Washington",
            "wv": "West Virginia",
            "wi": "Wisconsin",
            "wy": "Wyoming",
            "dc": "Washington DC",
        }

    def _build_city_to_state_mapping(self) -> Dict[str, str]:
        """Build major city to state mapping for tech hubs."""
        return {
            # California Tech Hubs
            "san francisco": "CA",
            "sf": "CA",
            "palo alto": "CA",
            "mountain view": "CA",
            "cupertino": "CA",
            "santa clara": "CA",
            "san jose": "CA",
            "los angeles": "CA",
            "la": "CA",
            "hollywood": "CA",
            "santa monica": "CA",
            "irvine": "CA",
            "san diego": "CA",
            "sacramento": "CA",
            "oakland": "CA",
            "berkeley": "CA",
            # New York
            "new york": "NY",
            "nyc": "NY",
            "manhattan": "NY",
            "brooklyn": "NY",
            "queens": "NY",
            "bronx": "NY",
            "staten island": "NY",
            "buffalo": "NY",
            "albany": "NY",
            "rochester": "NY",
            "syracuse": "NY",
            # Texas
            "austin": "TX",
            "atx": "TX",
            "houston": "TX",
            "dallas": "TX",
            "san antonio": "TX",
            "fort worth": "TX",
            "el paso": "TX",
            # Washington
            "seattle": "WA",
            "bellevue": "WA",
            "redmond": "WA",
            "tacoma": "WA",
            "spokane": "WA",
            "vancouver": "WA",
            # Other Major Tech Cities
            "boston": "MA",
            "cambridge": "MA",
            "chicago": "IL",
            "denver": "CO",
            "boulder": "CO",
            "atlanta": "GA",
            "miami": "FL",
            "orlando": "FL",
            "tampa": "FL",
            "phoenix": "AZ",
            "portland": "OR",
            "nashville": "TN",
            "raleigh": "NC",
            "charlotte": "NC",
            "columbus": "OH",
            "cleveland": "OH",
            "detroit": "MI",
            "minneapolis": "MN",
            "salt lake city": "UT",
            "las vegas": "NV",
            "baltimore": "MD",
            "philadelphia": "PA",
            "pittsburgh": "PA",
            "richmond": "VA",
            "indianapolis": "IN",
            # Special cases
            "washington": "DC",
            "washington dc": "DC",
            "dc": "DC",
        }

    def _build_location_aliases(self) -> Dict[str, List[str]]:
        """Build location aliases and nicknames."""
        return {
            "bay area": [
                "san francisco",
                "palo alto",
                "mountain view",
                "san jose",
                "california",
                "ca",
            ],
            "silicon valley": [
                "palo alto",
                "mountain view",
                "cupertino",
                "santa clara",
                "san jose",
                "california",
                "ca",
            ],
            "dmv": ["washington", "dc", "maryland", "virginia"],
            "tri-state": ["new york", "new jersey", "connecticut"],
            "greater boston": ["boston", "cambridge", "massachusetts", "ma"],
            "socal": ["los angeles", "san diego", "orange county", "california", "ca"],
            "norcal": ["san francisco", "bay area", "sacramento", "california", "ca"],
            "pacific northwest": ["seattle", "portland", "washington", "oregon"],
            "research triangle": [
                "raleigh",
                "durham",
                "chapel hill",
                "north carolina",
                "nc",
            ],
        }

    def _build_region_mappings(self) -> Dict[str, List[str]]:
        """Build broader regional mappings."""
        return {
            # Only include explicit regional terms to avoid over-matching
            "west coast": ["california", "washington", "oregon"],
            # Remove overly broad "east coast" that was matching NY with VA
            # "east coast": [...] - Removed to prevent over-matching
            "midwest": ["illinois", "michigan", "ohio", "wisconsin", "minnesota"],
            "southwest": ["texas", "arizona", "nevada", "new mexico"],
            "southeast": ["florida", "georgia", "north carolina", "south carolina"],
        }

    def normalize_location(self, location: str) -> str:
        """
        🎯 NORMALIZE LOCATION to standard format.

        Args:
            location: Raw location string (e.g., "California", "ca", "Bay Area")

        Returns:
            Normalized location string
        """
        if not location:
            return ""

        location_lower = location.lower().strip()

        # Handle special work arrangements
        work_arrangements = {
            "remote": "Remote",
            "work from home": "Remote",
            "wfh": "Remote",
            "hybrid": "Hybrid",
            "onsite": "On-site",
            "on-site": "On-site",
        }

        if location_lower in work_arrangements:
            return work_arrangements[location_lower]

        # Handle state abbreviations
        if location_lower in self.state_abbreviations:
            return self.state_abbreviations[location_lower]

        # Handle city to state mapping
        if location_lower in self.city_to_state:
            state_abbrev = self.city_to_state[location_lower]
            return f"{location.title()}, {state_abbrev}"

        # Return title case as fallback
        return location.title()

    def expand_location_for_matching(self, search_location: str) -> Set[str]:
        """
        🔍 EXPAND LOCATION for comprehensive matching.

        Converts a search location into all possible variations to match against.
        This is the KEY function that fixes the "California" vs "CA" issue.

        Args:
            search_location: Location from search query

        Returns:
            Set of all possible location variations to check
        """
        if not search_location:
            return set()

        search_lower = search_location.lower().strip()

        # 🚀 PERFORMANCE: Check cache first to avoid re-expanding same location
        if hasattr(self, "_expansion_cache") and search_lower in self._expansion_cache:
            return self._expansion_cache[search_lower]

        if not hasattr(self, "_expansion_cache"):
            self._expansion_cache = {}

        variations = {search_lower, search_location}

        # 🔧 Only log for first expansion of each unique location
        should_log = search_lower not in self._expansion_cache
        if should_log:
            logger.info(f"🔍 Expanding location '{search_location}' for matching...")

        # ⚠️ Handle suspicious short queries that might be typos
        if len(search_lower) <= 2 and search_lower in ["me", "us", "we", "my", "or"]:
            if should_log:
                logger.warning(
                    f"   ⚠️ Ambiguous short location '{search_location}' - may be a typo"
                )
                logger.info(
                    f"   💡 Consider: Are you looking for a specific city or state?"
                )

        # Add state abbreviations (but be cautious with very short queries)
        if search_lower in self.state_abbreviations:
            state_result = self.state_abbreviations[search_lower]
            # Only add state expansion if it's not a suspicious short query
            if len(search_lower) > 2 or search_lower not in [
                "me",
                "us",
                "we",
                "my",
                "or",
            ]:
                variations.add(state_result.lower())
                variations.add(state_result.upper())
                if should_log:
                    logger.info(f"   ✅ Added state variation: {state_result}")
            elif should_log:
                logger.info(
                    f"   ⚠️ Skipped ambiguous state expansion: {state_result} (query too short/ambiguous)"
                )

        # Add city-based expansions
        if search_lower in self.city_to_state:
            state_abbrev = self.city_to_state[search_lower]
            variations.add(state_abbrev.lower())
            variations.add(state_abbrev.upper())
            if should_log:
                logger.info(f"   ✅ Added city-to-state: {state_abbrev}")

        # Add alias expansions
        for alias, expansions in self.location_aliases.items():
            if search_lower == alias or search_lower in expansions:
                variations.update(expansions)
                variations.add(alias)
                if should_log:
                    logger.info(f"   ✅ Added alias expansions: {expansions}")

        # Add regional expansions
        for region, states in self.region_mappings.items():
            if search_lower == region or search_lower in states:
                variations.update(states)
                variations.add(region)
                if should_log:
                    logger.info(f"   ✅ Added regional expansions: {states}")

        # Remove empty strings
        variations = {v for v in variations if v and v.strip()}

        # 🚀 PERFORMANCE: Cache the result for future use
        self._expansion_cache[search_lower] = variations

        if should_log:
            logger.info(f"   🎯 Final variations: {sorted(variations)}")
        return variations

    def location_matches(
        self,
        search_location: str,
        candidate_location: str,
        confidence_threshold: float = 0.7,
    ) -> Tuple[bool, float, str]:
        """
        🎯 PRECISE LOCATION MATCHING with strict city matching.

        FIXED: Previous version was too permissive and caused "Boston" to match "Houston".
        Now uses precise matching with proper validation.

        Args:
            search_location: Location from search query (e.g., "Boston")
            candidate_location: Location from candidate profile (e.g., "Boston, MA")
            confidence_threshold: Minimum confidence for a match

        Returns:
            Tuple of (matches: bool, confidence: float, reason: str)
        """
        if not search_location or not candidate_location:
            return False, 0.0, "Empty location"

        search_lower = search_location.lower().strip()
        candidate_lower = candidate_location.lower().strip()

        # 1. EXACT MATCH (highest confidence)
        if search_lower == candidate_lower:
            return True, 1.0, "Exact match"

        # 2. PRECISE CITY MATCHING - Handle common formats
        # "Boston" should match "Boston, MA" but NOT "Houston, TX"
        if self._is_precise_city_match(search_lower, candidate_lower):
            return True, 0.95, "Precise city match"

        # 3. STATE EXPANSION MATCHING
        # "California" should match "San Francisco, CA"
        search_variations = self.expand_location_for_matching(search_location)
        for variation in search_variations:
            variation_lower = variation.lower()

            # Check if state/region in candidate location
            if self._is_state_region_match(variation_lower, candidate_lower):
                confidence = 0.9 if len(variation) > 2 else 0.7
                return True, confidence, f"State/region match: '{variation}'"

        # 4. METROPOLITAN AREA MATCHING
        # "Bay Area" should match "San Francisco, CA"
        if self._is_metro_area_match(search_lower, candidate_lower):
            return True, 0.85, "Metropolitan area match"

        # 5. CAREFUL FUZZY MATCHING (very strict threshold)
        # Only allow very high similarity to prevent false matches
        similarity = SequenceMatcher(None, search_lower, candidate_lower).ratio()
        if similarity >= 0.9:  # Much stricter threshold
            return True, similarity, f"High fuzzy match: {similarity:.2f}"

        # 6. NO DANGEROUS PARTIAL MATCHING
        # Removed the previous partial word matching that caused Boston->Houston false matches

        return False, 0.0, f"No match (similarity: {similarity:.2f})"

    def _is_precise_city_match(self, search_city: str, candidate_location: str) -> bool:
        """
        Check if search city precisely matches the candidate location.

        Examples:
        - "boston" matches "boston, ma" ✅
        - "boston" matches "houston, tx" ❌
        - "san francisco" matches "san francisco, ca" ✅
        """
        # Split candidate location by common separators
        candidate_parts = re.split(r"[,;]", candidate_location)

        for part in candidate_parts:
            part_clean = part.strip().lower()

            # Exact city name match
            if search_city == part_clean:
                return True

            # Handle compound city names
            if len(search_city.split()) > 1:
                # Multi-word city like "San Francisco"
                if search_city in part_clean or part_clean.startswith(search_city):
                    return True

        # Check if search is at the start of candidate (for "San Francisco" in "San Francisco Bay Area")
        if candidate_location.startswith(search_city):
            # Ensure it's a word boundary to avoid partial matches
            next_char_index = len(search_city)
            if next_char_index >= len(candidate_location) or candidate_location[
                next_char_index
            ] in [" ", ",", "-", "/"]:
                return True

        return False

    def _is_state_region_match(
        self, search_variation: str, candidate_location: str
    ) -> bool:
        """
        Check if search variation (state/region) matches candidate location.

        Examples:
        - "ca" matches "san francisco, ca" ✅
        - "california" matches "los angeles, ca" ✅
        - "ma" matches "boston, ma" ✅
        """
        # Common state patterns in candidate locations
        state_patterns = [
            f", {search_variation}",  # ", CA"
            f" {search_variation}",  # " CA"
            f"{search_variation},",  # "CA,"
            f"{search_variation} ",  # "CA "
        ]

        for pattern in state_patterns:
            if pattern in candidate_location:
                return True

        # Full state name matching
        if len(search_variation) > 3:  # Likely a full state name
            if search_variation in candidate_location:
                return True

        return False

    def _is_metro_area_match(
        self, search_location: str, candidate_location: str
    ) -> bool:
        """
        Check for metropolitan area matches.

        Examples:
        - "bay area" matches "san francisco, ca" ✅
        - "silicon valley" matches "palo alto, ca" ✅
        """
        metro_mappings = {
            "bay area": [
                "san francisco",
                "oakland",
                "san jose",
                "palo alto",
                "berkeley",
                "fremont",
            ],
            "silicon valley": [
                "palo alto",
                "mountain view",
                "cupertino",
                "sunnyvale",
                "san jose",
            ],
            "greater boston": [
                "boston",
                "cambridge",
                "somerville",
                "newton",
                "brookline",
            ],
            "dmv": ["washington", "arlington", "alexandria", "bethesda", "rockville"],
            "tri-state": ["new york", "newark", "jersey city", "stamford"],
        }

        if search_location in metro_mappings:
            metro_cities = metro_mappings[search_location]
            for city in metro_cities:
                if city in candidate_location:
                    return True

        return False

    def get_location_suggestions(self, failed_location: str) -> List[str]:
        """
        💡 GET SUGGESTIONS when location matching fails.

        Args:
            failed_location: The location that didn't match anything

        Returns:
            List of suggested alternative locations
        """
        suggestions = []
        failed_lower = failed_location.lower().strip()

        # Suggest state abbreviations
        if failed_lower in self.state_abbreviations:
            alt = self.state_abbreviations[failed_lower]
            suggestions.append(f"Try '{alt}' instead of '{failed_location}'")

        # Suggest popular tech cities if state was searched
        state_to_cities = {
            "california": ["San Francisco", "Los Angeles", "San Diego"],
            "ca": ["San Francisco", "Los Angeles", "San Diego"],
            "new york": ["New York City", "Buffalo"],
            "ny": ["New York City", "Buffalo"],
            "texas": ["Austin", "Houston", "Dallas"],
            "tx": ["Austin", "Houston", "Dallas"],
            "washington": ["Seattle", "Bellevue"],
            "wa": ["Seattle", "Bellevue"],
        }

        if failed_lower in state_to_cities:
            cities = state_to_cities[failed_lower]
            suggestions.append(f"Try specific cities: {', '.join(cities)}")

        # Suggest "Remote" as alternative
        if failed_lower not in ["remote", "wfh", "work from home"]:
            suggestions.append("Try 'Remote' for location")

        # Suggest removing location filter
        suggestions.append("Try searching without location filter")

        return suggestions[:3]  # Limit to 3 suggestions

    def debug_location_match(
        self, search_location: str, candidate_location: str
    ) -> Dict[str, any]:
        """
        🔧 DEBUG HELPER for understanding why location matching failed/succeeded.

        Args:
            search_location: Location from search
            candidate_location: Location from candidate

        Returns:
            Debug information dict
        """
        matches, confidence, reason = self.location_matches(
            search_location, candidate_location
        )
        variations = self.expand_location_for_matching(search_location)

        return {
            "search_location": search_location,
            "candidate_location": candidate_location,
            "matches": matches,
            "confidence": confidence,
            "reason": reason,
            "search_variations": sorted(variations),
            "suggestions": (
                self.get_location_suggestions(search_location) if not matches else []
            ),
        }


# Global instance for use across the application
location_service = LocationMappingService()
