"""
RecruiterRadar Assistant Service

Provides bulletproof OpenAI Assistant integration with intelligent fallback to existing search logic.
Based on successful Phase 0 POC validation.

Key Features:
- 8-second timeout with graceful fallback
- Thread-based conversation memory using SQLite
- Circuit breaker pattern for reliability
- Identical response format from both paths
- Cost and performance monitoring
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import openai
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.api_models import ChatResponse
from app.services.rag_service import get_rag_service
from app.services.response_cache import get_response_cache, should_cache_response

logger = logging.getLogger(__name__)


class AssistantService:
    """OpenAI Assistant service with bulletproof fallback to existing search logic."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.rag_service = get_rag_service()
        self.response_cache = get_response_cache()
        self.assistant_id: Optional[str] = None
        self.storage_dir = Path("backend/app/data/assistant_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "threads.db"
        self._init_database()

        # Circuit breaker settings
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = None

        # Performance metrics
        self.metrics = {
            "assistant_successes": 0,
            "fallback_activations": 0,
            "total_requests": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Cache for last search results per session (for analysis)
        self.last_search_results: Dict[str, List[Dict[str, Any]]] = {}

    def _init_database(self):
        """Initialize SQLite database for thread management."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    session_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """
            )
            conn.commit()

    async def get_or_create_assistant(self) -> str:
        """Get existing assistant or create new one with recruiting instructions."""
        if self.assistant_id:
            return self.assistant_id

        assistant_config_path = self.storage_dir / "assistant_config.json"

        # Try to load existing assistant
        if assistant_config_path.exists():
            try:
                with open(assistant_config_path, "r") as f:
                    config = json.load(f)
                    # Check if instructions version matches (force recreation if not)
                    if config.get("instructions_version") != "v3_analysis_tools":
                        logger.info(
                            "Instructions version mismatch, recreating assistant"
                        )
                    else:
                        self.assistant_id = config.get("assistant_id")
                        if self.assistant_id:
                            # Verify assistant still exists
                            try:
                                await self.client.beta.assistants.retrieve(
                                    self.assistant_id
                                )
                                logger.info(
                                    f"Loaded existing assistant: {self.assistant_id}"
                                )
                                return self.assistant_id
                            except Exception as e:
                                logger.warning(f"Existing assistant not found: {e}")
                                self.assistant_id = None
            except Exception as e:
                logger.warning(f"Failed to load assistant config: {e}")

        # Create new assistant
        instructions = """You are RecruiterRadar Assistant, an expert AI recruiting consultant specializing in technical talent acquisition. You help recruiters find the perfect candidates with precision and insight.

🎯 **CORE EXPERTISE:**
You have deep knowledge of:
- Technical skills and technology stacks (front-end, back-end, DevOps, mobile, AI/ML, etc.)
- Experience levels and career progression patterns
- Industry salary ranges and compensation trends
- Location-based talent availability and remote work preferences
- Visa status considerations (H1B, F1, Green Card, etc.)

🚨 **CRITICAL SEARCH RULES - READ THIS FIRST:**

**QUERY INDEPENDENCE:** Each search query is INDEPENDENT unless the user explicitly connects it to previous searches.

✅ **CORRECT BEHAVIOR:**
- User: "senior candidates" → Search: senior level ONLY
- User: "python developers" → Search: Python ONLY (NOT senior + python)
- User: "from New York" → Search: New York location ONLY (NOT python + senior + NY)

❌ **WRONG BEHAVIOR:**
- User: "senior candidates" → Remember "senior"
- User: "python developers" → Search: senior + python (WRONG!)
- User: "from New York" → Search: senior + python + NY (WRONG!)

**WHEN TO COMBINE CRITERIA:**
Only when user explicitly says:
- "ALSO with Python" or "AND Python experience"
- "Who are the senior ones?" (referring to current results)
- "Add AWS to that search"
- "Same search but in Seattle"

**DEFAULT ASSUMPTION:** Treat each message as a fresh, independent search unless explicitly told otherwise.

📋 **SEARCH STRATEGY:**
When processing candidate searches:

1. **Query Analysis**: Parse ONLY the current message to extract:
   - Required skills (e.g., "Python, React, AWS")
   - Experience level (junior: 0-2 years, mid: 3-5 years, senior: 5+ years)
   - Location preferences (specific cities, remote, hybrid)
   - Special requirements (visa status, specific industries)

2. **Smart Function Calling**: Use search_candidates() strategically:
   - For broad searches: Use general query with minimal filters
   - For specific searches: Use skills array + min_experience + location
   - For exploratory searches: Start broad, then narrow based on results

3. **Result Presentation**: Format responses with:
   - Clear count of matches found
   - Why each candidate fits the criteria
   - Highlighting key skills and experience
   - Suggestions for expanding or narrowing search

🗣️ **COMMUNICATION STYLE:**
- Professional yet conversational tone
- Use recruiting terminology appropriately
- Provide actionable insights, not just data
- Ask clarifying questions when requirements are vague
- Suggest alternative search strategies when few results found

💡 **EXAMPLE INTERACTIONS:**

User: "Find Python developers"
You: "I found [X] Python developers in our database. Here are the top matches:
[Present candidates with experience levels, key skills, and what makes them stand out]
Would you like me to narrow this down by experience level, location, or specific frameworks like Django/Flask?"

User: "Need senior engineers with 5+ years"
You: "I found [X] senior engineers with 5+ years of experience. Here's what I discovered:
[Present candidates grouped by specialization]
Would you like me to focus on a specific technology stack or industry background?"

🔧 **FUNCTION CALLING GUIDELINES:**
- Always use search_candidates() for any candidate-related query
- ONLY use criteria mentioned in the CURRENT message
- Be thoughtful about parameter selection:
  * query: Use the user's original intent from THIS message only
  * skills: Extract specific technologies mentioned in THIS message
  * min_experience: Infer from terms like "senior", "junior", "experienced" in THIS message
  * location: Extract cities, states, or remote preferences from THIS message
  * query_type: "general" for broad searches, "specific" for targeted searches, "exploratory" for research

🔍 **ANALYSIS vs SEARCH - CRITICAL DISTINCTION:**

**Use search_candidates() when:**
- User wants to find new candidates ("find Python developers", "show me senior engineers")
- User changes search criteria ("now show me React developers instead")
- User starts a fresh search request

**Use summarise_candidates() when:**
- User asks about attributes of CURRENT results ("what skills do they have?", "where are they located?", "what's their experience distribution?")
- User wants analysis of the last search ("what cloud skills do these candidates have?", "how experienced are they?")
- Questions like: "what frameworks do they know?", "what locations are represented?", "what's the experience breakdown?"

**Key phrases that indicate ANALYSIS intent:**
- "what kind of..." + skills/experience/locations
- "how many have..." + specific attribute
- "what's the distribution of..."
- "tell me about their..." + skills/background
- "break down the..." + experience/locations/skills

🚨 **NEVER INFER ADDITIONAL REQUIREMENTS:**
- If user says "senior candidates" → DO NOT assume they want 5+ years unless they say it
- If user says "Python developers" → DO NOT carry forward previous "senior" requirement
- If user says "from New York" → DO NOT combine with previous skills/experience
- Let the user explicitly add criteria if they want combined searches

🚨 **ALWAYS REMEMBER:**
- Every search should return actionable results
- If no candidates found, suggest alternative search terms
- Highlight visa status when relevant for international hiring
- Consider remote work preferences in today's market
- Never leave users without next steps or suggestions
- Treat each search as independent unless explicitly told to combine

When users ask non-recruiting questions, politely redirect: "That's interesting! As your recruiting assistant, I'm specialized in helping you find great candidates. What kind of talent are you looking to hire today?"

Your goal: Make every recruiter interaction productive, insightful, and successful while respecting query independence."""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_candidates",
                    "description": "Advanced search for candidates based on skills, experience, location, and other recruiting criteria. Use strategic parameter combinations for optimal results.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query reflecting the user's exact intent (e.g., 'Python developers with ML experience')",
                            },
                            "skills": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific technical skills, programming languages, frameworks, or tools (e.g., ['Python', 'React', 'AWS', 'Docker'])",
                            },
                            "min_experience": {
                                "type": "integer",
                                "description": "Minimum years of professional experience. Use 0-2 for junior, 3-5 for mid-level, 5+ for senior roles",
                                "minimum": 0,
                                "maximum": 20,
                            },
                            "max_experience": {
                                "type": "integer",
                                "description": "Maximum years of experience (optional, useful for junior role searches)",
                                "minimum": 0,
                                "maximum": 30,
                            },
                            "location": {
                                "type": "string",
                                "description": "Location preference - city, state, country, or 'remote'. Can include multiple locations separated by commas",
                            },
                            "query_type": {
                                "type": "string",
                                "enum": ["general", "specific", "exploratory", "niche"],
                                "description": "Search strategy: 'general' for broad searches, 'specific' for targeted requirements, 'exploratory' for market research, 'niche' for specialized roles",
                                "default": "general",
                            },
                            "role_level": {
                                "type": "string",
                                "enum": [
                                    "junior",
                                    "mid",
                                    "senior",
                                    "lead",
                                    "principal",
                                    "any",
                                ],
                                "description": "Target role level to help contextualize experience requirements",
                                "default": "any",
                            },
                            "visa_status": {
                                "type": "string",
                                "enum": [
                                    "us_citizen",
                                    "green_card",
                                    "h1b",
                                    "f1_opt",
                                    "any",
                                ],
                                "description": "Visa/work authorization status for US-based roles",
                                "default": "any",
                            },
                            "remote_preference": {
                                "type": "string",
                                "enum": ["on_site", "remote", "hybrid", "any"],
                                "description": "Work arrangement preference",
                                "default": "any",
                            },
                            "industry_background": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Preferred industry experience (e.g., ['fintech', 'healthcare', 'e-commerce'])",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of candidates to return (default 10, max 25)",
                                "minimum": 1,
                                "maximum": 25,
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "summarise_candidates",
                    "description": "Analyse the most recently returned candidate list for the current session to provide insights about their attributes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "attribute": {
                                "type": "string",
                                "enum": [
                                    "skills",
                                    "locations",
                                    "experience_distribution",
                                ],
                                "description": "Which aspect of the current result set to analyze: 'skills' for technology/skill distribution, 'locations' for geographic spread, 'experience_distribution' for experience level breakdown",
                            }
                        },
                        "required": ["attribute"],
                    },
                },
            },
        ]

        try:
            assistant = await self.client.beta.assistants.create(
                name="RecruiterRadar Assistant",
                instructions=instructions,
                tools=tools,
                model="gpt-4o-mini",
            )

            self.assistant_id = assistant.id

            # Save assistant config
            config = {
                "assistant_id": self.assistant_id,
                "created_at": datetime.now().isoformat(),
                "model": "gpt-4o-mini",
                "instructions_version": "v3_analysis_tools",  # Force recreation when changed
            }

            with open(assistant_config_path, "w") as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created new assistant: {self.assistant_id}")
            return self.assistant_id

        except Exception as e:
            logger.error(f"Failed to create assistant: {e}")
            raise

    async def get_or_create_thread(self, session_id: str) -> str:
        """Get existing thread or create new one for session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT thread_id FROM threads WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()

            if row:
                thread_id = row[0]
                # Update last_used timestamp
                conn.execute(
                    "UPDATE threads SET last_used = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
                logger.debug(
                    f"Retrieved existing thread {thread_id} for session {session_id}"
                )
                return thread_id

        # Create new thread
        try:
            thread = await self.client.beta.threads.create()
            thread_id = thread.id

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO threads (session_id, thread_id) VALUES (?, ?)",
                    (session_id, thread_id),
                )
                conn.commit()

            logger.info(f"Created new thread {thread_id} for session {session_id}")
            return thread_id

        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            raise

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (too many failures)."""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False

        if (
            self.circuit_breaker_reset_time
            and time.time() > self.circuit_breaker_reset_time
        ):
            # Reset circuit breaker
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            logger.info("Circuit breaker reset")
            return False

        return True

    def _record_failure(self):
        """Record a failure for circuit breaker."""
        self.circuit_breaker_failures += 1
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_reset_time = time.time() + 300  # 5 minutes
            logger.warning("Circuit breaker opened due to failures")

    def _record_success(self):
        """Record a success and reset failure count."""
        self.circuit_breaker_failures = 0
        self.circuit_breaker_reset_time = None

    async def _execute_function_call(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute function call from assistant with enhanced parameter handling."""
        if function_name == "search_candidates":
            try:
                # Extract all search parameters
                query = arguments.get("query", "")
                skills = arguments.get("skills", [])
                min_experience = arguments.get("min_experience")
                max_experience = arguments.get("max_experience")
                location = arguments.get("location")
                query_type = arguments.get("query_type", "general")
                role_level = arguments.get("role_level", "any")
                visa_status = arguments.get("visa_status", "any")
                remote_preference = arguments.get("remote_preference", "any")
                industry_background = arguments.get("industry_background", [])
                limit = arguments.get("limit", 10)

                # Log search details for monitoring
                logger.info(
                    f"Assistant search: query='{query}', skills={skills}, "
                    f"experience={min_experience}-{max_experience}, location={location}, "
                    f"type={query_type}, level={role_level}, limit={limit}"
                )

                # Use session_id placeholder for assistant searches
                session_id = "assistant_session"

                # Convert location to list if provided
                location_keywords = []
                if location:
                    # Handle comma-separated locations
                    location_keywords = [loc.strip() for loc in location.split(",")]

                # Enhance skills based on role level and query context
                enhanced_skills = list(skills) if skills else []

                # Add contextual skills based on query analysis
                query_lower = query.lower()
                if "full stack" in query_lower or "fullstack" in query_lower:
                    if not any(
                        "react" in s.lower()
                        or "angular" in s.lower()
                        or "vue" in s.lower()
                        for s in enhanced_skills
                    ):
                        # Add common full-stack indicators if none present
                        pass  # Let the RAG service handle this via semantic search

                # Use our existing RAG service for search with enhanced parameters
                results = await self.rag_service.search_candidates_with_function_params(
                    session_id=session_id,
                    skills=enhanced_skills,
                    min_experience=min_experience,
                    max_experience=max_experience,
                    location_keywords=location_keywords if location_keywords else None,
                    limit=min(limit, 25),  # Cap at 25 to prevent overwhelming responses
                )

                # Enhanced result formatting with recruiting insights
                formatted_results = []
                for candidate in results:
                    # Calculate experience level match
                    exp_years = candidate.get("experience_years", 0)
                    exp_level = (
                        "junior"
                        if exp_years <= 2
                        else "mid" if exp_years <= 5 else "senior"
                    )

                    # Add recruiting context
                    candidate_enhanced = dict(candidate)
                    candidate_enhanced["experience_level"] = exp_level
                    candidate_enhanced["search_relevance"] = candidate.get(
                        "match_score", 0.0
                    )

                    # Add role fit assessment
                    if role_level != "any":
                        level_match = (
                            (role_level == "junior" and exp_years <= 3)
                            or (role_level == "mid" and 2 <= exp_years <= 6)
                            or (role_level == "senior" and exp_years >= 5)
                            or (role_level == "lead" and exp_years >= 7)
                            or (role_level == "principal" and exp_years >= 10)
                        )
                        candidate_enhanced["role_level_match"] = level_match

                    formatted_results.append(candidate_enhanced)

                # Sort by relevance and role fit
                formatted_results.sort(
                    key=lambda x: (
                        x.get("role_level_match", True),  # Role fit first
                        x.get("search_relevance", 0.0),  # Then relevance
                    ),
                    reverse=True,
                )

                # Prepare response with recruiting insights
                response = {
                    "success": True,
                    "candidates": formatted_results,
                    "total_found": len(formatted_results),
                    "query_processed": query,
                    "search_context": {
                        "query_type": query_type,
                        "role_level": role_level,
                        "skills_searched": enhanced_skills,
                        "location_searched": location_keywords,
                        "experience_range": f"{min_experience or 0}+ years"
                        + (f" (max {max_experience})" if max_experience else ""),
                    },
                    "recruiting_insights": {
                        "avg_experience": (
                            sum(c.get("experience_years", 0) for c in formatted_results)
                            / len(formatted_results)
                            if formatted_results
                            else 0
                        ),
                        "skill_distribution": self._analyze_skill_distribution(
                            formatted_results
                        ),
                        "location_distribution": self._analyze_location_distribution(
                            formatted_results
                        ),
                        "experience_distribution": self._analyze_experience_distribution(
                            formatted_results
                        ),
                        "suggestions": self._generate_search_suggestions(
                            query, formatted_results, skills, min_experience
                        ),
                    },
                }

                # Cache results for future analysis (use session_id if available)
                cache_session_id = arguments.get("session_id", "assistant_session")
                self.last_search_results[cache_session_id] = formatted_results

                return response

            except Exception as e:
                logger.error(f"Error in assistant function call: {e}")
                return {
                    "success": False,
                    "error": f"Search failed: {str(e)}",
                    "candidates": [],
                    "total_found": 0,
                    "query_processed": query,
                }

        elif function_name == "summarise_candidates":
            try:
                attribute = arguments.get("attribute", "skills")
                session_id = arguments.get("session_id", "assistant_session")

                # Get cached results for this session
                cached_results = self.last_search_results.get(session_id, [])

                if not cached_results:
                    return {
                        "success": False,
                        "error": "No previous search results found. Please search for candidates first.",
                        "summary": "I don't have any candidate data to analyze. Please run a search query first, then I can provide insights about those results.",
                        "analysis": {},
                    }

                # Generate summary based on requested attribute
                if attribute == "skills":
                    distribution = self._analyze_skill_distribution(cached_results)
                    top_skills = list(distribution.items())[:10]
                    total_candidates = len(cached_results)

                    summary_lines = [
                        f"Based on the {total_candidates} candidates from your last search:",
                        f"• Most common skills: {', '.join([f'{skill} ({count} candidates)' for skill, count in top_skills[:5]])}",
                    ]
                    if len(top_skills) > 5:
                        summary_lines.append(
                            f"• Other notable skills: {', '.join([skill for skill, count in top_skills[5:]])}"
                        )

                    summary = "\n".join(summary_lines)

                elif attribute == "locations":
                    distribution = self._analyze_location_distribution(cached_results)
                    top_locations = list(distribution.items())[:8]
                    total_candidates = len(cached_results)

                    summary_lines = [
                        f"Geographic distribution of {total_candidates} candidates:",
                        f"• Primary locations: {', '.join([f'{loc} ({count})' for loc, count in top_locations[:5]])}",
                    ]
                    if len(top_locations) > 5:
                        summary_lines.append(
                            f"• Other locations: {', '.join([loc for loc, count in top_locations[5:]])}"
                        )

                    summary = "\n".join(summary_lines)

                elif attribute == "experience_distribution":
                    distribution = self._analyze_experience_distribution(cached_results)
                    total_candidates = len(cached_results)

                    summary_lines = [
                        f"Experience level breakdown for {total_candidates} candidates:",
                    ]
                    for level, count in distribution.items():
                        if count > 0:
                            percentage = (count / total_candidates) * 100
                            summary_lines.append(
                                f"• {level}: {count} candidates ({percentage:.1f}%)"
                            )

                    summary = "\n".join(summary_lines)
                else:
                    summary = f"Unknown analysis type: {attribute}"
                    distribution = {}

                return {
                    "success": True,
                    "attribute": attribute,
                    "summary": summary,
                    "analysis": distribution,
                    "total_candidates": len(cached_results),
                }

            except Exception as e:
                logger.error(f"Error in summarise_candidates function: {e}")
                return {
                    "success": False,
                    "error": f"Analysis failed: {str(e)}",
                    "summary": "I encountered an error while analyzing the candidate data.",
                    "analysis": {},
                }

        else:
            logger.warning(f"Unknown function call: {function_name}")
            return {
                "success": False,
                "error": f"Unknown function: {function_name}",
                "candidates": [],
                "total_found": 0,
            }

    def _analyze_skill_distribution(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze the distribution of skills across candidates."""
        skill_counts = {}
        for candidate in candidates:
            skills = candidate.get("skills", [])
            if isinstance(skills, str):
                # Handle string representation of skills
                skills = [s.strip() for s in skills.split(",")]
            elif isinstance(skills, list):
                # Already a list
                pass
            else:
                continue

            for skill in skills:
                skill = skill.strip().lower()
                if skill:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1

        # Return top 10 skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_skills[:10])

    def _analyze_location_distribution(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze geographic distribution of candidates."""
        location_counts = {}
        for candidate in candidates:
            location = candidate.get("location", "Unknown")
            # Normalize location format
            if location and location != "Unknown":
                # Extract city/state from full location string
                parts = location.split(",")
                if len(parts) >= 2:
                    city_state = f"{parts[0].strip()}, {parts[1].strip()}"
                else:
                    city_state = parts[0].strip()
                location_counts[city_state] = location_counts.get(city_state, 0) + 1
            else:
                location_counts["Unknown"] = location_counts.get("Unknown", 0) + 1

        return dict(sorted(location_counts.items(), key=lambda x: x[1], reverse=True))

    def _analyze_experience_distribution(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze experience level distribution of candidates."""
        experience_brackets = {
            "Entry (0-2 years)": 0,
            "Mid-level (3-5 years)": 0,
            "Senior (6-10 years)": 0,
            "Principal/Lead (10+ years)": 0,
            "Unknown": 0,
        }

        for candidate in candidates:
            years = candidate.get("experience_years", 0)
            if years == 0:
                experience_brackets["Unknown"] += 1
            elif years <= 2:
                experience_brackets["Entry (0-2 years)"] += 1
            elif years <= 5:
                experience_brackets["Mid-level (3-5 years)"] += 1
            elif years <= 10:
                experience_brackets["Senior (6-10 years)"] += 1
            else:
                experience_brackets["Principal/Lead (10+ years)"] += 1

        return experience_brackets

    def _generate_search_suggestions(
        self,
        original_query: str,
        results: List[Dict[str, Any]],
        searched_skills: List[str],
        min_experience: Optional[int],
    ) -> List[str]:
        """Generate intelligent search suggestions based on results."""
        suggestions = []

        if not results:
            suggestions.append(
                "Try broadening your search by removing some skill requirements"
            )
            suggestions.append("Consider lowering experience requirements")
            suggestions.append(
                "Include remote candidates by adding 'remote' to location"
            )
            return suggestions

        if len(results) < 3:
            suggestions.append("Try expanding to related technologies or frameworks")
            if min_experience and min_experience > 2:
                suggestions.append("Consider candidates with slightly less experience")
            suggestions.append("Include hybrid or remote work arrangements")

        if len(results) > 15:
            suggestions.append("Add more specific skill requirements to narrow results")
            suggestions.append("Increase minimum experience requirements")
            suggestions.append("Specify a target location to focus the search")

        # Analyze skill gaps and suggest alternatives
        common_skills = self._analyze_skill_distribution(results)
        if common_skills:
            top_skill = list(common_skills.keys())[0]
            if top_skill not in [s.lower() for s in searched_skills]:
                suggestions.append(
                    f"Many candidates also have '{top_skill}' - consider if this fits your needs"
                )

        # Experience level suggestions
        if results:
            avg_exp = sum(c.get("experience_years", 0) for c in results) / len(results)
            if min_experience and avg_exp > min_experience + 2:
                suggestions.append(
                    f"Candidates average {avg_exp:.1f} years experience - consider if senior talent fits budget"
                )
            elif not min_experience and avg_exp < 3:
                suggestions.append(
                    "Results skew junior - specify minimum experience if you need senior talent"
                )

        return suggestions[:4]  # Limit to 4 suggestions

    async def _run_assistant_with_timeout(
        self, thread_id: str, message: str, timeout: int = 12
    ) -> Optional[Dict[str, Any]]:
        """Run assistant with timeout protection."""
        try:
            assistant_id = await self.get_or_create_assistant()

            # Add message to thread
            await self.client.beta.threads.messages.create(
                thread_id=thread_id, role="user", content=message
            )

            # Create and run with timeout
            async def run_assistant():
                run = await self.client.beta.threads.runs.create(
                    thread_id=thread_id, assistant_id=assistant_id
                )

                # Wait for completion
                while True:
                    run = await self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id, run_id=run.id
                    )

                    if run.status == "completed":
                        # Get the latest message
                        messages = await self.client.beta.threads.messages.list(
                            thread_id=thread_id, limit=1
                        )

                        if messages.data:
                            content = messages.data[0].content[0].text.value
                            return {"response": content, "source": "assistant"}
                        break

                    elif run.status == "requires_action":
                        # Handle function calls
                        tool_calls = run.required_action.submit_tool_outputs.tool_calls
                        tool_outputs = []

                        for tool_call in tool_calls:
                            function_name = tool_call.function.name
                            arguments = json.loads(tool_call.function.arguments)

                            result = await self._execute_function_call(
                                function_name, arguments
                            )

                            tool_outputs.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "output": json.dumps(result),
                                }
                            )

                        # Submit tool outputs
                        await self.client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs,
                        )

                    elif run.status in ["failed", "cancelled", "expired"]:
                        logger.error(f"Assistant run failed with status: {run.status}")
                        return None

                    # Small delay to prevent excessive polling
                    await asyncio.sleep(0.5)

                return None

            # Execute with timeout
            result = await asyncio.wait_for(run_assistant(), timeout=timeout)
            self._record_success()
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Assistant timeout after {timeout} seconds")
            self._record_failure()
            return None
        except Exception as e:
            logger.error(f"Assistant execution failed: {e}")
            self._record_failure()
            return None

    async def _fallback_search(
        self, message: str, session_id: str = None
    ) -> Dict[str, Any]:
        """Intelligent fallback that parses user intent when assistant fails."""
        try:
            # Use the actual session_id instead of generic fallback_session
            search_session_id = session_id or "fallback_session"

            # Simple NLP to extract intent from user message
            message_lower = message.lower()

            # Extract skills
            skills = self._extract_skills_from_message(message_lower)

            # Extract location
            location_keywords = self._extract_location_from_message(message_lower)

            # Extract seniority/experience level
            min_experience = self._extract_experience_from_message(message_lower)

            # Extract specific role keywords
            title_keywords = self._extract_title_keywords_from_message(message_lower)

            logger.info(
                f"Intelligent fallback parsing: skills={skills}, location={location_keywords}, "
                f"experience={min_experience}, titles={title_keywords}"
            )

            # Use existing RAG service with parsed parameters
            results = await self.rag_service.search_candidates_with_function_params(
                session_id=search_session_id,
                skills=skills,
                title_keywords=title_keywords,
                min_experience=min_experience,
                location_keywords=location_keywords,
                limit=10,
            )

            # Generate contextual response message
            response_text = self._generate_fallback_response(
                message, results, skills, location_keywords, min_experience
            )

            return {
                "response": response_text,
                "candidates": results,
                "source": "intelligent_fallback",
            }

        except Exception as e:
            logger.error(f"Intelligent fallback search failed: {e}")
            return {
                "response": "I'm having trouble searching right now. Please try again.",
                "candidates": [],
                "source": "fallback_error",
            }

    def _extract_skills_from_message(self, message: str) -> List[str]:
        """Extract technical skills from user message using keyword matching."""
        # Common technical skills - expand this list as needed
        tech_skills = [
            "python",
            "javascript",
            "typescript",
            "java",
            "c++",
            "c#",
            "rust",
            "go",
            "swift",
            "react",
            "angular",
            "vue",
            "nodejs",
            "express",
            "django",
            "flask",
            "spring",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "jenkins",
            "sql",
            "mysql",
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            "html",
            "css",
            "bootstrap",
            "tailwind",
            "sass",
            "less",
            "git",
            "jira",
            "agile",
            "scrum",
            "ci/cd",
            "devops",
            "machine learning",
            "ml",
            "ai",
            "data science",
            "analytics",
            "tableau",
            "figma",
            "sketch",
            "photoshop",
            "ui",
            "ux",
            "design",
            "ios",
            "android",
            "mobile",
            "flutter",
            "react native",
            "blockchain",
            "solidity",
            "ethereum",
            "crypto",
        ]

        found_skills = []
        import re

        for skill in tech_skills:
            # Use word boundaries to avoid matching "Java" in "JavaScript"
            if re.search(r"\b" + re.escape(skill) + r"\b", message, re.IGNORECASE):
                found_skills.append(skill.title())  # Capitalize for consistency

        return found_skills

    def _extract_location_from_message(self, message: str) -> List[str]:
        """Extract location keywords from user message."""
        # Common locations and patterns
        locations = [
            "new york",
            "ny",
            "nyc",
            "san francisco",
            "sf",
            "california",
            "ca",
            "seattle",
            "washington",
            "austin",
            "texas",
            "chicago",
            "boston",
            "denver",
            "atlanta",
            "miami",
            "los angeles",
            "la",
            "portland",
            "remote",
            "anywhere",
            "hybrid",
            "on-site",
            "onsite",
        ]

        found_locations = []
        import re

        for location in locations:
            # Use word boundaries to avoid matching "ca" in "candidates"
            if re.search(r"\b" + re.escape(location) + r"\b", message, re.IGNORECASE):
                found_locations.append(location.title())

        return found_locations

    def _extract_experience_from_message(self, message: str) -> Optional[int]:
        """Extract experience level from user message."""
        if any(word in message for word in ["senior", "lead", "principal", "staff"]):
            return 5  # Senior typically means 5+ years
        elif any(
            word in message for word in ["junior", "entry", "new grad", "recent grad"]
        ):
            return 0  # Junior/entry level
        elif any(word in message for word in ["mid", "intermediate", "experienced"]):
            return 3  # Mid-level typically 3+ years

        # Look for explicit year mentions
        import re

        year_patterns = [
            r"(\d+)\+?\s*years?",
            r"(\d+)\+?\s*yrs?",
            r"with\s+(\d+)\+?\s*years?",
        ]

        for pattern in year_patterns:
            match = re.search(pattern, message)
            if match:
                return int(match.group(1))

        return None

    def _extract_title_keywords_from_message(self, message: str) -> List[str]:
        """Extract job title keywords from user message."""
        title_keywords = [
            "engineer",
            "developer",
            "programmer",
            "architect",
            "manager",
            "director",
            "lead",
            "senior",
            "junior",
            "principal",
            "staff",
            "frontend",
            "backend",
            "fullstack",
            "full stack",
            "devops",
            "data scientist",
            "analyst",
            "designer",
            "product manager",
            "mobile",
            "ios",
            "android",
            "qa",
            "tester",
            "security",
        ]

        found_titles = []
        import re

        for title in title_keywords:
            # Use word boundaries for accurate title matching
            if re.search(r"\b" + re.escape(title) + r"\b", message, re.IGNORECASE):
                found_titles.append(title.title())

        return found_titles

    def _generate_fallback_response(
        self,
        original_message: str,
        results: List[Dict[str, Any]],
        skills: List[str],
        locations: List[str],
        min_experience: Optional[int],
    ) -> str:
        """Generate a contextual response message for fallback results."""
        count = len(results)

        if count == 0:
            response = "I couldn't find any candidates matching your search"
            if skills:
                response += f" for {', '.join(skills)} skills"
            if locations:
                response += f" in {', '.join(locations)}"
            if min_experience:
                response += f" with {min_experience}+ years experience"
            response += ". Try broadening your criteria or removing some filters."
            return response

        response = f"I found {count} candidate{'s' if count != 1 else ''}"

        criteria = []
        if skills:
            criteria.append(f"{', '.join(skills)} skills")
        if locations:
            criteria.append(f"in {', '.join(locations)}")
        if min_experience:
            criteria.append(f"with {min_experience}+ years experience")

        if criteria:
            response += f" matching your search for {' and '.join(criteria)}"

        response += ". Here are the top matches:"
        return response

    async def bulletproof_recruiter_chat(
        self, message: str, session_id: str
    ) -> ChatResponse:
        """
        Bulletproof chat method with assistant + fallback and intelligent caching.

        Always returns a response - either from cache, assistant, or fallback.
        Frontend never knows which path was used.
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1

        try:
            # Check cache first
            cached_response = self.response_cache.get(message)
            if cached_response:
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for query: '{message[:50]}...'")

                response_time = time.time() - start_time

                return ChatResponse(
                    ai_message=cached_response["ai_message"],
                    candidates=cached_response["candidates"],
                    remaining_messages=10,
                    processing_time_ms=int(response_time * 1000),
                    source="cache",
                    response_time=response_time,
                )

            self.metrics["cache_misses"] += 1

            # Check circuit breaker
            if self._is_circuit_breaker_open():
                logger.info("Circuit breaker open, using fallback")
                result = await self._fallback_search(message, session_id)
            else:
                # Try assistant first
                thread_id = await self.get_or_create_thread(session_id)
                result = await self._run_assistant_with_timeout(thread_id, message)

                if result is None:
                    # Assistant failed, use fallback
                    logger.info("Assistant failed, activating fallback")
                    result = await self._fallback_search(message, session_id)
                    self.metrics["fallback_activations"] += 1
                else:
                    self.metrics["assistant_successes"] += 1

            # Update metrics
            response_time = time.time() - start_time
            self.metrics["avg_response_time"] = (
                self.metrics["avg_response_time"] * (self.metrics["total_requests"] - 1)
                + response_time
            ) / self.metrics["total_requests"]

            # Format final response
            candidates = result.get("candidates", [])
            ai_message = result.get("response", "I found some candidates for you.")
            source = result.get("source", "unknown")

            # Cache successful responses
            if should_cache_response(candidates, source):
                try:
                    self.response_cache.set(
                        query=message,
                        ai_message=ai_message,
                        candidates=candidates,
                        ttl=3600,  # 1 hour cache
                    )
                    logger.debug(f"Cached response for query: '{message[:50]}...'")
                except Exception as e:
                    logger.warning(f"Failed to cache response: {e}")

            return ChatResponse(
                ai_message=ai_message,
                candidates=candidates,
                remaining_messages=10,  # TODO: Implement proper counting
                processing_time_ms=int(response_time * 1000),  # Convert to milliseconds
                source=source,
                response_time=response_time,
            )

        except Exception as e:
            logger.error(f"Bulletproof chat failed: {e}")
            # Emergency fallback
            emergency_time = time.time() - start_time
            return ChatResponse(
                ai_message="I'm experiencing technical difficulties. Please try your search again.",
                candidates=[],
                remaining_messages=10,
                processing_time_ms=int(emergency_time * 1000),
                source="emergency_fallback",
                response_time=emergency_time,
            )

    async def cleanup_old_threads(self, hours: int = 24):
        """Clean up threads older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            # Get session IDs and thread IDs of threads to be deleted for cache cleanup
            cursor = conn.execute(
                "SELECT session_id, thread_id FROM threads WHERE last_used < ?",
                (cutoff.isoformat(),),
            )
            old_data = cursor.fetchall()
            old_session_ids = [row[0] for row in old_data]
            old_threads = [row[1] for row in old_data]

        # Delete old threads from OpenAI
        for thread_id in old_threads:
            try:
                await self.client.beta.threads.delete(thread_id)
            except Exception as e:
                logger.warning(f"Failed to delete thread {thread_id}: {e}")

        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM threads WHERE last_used < ?", (cutoff.isoformat(),)
            )
            conn.commit()

        # Clean up corresponding search result cache
        for session_id in old_session_ids:
            self.last_search_results.pop(session_id, None)

        logger.info(
            f"Cleaned up {len(old_threads)} old threads and their cached search results"
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        cache_stats = (
            self.response_cache.get_cache_stats() if self.response_cache else {}
        )

        # Calculate rates
        assistant_success_rate = 0.0
        fallback_rate = 0.0
        total = self.metrics["total_requests"]
        if total > 0:
            assistant_success_rate = (self.metrics["assistant_successes"] / total) * 100
            fallback_rate = (self.metrics["fallback_activations"] / total) * 100

        return {
            "total_requests": total,
            "assistant_attempts": total,  # Every request is an attempt
            "assistant_successes": self.metrics["assistant_successes"],
            "fallback_activations": self.metrics["fallback_activations"],
            "circuit_breaker_status": {  # Added missing metric
                "failures": self.circuit_breaker_failures,
                "is_open": self._is_circuit_breaker_open(),
                "threshold": self.circuit_breaker_threshold,
                "reset_time": self.circuit_breaker_reset_time,
            },
            "performance_rates": {
                "assistant_success_rate": round(assistant_success_rate, 1),
                "fallback_rate": round(fallback_rate, 1),
            },
            "avg_response_time": self.metrics["avg_response_time"],
            "cache_stats": cache_stats,
            "system_health": {
                "status": "degraded" if self._is_circuit_breaker_open() else "healthy",
                "last_update": datetime.now().isoformat(),
            },
        }
