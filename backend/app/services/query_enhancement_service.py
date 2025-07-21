"""
LLM-Powered Query Enhancement Service for RecruiterRadar MVP.

Uses GPT-4o-mini to intelligently parse natural language queries and expand them
with related skills, role-based inferences, and better search intent understanding.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
import json
import re
import logging
import asyncio
from datetime import datetime

from app.services.llm_service import LLMService
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryEnhancementService:
    """
    🧠 LLM-POWERED QUERY ENHANCEMENT SERVICE

    Transforms natural language queries into intelligent search parameters
    that understand intent, expand related skills, and improve search accuracy.
    """

    def __init__(self, llm_service: LLMService):
        """Initialize the query enhancement service."""
        self.llm_service = llm_service
        self.cache = {}  # Simple cache for repeated queries
        self.max_cache_size = 100

    async def enhance_query(
        self, query: str, existing_filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        🚀 MAIN ENHANCEMENT FUNCTION

        Takes a natural language query and returns enhanced search parameters.

        Args:
            query: Natural language query (e.g., "python developers in California")
            existing_filters: Any existing search filters

        Returns:
            Enhanced query parameters with expanded skills, locations, etc.
        """
        if not query or not query.strip():
            return self._get_fallback_enhancement()

        # Check cache first
        cache_key = f"{query.lower().strip()}_{str(existing_filters)}"
        if cache_key in self.cache:
            logger.info(f"🎯 Using cached enhancement for: '{query}'")
            return self.cache[cache_key]

        logger.info(f"🧠 Enhancing query: '{query}'")

        try:
            # Use LLM to intelligently parse the query
            logger.info(f"🤖 Calling LLM for query enhancement: '{query}'")
            enhancement_result = await self._llm_enhance_query(
                query, existing_filters or {}
            )
            logger.info("✅ LLM enhancement successful")

            # Post-process and validate the results
            final_result = self._post_process_enhancement(
                enhancement_result, query, existing_filters or {}
            )

            # Cache the result
            self._add_to_cache(cache_key, final_result)

            logger.info(f"✅ Query enhancement completed successfully")
            return final_result

        except Exception as e:
            logger.error(f"❌ LLM query enhancement failed: {str(e)}", exc_info=True)
            # Fallback to basic enhancement without raising
            return self._get_basic_enhancement(query, existing_filters or {})

    async def _llm_enhance_query(
        self, query: str, existing_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🤖 Use GPT-4o-mini to intelligently enhance the query.
        """
        # Construct a focused prompt for query enhancement
        prompt = f"""You are an expert recruiter query analyzer. Parse this search query and extract structured information to help find the best candidates.

SEARCH QUERY: "{query}"

Analyze this query and provide a JSON response with the following structure:

{{
    "intent": {{
        "primary_role": "the main job role being searched for",
        "seniority_level": "junior|mid|senior|lead|principal|null",
        "employment_type": "full-time|part-time|contract|intern|null"
    }},
    "skills": {{
        "required_skills": ["essential skills that candidates MUST have"],
        "preferred_skills": ["nice-to-have skills that would be valuable"],
        "technology_stack": ["specific technologies, frameworks, languages"],
        "skill_categories": ["frontend|backend|fullstack|mobile|data|devops|ml|security|design"]
    }},
    "location": {{
        "primary_location": "main location mentioned or null",
        "work_arrangement": "remote|hybrid|onsite|null",
        "location_flexibility": "strict|flexible|null"
    }},
    "experience": {{
        "min_years": "minimum years of experience or null",
        "max_years": "maximum years of experience or null",
        "specific_experience": ["specific experience requirements"]
    }},
    "expanded_search_terms": ["additional related terms to improve search"],
    "search_intent_confidence": "how confident you are about the search intent (0.0-1.0)"
}}

EXAMPLES:

Query: "senior python developers"
→ Required skills: ["Python"], Preferred: ["Django", "FastAPI", "Flask"], Role: "Software Engineer", Seniority: "senior"

Query: "web developers with React experience"
→ Required skills: ["React", "JavaScript"], Preferred: ["TypeScript", "HTML", "CSS", "Node.js"], Categories: ["frontend", "fullstack"]

Query: "backend engineers in California"
→ Required skills: ["Backend Development"], Preferred: ["API Design", "Databases", "Python", "Java", "Node.js"], Location: "California"

Query: "full stack developers for remote work"
→ Required skills: ["Full-stack Development"], Preferred: ["React", "Node.js", "Python", "JavaScript"], Work arrangement: "remote"

Query: "machine learning engineers with 5+ years experience"
→ Required skills: ["Machine Learning"], Preferred: ["Python", "TensorFlow", "PyTorch", "Data Science"], Min years: 5

Be intelligent about:
1. Role inference: "web developers" includes frontend, backend, and fullstack developers
2. Technology ecosystems: React developers likely know JavaScript, TypeScript, HTML, CSS
3. Seniority parsing: "senior", "lead", "principal", "junior", years of experience
4. Location understanding: cities, states, regions, remote work preferences
5. Skill relationships: ML engineers likely know Python, data scientists know statistics

Provide ONLY the JSON response, no additional text."""

        try:
            response = await self.llm_service.client.chat.completions.create(
                model=settings.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert recruiter query analyzer. Always respond with valid JSON that matches the specified structure exactly.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent parsing
                max_tokens=800,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")

            # Parse the JSON response
            enhancement_data = json.loads(content)

            logger.info(
                f"🤖 LLM enhancement result: {json.dumps(enhancement_data, indent=2)}"
            )
            return enhancement_data

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM JSON response: {e}")
            raise Exception(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"❌ LLM query enhancement failed: {e}")
            raise

    def _post_process_enhancement(
        self,
        llm_result: Dict[str, Any],
        original_query: str,
        existing_filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        🔧 Post-process and validate LLM enhancement results.
        """
        # Start with existing filters
        enhanced_filters = existing_filters.copy()

        # Extract and validate skills
        skills_data = llm_result.get("skills", {})
        required_skills = skills_data.get("required_skills", [])
        preferred_skills = skills_data.get("preferred_skills", [])

        # Combine required and preferred skills for the search
        all_skills = required_skills + preferred_skills
        if all_skills:
            enhanced_filters["skills_query"] = all_skills
            enhanced_filters["required_skills"] = required_skills
            enhanced_filters["preferred_skills"] = preferred_skills

        # Extract location information
        location_data = llm_result.get("location", {})
        if not enhanced_filters.get("location") and location_data.get(
            "primary_location"
        ):
            enhanced_filters["location"] = location_data["primary_location"]

        # Extract experience requirements
        experience_data = llm_result.get("experience", {})
        if not enhanced_filters.get("min_experience") and experience_data.get(
            "min_years"
        ):
            try:
                enhanced_filters["min_experience"] = int(experience_data["min_years"])
            except (ValueError, TypeError):
                pass

        # Build enhanced query metadata
        enhancement_metadata = {
            "original_query": original_query,
            "enhanced_filters": enhanced_filters,
            "intent_analysis": llm_result.get("intent", {}),
            "skill_categories": skills_data.get("skill_categories", []),
            "technology_stack": skills_data.get("technology_stack", []),
            "work_arrangement": location_data.get("work_arrangement"),
            "confidence": llm_result.get("search_intent_confidence", 0.8),
            "expanded_terms": llm_result.get("expanded_search_terms", []),
            "enhancement_timestamp": datetime.utcnow().isoformat(),
            "enhancement_method": "llm_powered",
        }

        # Flatten LLM output for easier access
        enhancements = {}
        # Extract location with null handling
        extracted_location = location_data.get("primary_location")
        if extracted_location == "null":
            extracted_location = None
        enhancements["extracted_location"] = extracted_location

        # Extract skills - combine required and preferred
        extracted_skills = skills_data.get("required_skills", []) + skills_data.get(
            "preferred_skills", []
        )
        enhancements["extracted_skills"] = extracted_skills

        # Extract experience
        extracted_experience = {}
        min_years = experience_data.get("min_years")
        if min_years != "null" and min_years is not None:
            try:
                extracted_experience["min_years"] = int(min_years)
            except ValueError:
                pass
        enhancements["extracted_experience"] = (
            extracted_experience if extracted_experience else None
        )

        return {
            **enhancement_metadata,
            "enhanced_filters": enhanced_filters,
            **enhancements,
        }

    def _get_basic_enhancement(
        self, query: str, existing_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🔧 FALLBACK: Basic rule-based enhancement when LLM fails.
        """
        logger.info(f"🔧 Using basic enhancement fallback for: '{query}'")

        enhanced_filters = existing_filters.copy()

        # Basic skill extraction using patterns
        basic_skills = self._extract_basic_skills(query)
        if basic_skills:
            enhanced_filters["skills_query"] = basic_skills

        # Basic location extraction
        basic_location = self._extract_basic_location(query)
        if basic_location and not enhanced_filters.get("location"):
            enhanced_filters["location"] = basic_location

        # Basic experience extraction
        basic_experience = self._extract_basic_experience(query)
        if basic_experience and not enhanced_filters.get("min_experience"):
            enhanced_filters["min_experience"] = basic_experience

        return {
            "original_query": query,
            "enhanced_filters": enhanced_filters,
            "enhancement_method": "basic_fallback",
            "confidence": 0.6,
            "enhancement_timestamp": datetime.utcnow().isoformat(),
        }

    def _extract_basic_skills(self, query: str) -> List[str]:
        """Extract skills using basic pattern matching."""
        skills = []
        query_lower = query.lower()

        # Common technology patterns
        tech_patterns = {
            r"\b(python|py)\b": "Python",
            r"\b(javascript|js)\b": "JavaScript",
            r"\b(typescript|ts)\b": "TypeScript",
            r"\b(react|reactjs)\b": "React",
            r"\b(node|nodejs|node\.js)\b": "Node.js",
            r"\b(java)\b": "Java",
            r"\b(c\+\+|cpp)\b": "C++",
            r"\b(html|css)\b": "Frontend",
            r"\b(sql|database)\b": "SQL",
            r"\b(aws|cloud)\b": "AWS",
            r"\b(docker|kubernetes)\b": "DevOps",
        }

        for pattern, skill in tech_patterns.items():
            if re.search(pattern, query_lower):
                skills.append(skill)

        # Role-based skill inference
        if re.search(r"\b(web|frontend|front-end)\b", query_lower):
            skills.extend(["JavaScript", "HTML", "CSS", "React"])
        elif re.search(r"\b(backend|back-end|api)\b", query_lower):
            skills.extend(["Python", "Java", "API Design", "Databases"])
        elif re.search(r"\b(fullstack|full-stack)\b", query_lower):
            skills.extend(["JavaScript", "React", "Node.js", "Python"])
        elif re.search(r"\b(data|ml|machine learning)\b", query_lower):
            skills.extend(["Python", "Machine Learning", "Data Science"])

        return list(set(skills))  # Remove duplicates

    def _extract_basic_location(self, query: str) -> Optional[str]:
        """Extract location using basic pattern matching."""
        location_patterns = [
            r"\b(california|ca|san francisco|sf|los angeles|la)\b",
            r"\b(new york|ny|nyc|manhattan)\b",
            r"\b(texas|tx|austin|houston)\b",
            r"\b(washington|wa|seattle)\b",
            r"\b(remote|wfh|work from home)\b",
        ]

        query_lower = query.lower()
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return match.group(0).title()

        return None

    def _extract_basic_experience(self, query: str) -> Optional[int]:
        """Extract experience requirements using basic patterns."""
        # Look for patterns like "5+ years", "senior", etc.
        experience_patterns = [
            (r"(\d+)\+?\s*years?", lambda m: int(m.group(1))),
            (r"\bsenior\b", lambda m: 5),
            (r"\blead\b", lambda m: 7),
            (r"\bjunior\b", lambda m: 0),
            (r"\bintern\b", lambda m: 0),
        ]

        query_lower = query.lower()
        for pattern, extractor in experience_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    return extractor(match)
                except:
                    continue

        return None

    def _get_fallback_enhancement(self) -> Dict[str, Any]:
        """Provide fallback enhancement for empty queries."""
        return {
            "original_query": "",
            "enhanced_filters": {},
            "enhancement_method": "empty_query_fallback",
            "confidence": 0.3,
            "suggestions": [
                "Try specific skills like 'Python' or 'React'",
                "Specify experience level like 'Senior' or 'Junior'",
                "Add location like 'California' or 'Remote'",
            ],
            "enhancement_timestamp": datetime.utcnow().isoformat(),
        }

    def _add_to_cache(self, key: str, result: Dict[str, Any]) -> None:
        """Add result to cache with size management."""
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = result

    def get_enhancement_suggestions(
        self, failed_query: str, result_count: int
    ) -> List[str]:
        """
        💡 GET SUGGESTIONS when query enhancement doesn't find good results.

        Args:
            failed_query: The query that didn't work well
            result_count: Number of results found

        Returns:
            List of suggestions to improve the search
        """
        suggestions = []

        if result_count == 0:
            suggestions.extend(
                [
                    "Try broader terms (e.g., 'developer' instead of specific frameworks)",
                    "Remove location restrictions or try 'Remote'",
                    "Reduce experience requirements",
                    "Try related technologies (e.g., 'JavaScript' for React developers)",
                ]
            )
        elif result_count < 5:
            suggestions.extend(
                [
                    "Try related skills or frameworks",
                    "Consider broader location search",
                    "Look for related job titles",
                ]
            )

        # Add query-specific suggestions
        query_lower = failed_query.lower()
        if "senior" in query_lower:
            suggestions.append("Try 'experienced' instead of 'senior'")
        if any(tech in query_lower for tech in ["react", "angular", "vue"]):
            suggestions.append("Try 'frontend developer' for broader results")
        if any(tech in query_lower for tech in ["python", "java", "node"]):
            suggestions.append("Try 'backend developer' for broader results")

        return suggestions[:4]  # Limit to 4 suggestions


# Global service instance
query_enhancement_service = None


def get_query_enhancement_service(llm_service: LLMService) -> QueryEnhancementService:
    """Get or create the global query enhancement service instance."""
    global query_enhancement_service
    if query_enhancement_service is None:
        query_enhancement_service = QueryEnhancementService(llm_service)
    return query_enhancement_service
