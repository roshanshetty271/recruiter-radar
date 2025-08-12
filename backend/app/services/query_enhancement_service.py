"""
Query Enhancement Service

This service transforms natural language search queries into structured search intent
using OpenAI LLM. It handles:
- Role identification and skill expansion
- Experience level parsing
- Location normalization
- Skills categorization and synonym handling
- Confidence scoring and fallback mechanisms

The service is the core of the intelligent search system, enabling LinkedIn-quality
natural language search capabilities.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from openai import AsyncOpenAI, APIError
from fastapi import HTTPException

from app.core.config import settings
from app.core.prompts import (
    QUERY_INTENT_PARSING_PROMPT,
    SKILL_EXPANSION_PROMPT,
    LOCATION_NORMALIZATION_PROMPT,
)
from app.models.query_models import (
    QueryIntent,
    QueryEnhancementResult,
    LocationMatch,
    SkillMatch,
    RoleType,
    ExperienceLevel,
    SkillCategory,
)

logger = logging.getLogger(__name__)


class QueryEnhancementError(Exception):
    """Custom exception for query enhancement errors"""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class QueryEnhancementService:
    """
    Service for parsing and enhancing natural language search queries
    using OpenAI GPT models for intelligent intent extraction.
    """

    def __init__(self):
        """Initialize the query enhancement service with OpenAI client"""
        try:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = settings.chat_model_name  # gpt-4o-mini
            logger.info(f"QueryEnhancementService initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize QueryEnhancementService: {e}")
            raise QueryEnhancementError(f"Initialization failed: {e}", e)

    async def enhance_query(
        self, query: str, fallback_on_error: bool = True
    ) -> QueryEnhancementResult:
        """
        Main method to enhance a natural language query into structured intent.

        Args:
            query: Natural language search query
            fallback_on_error: Whether to use fallback parsing if LLM fails

        Returns:
            QueryEnhancementResult with parsed intent and metadata
        """
        start_time = time.time()

        logger.info(f"🧠 Enhancing query: '{query}'")

        # Handle empty or whitespace-only queries
        if not query or not query.strip():
            return self._create_empty_query_result(query, start_time)

        try:
            # Parse query using LLM
            query_intent = await self._parse_query_with_llm(query)

            # Enhance with additional skills if role is detected
            if query_intent.role_type:
                query_intent = await self._expand_role_skills(query_intent)

            # Apply post-processing for specific role intents detected from raw query text
            query_intent = self._adjust_for_pm_intent(query, query_intent)

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"✅ Query enhanced successfully: role={query_intent.role_type}, "
                f"skills={len(query_intent.required_skills)}, "
                f"confidence={query_intent.confidence_score:.2f}"
            )

            return QueryEnhancementResult(
                query_intent=query_intent,
                processing_time_ms=processing_time,
                llm_tokens_used=None,  # TODO: Track token usage
                fallback_used=False,
                enhancement_version="1.0",
            )

        except Exception as e:
            logger.warning(f"LLM query parsing failed: {e}")

            if fallback_on_error:
                logger.info("Using fallback query parsing")
                query_intent = await self._fallback_parse_query(query)
                # Apply post-processing even in fallback mode
                query_intent = self._adjust_for_pm_intent(query, query_intent)
                processing_time = (time.time() - start_time) * 1000

                return QueryEnhancementResult(
                    query_intent=query_intent,
                    processing_time_ms=processing_time,
                    llm_tokens_used=None,
                    fallback_used=True,
                    enhancement_version="1.0",
                )
            else:
                raise QueryEnhancementError(f"Query enhancement failed: {e}", e)

    def _adjust_for_pm_intent(self, raw_query: str, intent: QueryIntent) -> QueryIntent:
        """Lightweight rule-based adjustment when PM intent is detected.

        - If the user asks for project/program managers, ensure role intent reflects management, not developer.
        - Avoid injecting developer-centric required skills; prefer PM-related preferred skills.
        - Keep adjustments soft to avoid hardcoding candidates.
        """
        q = raw_query.lower()
        pm_signals = [
            "project manager",
            "program manager",
            "scrum master",
            "delivery manager",
            "project managers",
            "program managers",
        ]

        if any(sig in q for sig in pm_signals):
            # If role is generic or developer, nudge towards generic without dev skill injection
            from app.models.query_models import RoleType, SkillMatch

            if intent.role_type in (None, RoleType.GENERIC):
                intent.role_type = RoleType.GENERIC

            # Remove obviously dev-centric required skills if they were injected for a PM query
            dev_like = {
                "python",
                "java",
                "javascript",
                "react",
                "node",
                "kubernetes",
                "docker",
            }
            intent.required_skills = [
                s for s in intent.required_skills if s.skill not in dev_like
            ]

            # Add PM-centric preferred skills softly if empty
            if not intent.preferred_skills:
                pm_pref = [
                    SkillMatch(
                        skill="agile", confidence_score=0.7, is_exact_match=True
                    ),
                    SkillMatch(
                        skill="scrum", confidence_score=0.7, is_exact_match=True
                    ),
                    SkillMatch(skill="jira", confidence_score=0.6, is_exact_match=True),
                    SkillMatch(
                        skill="stakeholder management",
                        confidence_score=0.6,
                        is_exact_match=True,
                    ),
                    SkillMatch(
                        skill="roadmaps", confidence_score=0.6, is_exact_match=True
                    ),
                ]
                intent.preferred_skills.extend(pm_pref)

            logger.info(
                "✅ Adjusted intent for PM query: emphasized PM skills, removed dev-only requirements"
            )

        return intent

    async def _parse_query_with_llm(self, query: str) -> QueryIntent:
        """Parse query using OpenAI LLM with structured prompts"""
        try:
            prompt = QUERY_INTENT_PARSING_PROMPT.format(query=query)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert recruiter search assistant. Parse queries accurately and return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent parsing
                max_tokens=1500,
                timeout=30.0,
            )

            content = response.choices[0].message.content
            if not content:
                raise QueryEnhancementError("Empty response from LLM")

            # Parse JSON response
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {content}")
                raise QueryEnhancementError(f"Invalid JSON from LLM: {e}", e)

            # Convert to QueryIntent model
            query_intent = self._convert_llm_response_to_query_intent(
                query, parsed_data
            )

            return query_intent

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise QueryEnhancementError(f"OpenAI API error: {e}", e)

    def _convert_llm_response_to_query_intent(
        self, original_query: str, data: Dict[str, Any]
    ) -> QueryIntent:
        """Convert LLM JSON response to QueryIntent model with validation"""
        try:
            # Convert role_type string to enum
            role_type = None
            if data.get("role_type"):
                try:
                    role_type = RoleType(data["role_type"])
                except ValueError:
                    logger.warning(f"Unknown role type: {data['role_type']}")

            # Convert experience_level string to enum
            experience_level = None
            if data.get("experience_level"):
                try:
                    experience_level = ExperienceLevel(data["experience_level"])
                except ValueError:
                    logger.warning(
                        f"Unknown experience level: {data['experience_level']}"
                    )

            # Convert skills to SkillMatch objects
            required_skills = []
            for skill_data in data.get("required_skills", []):
                skill_match = self._create_skill_match(skill_data)
                if skill_match:
                    required_skills.append(skill_match)

            preferred_skills = []
            for skill_data in data.get("preferred_skills", []):
                skill_match = self._create_skill_match(skill_data)
                if skill_match:
                    preferred_skills.append(skill_match)

            # Convert location data to LocationMatch object
            location_match = None
            if data.get("location_match"):
                location_data = data["location_match"]
                location_match = LocationMatch(
                    original_query=location_data.get("original_query", ""),
                    normalized_location=location_data.get("normalized_location"),
                    city=location_data.get("city"),
                    state=location_data.get("state"),
                    country=location_data.get("country"),
                    confidence_score=location_data.get("confidence_score", 0.0),
                    is_valid=location_data.get("is_valid", False),
                    suggested_radius_km=location_data.get("suggested_radius_km"),
                )

            # Create QueryIntent object
            query_intent = QueryIntent(
                original_query=original_query,
                role_type=role_type,
                role_keywords=data.get("role_keywords", []),
                experience_level=experience_level,
                experience_years_min=data.get("experience_years_min"),
                experience_years_max=data.get("experience_years_max"),
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                excluded_skills=data.get("excluded_skills", []),
                location_match=location_match,
                confidence_score=data.get("confidence_score", 0.0),
                is_empty_query=data.get("is_empty_query", False),
                parsing_errors=data.get("parsing_errors", []),
                additional_filters=data.get("additional_filters", {}),
            )

            return query_intent

        except Exception as e:
            logger.error(f"Failed to convert LLM response to QueryIntent: {e}")
            raise QueryEnhancementError(f"Response conversion failed: {e}", e)

    def _create_skill_match(self, skill_data: Dict[str, Any]) -> Optional[SkillMatch]:
        """Create SkillMatch object from LLM skill data"""
        try:
            skill_category = None
            if skill_data.get("category"):
                try:
                    skill_category = SkillCategory(skill_data["category"])
                except ValueError:
                    logger.warning(f"Unknown skill category: {skill_data['category']}")

            return SkillMatch(
                skill=skill_data.get("skill", "").lower(),
                category=skill_category,
                confidence_score=skill_data.get("confidence_score", 1.0),
                is_exact_match=skill_data.get("is_exact_match", True),
            )
        except Exception as e:
            logger.error(f"Failed to create SkillMatch: {e}")
            return None

    async def _expand_role_skills(self, query_intent: QueryIntent) -> QueryIntent:
        """Expand skills based on detected role type using LLM"""
        if not query_intent.role_type:
            return query_intent

        try:
            mentioned_skills = [
                skill.skill
                for skill in query_intent.required_skills
                + query_intent.preferred_skills
            ]

            prompt = SKILL_EXPANSION_PROMPT.format(
                role_type=query_intent.role_type.value,
                mentioned_skills=(
                    ", ".join(mentioned_skills) if mentioned_skills else "None"
                ),
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical recruiter expert. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
                timeout=20.0,
            )

            content = response.choices[0].message.content
            if content:
                expansion_data = json.loads(content)

                # Add additional required skills
                for skill_data in expansion_data.get("additional_required_skills", []):
                    skill_match = self._create_skill_match(skill_data)
                    if skill_match and skill_match.skill not in mentioned_skills:
                        query_intent.required_skills.append(skill_match)

                # Add additional preferred skills
                for skill_data in expansion_data.get("additional_preferred_skills", []):
                    skill_match = self._create_skill_match(skill_data)
                    if skill_match and skill_match.skill not in mentioned_skills:
                        query_intent.preferred_skills.append(skill_match)

                logger.info(
                    f"Expanded skills for {query_intent.role_type.value}: "
                    f"+{len(expansion_data.get('additional_required_skills', []))} required, "
                    f"+{len(expansion_data.get('additional_preferred_skills', []))} preferred"
                )

        except Exception as e:
            logger.warning(f"Skills expansion failed for {query_intent.role_type}: {e}")

        return query_intent

    async def _fallback_parse_query(self, query: str) -> QueryIntent:
        """Fallback query parsing using simple keyword matching"""
        logger.info(f"Using fallback parsing for: '{query}'")

        query_lower = query.lower().strip()

        # Simple role detection
        role_type = None
        role_keywords = []

        role_mappings = {
            RoleType.FRONTEND_DEVELOPER: [
                "frontend",
                "front-end",
                "react",
                "angular",
                "vue",
                "ui",
                "web developer",
            ],
            RoleType.BACKEND_DEVELOPER: [
                "backend",
                "back-end",
                "api",
                "server",
                "python",
                "java",
                "node",
            ],
            RoleType.FULLSTACK_DEVELOPER: ["fullstack", "full-stack", "full stack"],
            RoleType.CLOUD_ENGINEER: [
                "cloud",
                "aws",
                "azure",
                "gcp",
                "devops",
                "kubernetes",
                "docker",
            ],
            RoleType.DATA_SCIENTIST: [
                "data scientist",
                "machine learning",
                "ml",
                "ai",
                "data analyst",
            ],
            RoleType.MOBILE_DEVELOPER: [
                "mobile",
                "ios",
                "android",
                "react native",
                "flutter",
            ],
        }

        for role, keywords in role_mappings.items():
            for keyword in keywords:
                if keyword in query_lower:
                    role_type = role
                    role_keywords.append(keyword)
                    break
            if role_type:
                break

        # Simple experience detection
        experience_level = None
        if any(word in query_lower for word in ["senior", "sr", "experienced"]):
            experience_level = ExperienceLevel.SENIOR
        elif any(word in query_lower for word in ["junior", "entry", "new grad"]):
            experience_level = ExperienceLevel.JUNIOR
        elif any(word in query_lower for word in ["mid", "intermediate"]):
            experience_level = ExperienceLevel.MID

        # Simple skills extraction - look for common technologies
        common_skills = [
            "python",
            "java",
            "javascript",
            "react",
            "angular",
            "vue",
            "node",
            "typescript",
            "aws",
            "azure",
            "docker",
            "kubernetes",
            "sql",
            "mongodb",
            "postgresql",
            "html",
            "css",
            "git",
            "linux",
            "bash",
            "tensorflow",
            "pytorch",
        ]

        found_skills = []
        for skill in common_skills:
            if skill in query_lower:
                found_skills.append(
                    SkillMatch(
                        skill=skill,
                        confidence_score=0.8,
                        is_exact_match=True,
                        synonyms=[],
                    )
                )

        return QueryIntent(
            original_query=query,
            role_type=role_type,
            role_keywords=role_keywords,
            experience_level=experience_level,
            required_skills=found_skills,
            preferred_skills=[],
            excluded_skills=[],
            location_match=None,
            confidence_score=0.5,  # Lower confidence for fallback
            is_empty_query=len(query.strip()) == 0,
            parsing_errors=["Used fallback parsing due to LLM failure"],
            additional_filters={},
        )

    def _create_empty_query_result(
        self, query: str, start_time: float
    ) -> QueryEnhancementResult:
        """Create result for empty or invalid queries"""
        processing_time = (time.time() - start_time) * 1000

        query_intent = QueryIntent(
            original_query=query,
            confidence_score=0.0,
            is_empty_query=True,
            parsing_errors=[] if not query else ["Empty query provided"],
        )

        return QueryEnhancementResult(
            query_intent=query_intent,
            processing_time_ms=processing_time,
            fallback_used=False,
            enhancement_version="1.0",
        )

    async def normalize_location(self, location: str) -> Optional[LocationMatch]:
        """
        Standalone method to normalize location queries.

        Args:
            location: Location string to normalize

        Returns:
            LocationMatch object or None if invalid
        """
        if not location or not location.strip():
            return None

        try:
            prompt = LOCATION_NORMALIZATION_PROMPT.format(location=location)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a geographic location expert. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
                timeout=15.0,
            )

            content = response.choices[0].message.content
            if content:
                location_data = json.loads(content)
                return LocationMatch(**location_data)

        except Exception as e:
            logger.warning(f"Location normalization failed for '{location}': {e}")

        return None
