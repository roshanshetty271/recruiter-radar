"""
Skills Taxonomy Service

This service provides intelligent skills management for the search system:
- Role-based skill expansion (React developer → JavaScript, HTML, CSS)
- Skill categorization and priority scoring
- Synonym and alternative name handling
- Skill similarity computation
- Experience level mapping

The service uses a comprehensive skills taxonomy database to enhance
search query understanding beyond simple keyword matching.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from fuzzywuzzy import fuzz

from app.models.query_models import (
    RoleType,
    SkillCategory,
    SkillMatch,
    ExperienceLevel,
)

logger = logging.getLogger(__name__)


class SkillsTaxonomyError(Exception):
    """Custom exception for skills taxonomy errors"""

    pass


class SkillsTaxonomyService:
    """
    Service for intelligent skills management and expansion.

    Provides role-based skill expansion, synonym handling, and
    skill categorization for enhanced search capabilities.
    """

    def __init__(self):
        """Initialize the skills taxonomy service with the taxonomy database"""
        self.taxonomy_data = None
        self.role_mappings = {}
        self.skill_synonyms = {}
        self.skill_categories_info = {}
        self.experience_mappings = {}
        self._skill_to_roles_cache = {}
        self._normalized_skills_cache = {}

        self._load_taxonomy_data()

    def _load_taxonomy_data(self):
        """Load the skills taxonomy data from JSON file"""
        try:
            taxonomy_path = (
                Path(__file__).parent.parent / "data" / "skills_taxonomy.json"
            )

            if not taxonomy_path.exists():
                raise SkillsTaxonomyError(
                    f"Skills taxonomy file not found: {taxonomy_path}"
                )

            with open(taxonomy_path, "r", encoding="utf-8") as f:
                self.taxonomy_data = json.load(f)

            # Parse and cache the data
            self.role_mappings = self.taxonomy_data.get("role_mappings", {})
            self.skill_synonyms = self.taxonomy_data.get("skill_synonyms", {})
            self.skill_categories_info = self.taxonomy_data.get("skill_categories", {})
            self.experience_mappings = self.taxonomy_data.get("experience_mappings", {})

            # Build reverse mappings for faster lookups
            self._build_skill_to_roles_mapping()

            logger.info(
                f"Skills taxonomy loaded: {len(self.role_mappings)} roles, "
                f"{len(self.skill_synonyms)} skill synonyms"
            )

        except FileNotFoundError:
            logger.error(f"Skills taxonomy file not found: {taxonomy_path}")
            raise SkillsTaxonomyError("Skills taxonomy database file not found")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in skills taxonomy file: {e}")
            raise SkillsTaxonomyError(f"Invalid skills taxonomy data: {e}")
        except Exception as e:
            logger.error(f"Failed to load skills taxonomy: {e}")
            raise SkillsTaxonomyError(f"Failed to load skills taxonomy: {e}")

    def _build_skill_to_roles_mapping(self):
        """Build reverse mapping from skills to roles for faster lookups"""
        self._skill_to_roles_cache = {}

        for role_type, role_data in self.role_mappings.items():
            all_skills = (
                role_data.get("core_skills", [])
                + role_data.get("framework_skills", [])
                + role_data.get("related_skills", [])
            )

            for skill_info in all_skills:
                skill_name = skill_info["skill"].lower()

                if skill_name not in self._skill_to_roles_cache:
                    self._skill_to_roles_cache[skill_name] = []

                self._skill_to_roles_cache[skill_name].append(
                    {
                        "role": role_type,
                        "category": skill_info.get("category", "unknown"),
                        "priority": skill_info.get("priority", 3),
                    }
                )

    async def expand_role_skills(
        self,
        role_type: RoleType,
        mentioned_skills: List[str] = None,
        include_related: bool = True,
    ) -> Dict[str, List[SkillMatch]]:
        """
        Expand skills for a given role type.

        Args:
            role_type: The role to expand skills for
            mentioned_skills: Skills already mentioned in the query
            include_related: Whether to include related/nice-to-have skills

        Returns:
            Dictionary with 'required' and 'preferred' skill lists
        """
        mentioned_skills = mentioned_skills or []
        mentioned_skills_lower = [skill.lower() for skill in mentioned_skills]

        role_key = role_type.value
        if role_key not in self.role_mappings:
            logger.warning(f"Role type {role_key} not found in taxonomy")
            return {"required": [], "preferred": []}

        role_data = self.role_mappings[role_key]

        # Get core skills (always required)
        required_skills = []
        for skill_info in role_data.get("core_skills", []):
            skill_name = skill_info["skill"].lower()
            if skill_name not in mentioned_skills_lower:
                skill_match = self._create_skill_match_from_taxonomy(skill_info, False)
                if skill_match:
                    required_skills.append(skill_match)

        # Get framework skills (usually required for the role)
        for skill_info in role_data.get("framework_skills", []):
            skill_name = skill_info["skill"].lower()
            if (
                skill_name not in mentioned_skills_lower
                and skill_info.get("priority", 3) <= 2
            ):
                skill_match = self._create_skill_match_from_taxonomy(skill_info, False)
                if skill_match:
                    required_skills.append(skill_match)

        # Get preferred skills
        preferred_skills = []
        if include_related:
            # Add lower priority framework skills
            for skill_info in role_data.get("framework_skills", []):
                skill_name = skill_info["skill"].lower()
                if (
                    skill_name not in mentioned_skills_lower
                    and skill_info.get("priority", 3) > 2
                ):
                    skill_match = self._create_skill_match_from_taxonomy(
                        skill_info, False
                    )
                    if skill_match:
                        preferred_skills.append(skill_match)

            # Add related skills
            for skill_info in role_data.get("related_skills", []):
                skill_name = skill_info["skill"].lower()
                if skill_name not in mentioned_skills_lower:
                    skill_match = self._create_skill_match_from_taxonomy(
                        skill_info, False
                    )
                    if skill_match:
                        preferred_skills.append(skill_match)

        logger.info(
            f"Expanded skills for {role_key}: {len(required_skills)} required, "
            f"{len(preferred_skills)} preferred"
        )

        return {"required": required_skills, "preferred": preferred_skills}

    def _create_skill_match_from_taxonomy(
        self, skill_info: Dict[str, Any], is_exact_match: bool = False
    ) -> Optional[SkillMatch]:
        """Create SkillMatch object from taxonomy skill information"""
        try:
            skill_name = skill_info["skill"].lower()

            # Determine skill category
            skill_category = None
            category_str = skill_info.get("category")
            if category_str:
                try:
                    skill_category = SkillCategory(category_str)
                except ValueError:
                    logger.warning(f"Unknown skill category: {category_str}")

            # Calculate confidence based on priority
            priority = skill_info.get("priority", 3)
            confidence_score = max(
                0.4, 1.0 - (priority - 1) * 0.2
            )  # Priority 1=1.0, 2=0.8, 3=0.6, etc.

            # Get synonyms
            synonyms = self.skill_synonyms.get(skill_name, [])

            return SkillMatch(
                skill=skill_name,
                category=skill_category,
                confidence_score=confidence_score,
                is_exact_match=is_exact_match,
                synonyms=synonyms,
            )

        except Exception as e:
            logger.warning(f"Failed to create SkillMatch from {skill_info}: {e}")
            return None

    async def get_skill_synonyms(self, skill: str) -> List[str]:
        """Get synonyms for a given skill"""
        skill_lower = skill.lower().strip()

        # Direct lookup
        synonyms = self.skill_synonyms.get(skill_lower, [])

        # Also check if the skill IS a synonym of another skill
        for main_skill, skill_synonyms in self.skill_synonyms.items():
            if skill_lower in [s.lower() for s in skill_synonyms]:
                synonyms.extend([main_skill] + skill_synonyms)
                break

        # Remove duplicates and the original skill
        unique_synonyms = list(set(synonyms))
        if skill_lower in [s.lower() for s in unique_synonyms]:
            unique_synonyms = [s for s in unique_synonyms if s.lower() != skill_lower]

        return unique_synonyms

    async def normalize_skill_name(self, skill: str) -> str:
        """
        Normalize skill name to its canonical form.

        Args:
            skill: Raw skill name

        Returns:
            Normalized skill name
        """
        if skill in self._normalized_skills_cache:
            return self._normalized_skills_cache[skill]

        skill_lower = skill.lower().strip()

        # Check if it's already a main skill
        if skill_lower in self.skill_synonyms:
            self._normalized_skills_cache[skill] = skill_lower
            return skill_lower

        # Check if it's a synonym
        for main_skill, synonyms in self.skill_synonyms.items():
            if skill_lower in [s.lower() for s in synonyms]:
                self._normalized_skills_cache[skill] = main_skill
                return main_skill

        # If not found, return cleaned version
        normalized = re.sub(r"[^\w\s\+\#\.]", "", skill_lower).strip()
        self._normalized_skills_cache[skill] = normalized
        return normalized

    async def compute_skill_similarity(self, skill1: str, skill2: str) -> float:
        """
        Compute similarity between two skills using multiple methods.

        Args:
            skill1: First skill name
            skill2: Second skill name

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize both skills
        norm_skill1 = await self.normalize_skill_name(skill1)
        norm_skill2 = await self.normalize_skill_name(skill2)

        # Exact match
        if norm_skill1 == norm_skill2:
            return 1.0

        # Synonym match
        skill1_synonyms = await self.get_skill_synonyms(norm_skill1)
        if norm_skill2 in [s.lower() for s in skill1_synonyms]:
            return 0.95

        # Fuzzy string similarity with minimum threshold
        fuzzy_score = fuzz.ratio(norm_skill1, norm_skill2) / 100.0

        # Partial match for compound skills (e.g., "react native" vs "react")
        if norm_skill1 in norm_skill2 or norm_skill2 in norm_skill1:
            # Only if one skill contains the other and they're reasonably related
            if (
                len(norm_skill1) >= 3 and len(norm_skill2) >= 3
            ):  # Avoid single character matches
                partial_score = 0.8
                return max(fuzzy_score, partial_score)

        # Apply minimum threshold for fuzzy matches to avoid false positives
        # Skills must be at least 80% similar to be considered related
        if fuzzy_score >= 0.8:
            return fuzzy_score

        # For skills that are somewhat similar but not enough, return 0
        return 0.0

    async def categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """
        Categorize a list of skills by their types.

        Args:
            skills: List of skill names

        Returns:
            Dictionary mapping categories to skill lists
        """
        categorized = {category.value: [] for category in SkillCategory}
        categorized["unknown"] = []

        for skill in skills:
            normalized_skill = await self.normalize_skill_name(skill)
            category = await self._get_skill_category(normalized_skill)

            if category:
                categorized[category.value].append(skill)
            else:
                categorized["unknown"].append(skill)

        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}

    async def _get_skill_category(self, skill: str) -> Optional[SkillCategory]:
        """Determine the category of a skill"""
        skill_lower = skill.lower()

        # Check in role mappings for category info
        for role_data in self.role_mappings.values():
            all_skills = (
                role_data.get("core_skills", [])
                + role_data.get("framework_skills", [])
                + role_data.get("related_skills", [])
            )

            for skill_info in all_skills:
                if skill_info["skill"].lower() == skill_lower:
                    category_str = skill_info.get("category")
                    if category_str:
                        try:
                            return SkillCategory(category_str)
                        except ValueError:
                            pass

        return None

    async def suggest_roles_for_skills(
        self, skills: List[str]
    ) -> List[Tuple[RoleType, float]]:
        """
        Suggest roles based on a list of skills.

        Args:
            skills: List of skill names

        Returns:
            List of (role, confidence_score) tuples, sorted by confidence
        """
        role_scores = {}

        for skill in skills:
            normalized_skill = await self.normalize_skill_name(skill)

            if normalized_skill in self._skill_to_roles_cache:
                for role_info in self._skill_to_roles_cache[normalized_skill]:
                    role_type = role_info["role"]
                    priority = role_info["priority"]

                    # Calculate score based on priority (higher priority = higher score)
                    score = max(0.1, 1.0 - (priority - 1) * 0.3)

                    if role_type not in role_scores:
                        role_scores[role_type] = 0.0

                    role_scores[role_type] += score

        # Normalize scores and convert to RoleType enums
        if role_scores:
            max_score = max(role_scores.values())
            normalized_scores = []

            for role_str, score in role_scores.items():
                try:
                    role_enum = RoleType(role_str)
                    normalized_score = min(1.0, score / max_score)
                    normalized_scores.append((role_enum, normalized_score))
                except ValueError:
                    logger.warning(f"Unknown role type in taxonomy: {role_str}")

            # Sort by confidence score (descending)
            normalized_scores.sort(key=lambda x: x[1], reverse=True)
            return normalized_scores

        return []

    async def get_experience_level_info(
        self, experience_level: ExperienceLevel
    ) -> Dict[str, Any]:
        """Get information about an experience level"""
        level_str = experience_level.value
        return self.experience_mappings.get(level_str, {})

    def get_all_skills_for_role(self, role_type: RoleType) -> List[str]:
        """Get all skills associated with a role (for testing/debugging)"""
        role_key = role_type.value
        if role_key not in self.role_mappings:
            return []

        role_data = self.role_mappings[role_key]
        all_skills = []

        for skill_list in ["core_skills", "framework_skills", "related_skills"]:
            for skill_info in role_data.get(skill_list, []):
                all_skills.append(skill_info["skill"])

        return all_skills

    def get_taxonomy_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded taxonomy (for debugging)"""
        total_skills = set()

        for role_data in self.role_mappings.values():
            for skill_list in ["core_skills", "framework_skills", "related_skills"]:
                for skill_info in role_data.get(skill_list, []):
                    total_skills.add(skill_info["skill"])

        return {
            "total_roles": len(self.role_mappings),
            "total_unique_skills": len(total_skills),
            "total_synonyms": len(self.skill_synonyms),
            "skill_categories": len(self.skill_categories_info),
            "experience_levels": len(self.experience_mappings),
        }
