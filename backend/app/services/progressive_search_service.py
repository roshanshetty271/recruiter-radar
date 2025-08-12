"""
Progressive Search Service for RecruiterRadar MVP.

Implements intelligent fallback strategies when searches return no results,
ensuring users always get helpful suggestions and never see empty result pages.
"""

from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
import logging
import asyncio
from datetime import datetime

from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.location_service import location_service

# 🚀 NEW: Import QueryIntent for type hints
if TYPE_CHECKING:
    from app.models.query_models import QueryIntent

logger = logging.getLogger(__name__)


class ProgressiveSearchService:
    """
    🔄 PROGRESSIVE SEARCH SERVICE

    Implements intelligent search fallback strategies to ensure users
    never encounter empty results without helpful suggestions.
    """

    def __init__(self, rag_service: RAGService, llm_service: LLMService):
        """Initialize the progressive search service."""
        self.rag_service = rag_service
        self.llm_service = llm_service

    async def search_with_fallback(
        self,
        query_embedding: List[float],
        original_query: str,
        enhanced_filters: Dict[str, Any],
        k: int = 20,
        max_fallback_levels: int = 4,
        required_skills: Optional[List[str]] = None,
        preferred_skills: Optional[List[str]] = None,
        query_intent: Optional[
            "QueryIntent"
        ] = None,  # 🚀 NEW: Accept pre-parsed intent
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        🎯 MAIN PROGRESSIVE SEARCH FUNCTION

        Performs search with intelligent fallback if no results found.

        Args:
            query_embedding: Vector embedding of the search query
            original_query: Original user query string
            enhanced_filters: Enhanced filters from query enhancement
            k: Number of results to return
            max_fallback_levels: Maximum fallback attempts
            query_intent: 🚀 NEW - Pre-parsed query intent to avoid redundant AI calls

        Returns:
            Tuple of (results, search_metadata)
        """
        search_metadata = {
            "original_query": original_query,
            "enhanced_filters": enhanced_filters,
            "fallback_level_used": 0,
            "search_strategy": "exact_match",
            "suggestions": [],
            "total_attempts": 0,
            "search_timestamp": datetime.utcnow().isoformat(),
        }

        # Level 0: Exact search with all filters
        logger.info(f"🎯 Level 0: Exact search with all filters")
        try:
            results, count_before_filter = await self.rag_service.similarity_search(
                query_embedding=query_embedding,
                query_text=original_query,
                k=k,
                filters=enhanced_filters,
                required_skills=required_skills or [],
                preferred_skills=preferred_skills or [],
                query_intent=query_intent,  # 🚀 NEW: Pass pre-parsed intent
            )
        except Exception as e:
            logger.error(f"❌ Level 0 search failed: {e}")
            logger.info(f"🔄 Falling back to basic unfiltered search...")
            # Fallback: Basic search without problematic filters
            fallback_filters = {}  # Remove all filters that might cause issues
            results, count_before_filter = await self.rag_service.similarity_search(
                query_embedding=query_embedding,
                query_text=original_query,
                k=k,
                filters=fallback_filters,
                required_skills=[],
                preferred_skills=[],
                query_intent=query_intent,  # 🚀 NEW: Pass pre-parsed intent to fallback too
            )
            search_metadata["fallback_used"] = True
            search_metadata["fallback_reason"] = f"Level 0 error: {str(e)}"

        search_metadata["total_attempts"] += 1

        if results:
            logger.info(f"✅ Level 0 success: Found {len(results)} candidates")
            search_metadata["search_strategy"] = "exact_match"
            return results, search_metadata

        # Start progressive fallback if no results
        logger.warning(f"🚨 Level 0 failed: 0 results with exact filters")

        for level in range(1, max_fallback_levels + 1):
            logger.info(f"🔄 Starting fallback Level {level}")

            # Generate relaxed filters for this level
            relaxed_filters = self._get_relaxed_filters(enhanced_filters, level)

            # Attempt search with relaxed filters
            results, count_before_filter = await self.rag_service.similarity_search(
                query_embedding=query_embedding,
                query_text=original_query,
                k=k,
                filters=relaxed_filters,
                required_skills=required_skills or [],
                preferred_skills=preferred_skills or [],
                query_intent=query_intent,  # 🚀 NEW: Pass pre-parsed intent to fallback too
            )

            search_metadata["total_attempts"] += 1

            if results:
                logger.info(
                    f"✅ Level {level} success: Found {len(results)} candidates with relaxed filters"
                )
                search_metadata["fallback_level_used"] = level
                search_metadata["search_strategy"] = self._get_strategy_name(level)
                search_metadata["relaxed_filters"] = relaxed_filters
                search_metadata["suggestions"] = self._get_level_suggestions(
                    level, enhanced_filters, relaxed_filters
                )
                return results, search_metadata
            else:
                logger.warning(f"❌ Level {level} failed: Still 0 results")

        # All fallback levels failed - provide comprehensive suggestions
        logger.error(f"🚨 All {max_fallback_levels} fallback levels failed!")
        search_metadata["fallback_level_used"] = max_fallback_levels
        search_metadata["search_strategy"] = "all_fallbacks_failed"
        search_metadata["suggestions"] = await self._get_comprehensive_suggestions(
            original_query, enhanced_filters
        )
        return [], search_metadata

    def _get_relaxed_filters(
        self, original_filters: Dict[str, Any], level: int
    ) -> Dict[str, Any]:
        """
        🔧 Generate relaxed filters for the given fallback level.

        Args:
            original_filters: Original enhanced filters
            level: Fallback level (1-4)

        Returns:
            Relaxed filters for this level
        """
        relaxed = original_filters.copy()

        if level == 1:
            # Level 1: Relax location and preferred skills
            if relaxed.get("location"):
                relaxed.pop("location", None)
            if relaxed.get("preferred_skills"):
                relaxed["preferred_skills"] = []  # Remove preferred

        elif level == 2:
            # Level 2: Relax location + reduce required skills
            relaxed.pop("location", None)
            if relaxed.get("required_skills") and len(relaxed["required_skills"]) > 1:
                relaxed["required_skills"] = [relaxed["required_skills"][0]]

        elif level == 3:
            # Level 3: Relax experience + location + reduce skills
            relaxed.pop("location", None)
            relaxed.pop("experience_years", None)  # Remove experience filter
            if relaxed.get("skills_query") and len(relaxed["skills_query"]) > 1:
                relaxed["skills_query"] = [relaxed["skills_query"][0]]
            logger.info(f"   Level 3: Removed experience filter and location")

        elif level == 4:
            # Level 4: Keep only visa status (if any), remove everything else
            visa_status = relaxed.get("visa_status")
            relaxed = {}
            if visa_status:
                relaxed["visa_status"] = visa_status
                logger.info(f"   Level 4: Keeping only visa status: {visa_status}")
            else:
                logger.info(f"   Level 4: Removed all filters - broad search")

        return relaxed

    def _get_strategy_name(self, level: int) -> str:
        """Get human-readable strategy name for the fallback level."""
        strategy_names = {
            1: "exact_match",
            2: "exact_match",
            3: "exact_match",
            4: "exact_match",
        }
        return strategy_names.get(level, f"fallback_level_{level}")

    def _get_level_suggestions(
        self,
        level: int,
        original_filters: Dict[str, Any],
        relaxed_filters: Dict[str, Any],
    ) -> List[str]:
        """
        💡 Generate suggestions for successful fallback level.

        Args:
            level: The fallback level that succeeded
            original_filters: Original search filters
            relaxed_filters: The relaxed filters that worked

        Returns:
            List of suggestions for the user
        """
        suggestions = []

        if level == 1:
            if original_filters.get("location"):
                suggestions.append(
                    f"Found results by expanding location search beyond '{original_filters['location']}'"
                )
                suggestions.append("Try 'Remote' or nearby cities for more options")

        elif level == 2:
            if (
                original_filters.get("skills_query")
                and len(original_filters["skills_query"]) > 1
            ):
                removed_skills = original_filters["skills_query"][1:]
                suggestions.append(
                    f"Found results by focusing on core skill requirements"
                )
                suggestions.append(
                    f"Consider making these skills optional: {', '.join(removed_skills)}"
                )

        elif level == 3:
            suggestions.append("Found results by relaxing experience requirements")
            if original_filters.get("experience_years"):
                suggestions.append(
                    "Consider candidates with less experience who show potential"
                )

        elif level == 4:
            # Remove noisy suggestions for broad search
            pass

        return suggestions

    async def _get_comprehensive_suggestions(
        self, original_query: str, enhanced_filters: Dict[str, Any]
    ) -> List[str]:
        """
        💡 Generate comprehensive suggestions when all fallback levels fail.

        Args:
            original_query: Original search query
            enhanced_filters: Enhanced filters that failed

        Returns:
            List of comprehensive suggestions
        """
        suggestions = []

        # Query-specific suggestions
        query_lower = original_query.lower()

        # Skill-based suggestions
        if enhanced_filters.get("skills_query"):
            primary_skill = enhanced_filters["skills_query"][0]
            suggestions.append(
                f"Try broader terms like 'developer' instead of specific '{primary_skill}' requirements"
            )

            # Technology-specific suggestions
            if any(
                tech in primary_skill.lower() for tech in ["react", "angular", "vue"]
            ):
                suggestions.append(
                    "Try 'Frontend Developer' for broader frontend candidates"
                )
            elif any(
                tech in primary_skill.lower() for tech in ["python", "java", "node"]
            ):
                suggestions.append(
                    "Try 'Backend Developer' for broader backend candidates"
                )
            elif "full" in primary_skill.lower():
                suggestions.append("Try separate 'Frontend' and 'Backend' searches")

        # Location-based suggestions
        if enhanced_filters.get("location"):
            location_suggestions = location_service.get_location_suggestions(
                enhanced_filters["location"]
            )
            suggestions.extend(location_suggestions)
        else:
            suggestions.append("Try adding 'Remote' to see work-from-home candidates")

        # Experience-based suggestions
        if enhanced_filters.get("experience_years"):
            exp_years = enhanced_filters["experience_years"]["$gte"]
            if exp_years > 5:
                suggestions.append(
                    f"Try reducing experience requirement from {exp_years}+ years"
                )
            suggestions.append(
                "Consider candidates with relevant project experience vs. just years"
            )

        # General fallback suggestions
        suggestions.extend(
            [
                "Try searching for related job titles or technologies",
                "Consider remote candidates to expand your talent pool",
                "Break complex queries into simpler, focused searches",
            ]
        )

        # Popular alternative searches
        popular_searches = [
            "Senior Software Engineer",
            "Full Stack Developer",
            "Frontend Developer React",
            "Backend Developer Python",
            "DevOps Engineer AWS",
            "Data Scientist Python",
        ]

        suggestions.append("Popular searches to try:")
        suggestions.extend([f"  • {search}" for search in popular_searches[:3]])

        return suggestions[:8]  # Limit to 8 suggestions to avoid overwhelming

    async def get_search_insights(
        self, search_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        📊 Generate insights about the search performance and suggestions.

        Args:
            search_metadata: Metadata from the progressive search

        Returns:
            Search insights and recommendations
        """
        insights = {
            "search_effectiveness": "excellent",
            "optimization_tips": [],
            "alternative_strategies": [],
            "success_metrics": {},
        }

        fallback_level = search_metadata.get("fallback_level_used", 0)

        if fallback_level == 0:
            insights["search_effectiveness"] = "excellent"
            insights["optimization_tips"].append(
                "Your search parameters are well-optimized"
            )
        elif fallback_level <= 2:
            insights["search_effectiveness"] = "good"
            insights["optimization_tips"].append(
                "Consider slightly broader search criteria for more results"
            )
        elif fallback_level <= 3:
            insights["search_effectiveness"] = "moderate"
            insights["optimization_tips"].extend(
                [
                    "Your search criteria might be too specific",
                    "Consider breaking complex requirements into separate searches",
                ]
            )
        else:
            insights["search_effectiveness"] = "challenging"
            insights["optimization_tips"].extend(
                [
                    "This search combination is very rare in our database",
                    "Try focusing on 1-2 key requirements instead",
                ]
            )

        # Add success metrics
        insights["success_metrics"] = {
            "fallback_level_used": fallback_level,
            "total_search_attempts": search_metadata.get("total_attempts", 0),
            "search_strategy": search_metadata.get("search_strategy", "unknown"),
        }

        return insights


# Global service instance
progressive_search_service = None


def get_progressive_search_service(
    rag_service: RAGService, llm_service: LLMService
) -> ProgressiveSearchService:
    """Get or create the global progressive search service instance."""
    global progressive_search_service
    if progressive_search_service is None:
        progressive_search_service = ProgressiveSearchService(rag_service, llm_service)
    return progressive_search_service
