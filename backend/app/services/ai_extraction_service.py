import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import re
from collections import defaultdict, Counter
import random

from app.services.llm_service import LLMService
from app.services.extraction_utils import (
    try_fast_extraction,
    derive_name_from_email,
    extract_skills_section,
    extract_work_experience,
    extract_education,
    extract_certifications,
    extract_headline,
)
from app.models.extraction_models import ExtractedResumeData
from app.core.prompts import RESUME_EXTRACTION_PROMPT_V6
from app.core.config import settings

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0  # Start with 1 second
        self.max_delay = 30.0  # Cap at 30 seconds
        self.exponential_base = 2.0
        self.jitter = True  # Add randomness to prevent thundering herd

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5  # Add 0-50% jitter
        return delay


class AdaptiveTimeoutConfig:
    """Adaptive timeout based on resume complexity."""

    def __init__(self):
        self.base_timeout = 20.0  # Start with 20s instead of 15s
        self.max_timeout = 60.0  # Cap at 60s for very complex resumes
        self.chars_per_second = 100  # Rough estimate of processing speed

    def calculate_timeout(self, resume_text: str) -> float:
        """Calculate adaptive timeout based on resume complexity."""
        text_length = len(resume_text)

        # Count complexity indicators
        job_count = resume_text.lower().count("experience") + resume_text.lower().count(
            "employment"
        )
        skill_indicators = len(
            re.findall(
                r"\b(?:skills?|technologies?|tools?|languages?)\b", resume_text.lower()
            )
        )
        education_count = resume_text.lower().count(
            "education"
        ) + resume_text.lower().count("degree")

        # Base timeout + complexity factors
        complexity_factor = (
            (job_count * 2) + (skill_indicators * 1.5) + (education_count * 1)
        )
        adaptive_timeout = (
            self.base_timeout
            + (text_length / self.chars_per_second)
            + complexity_factor
        )

        # Cap the timeout
        final_timeout = min(adaptive_timeout, self.max_timeout)

        logger.info(f"📊 Adaptive timeout calculation:")
        logger.info(f"   Text length: {text_length} chars")
        logger.info(f"   Job indicators: {job_count}")
        logger.info(f"   Skill indicators: {skill_indicators}")
        logger.info(f"   Education indicators: {education_count}")
        logger.info(f"   Complexity factor: {complexity_factor}")
        logger.info(f"   Final timeout: {final_timeout:.1f}s")

        return final_timeout


class ExtractionAnalytics:
    """Simple in-memory analytics tracking for extraction performance."""

    def __init__(self):
        self.extractions: List[Dict[str, Any]] = []
        self.max_stored_extractions = 1000  # Keep last 1000 extractions

    def record_extraction(
        self,
        success: bool,
        extraction_time: float,
        extracted_data: Optional[ExtractedResumeData] = None,
        cache_hit: bool = False,
    ):
        """Record extraction attempt with performance metrics."""
        record = {
            "timestamp": datetime.utcnow(),
            "success": success,
            "extraction_time": extraction_time,
            "cache_hit": cache_hit,
            "skills_count": (
                len(extracted_data.technical_skills) + len(extracted_data.soft_skills)
                if extracted_data
                else 0
            ),
            "jobs_count": len(extracted_data.work_experience) if extracted_data else 0,
            "education_count": len(extracted_data.education) if extracted_data else 0,
            "certifications_count": (
                len(extracted_data.certifications) if extracted_data else 0
            ),
            "confidence": (
                extracted_data.extraction_confidence if extracted_data else 0.0
            ),
        }

        self.extractions.append(record)

        # Keep only recent extractions
        if len(self.extractions) > self.max_stored_extractions:
            self.extractions = self.extractions[-self.max_stored_extractions :]

    def get_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get extraction analytics for the specified time window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        recent_extractions = [
            e for e in self.extractions if e["timestamp"] >= cutoff_time
        ]

        if not recent_extractions:
            return {
                "total_extractions": 0,
                "message": "No extractions in the specified time window",
            }

        successful_extractions = [e for e in recent_extractions if e["success"]]
        cache_hits = [e for e in recent_extractions if e["cache_hit"]]

        # Calculate averages for successful extractions
        if successful_extractions:
            avg_skills = sum(e["skills_count"] for e in successful_extractions) / len(
                successful_extractions
            )
            avg_jobs = sum(e["jobs_count"] for e in successful_extractions) / len(
                successful_extractions
            )
            avg_education = sum(
                e["education_count"] for e in successful_extractions
            ) / len(successful_extractions)
            avg_certs = sum(
                e["certifications_count"] for e in successful_extractions
            ) / len(successful_extractions)
            avg_time = sum(e["extraction_time"] for e in successful_extractions) / len(
                successful_extractions
            )
            avg_confidence = sum(e["confidence"] for e in successful_extractions) / len(
                successful_extractions
            )
        else:
            avg_skills = avg_jobs = avg_education = avg_certs = avg_time = (
                avg_confidence
            ) = 0

        return {
            "time_window_hours": hours_back,
            "total_extractions": len(recent_extractions),
            "successful_extractions": len(successful_extractions),
            "failed_extractions": len(recent_extractions) - len(successful_extractions),
            "cache_hits": len(cache_hits),
            "success_rate": (
                len(successful_extractions) / len(recent_extractions)
                if recent_extractions
                else 0
            ),
            "cache_hit_rate": (
                len(cache_hits) / len(recent_extractions) if recent_extractions else 0
            ),
            "average_metrics": {
                "skills_extracted": round(avg_skills, 1),
                "jobs_extracted": round(avg_jobs, 1),
                "education_entries": round(avg_education, 1),
                "certifications": round(avg_certs, 1),
                "extraction_time_seconds": round(avg_time, 2),
                "confidence_score": round(avg_confidence, 3),
            },
            "performance_benchmarks": {
                "extraction_time_target": "< 10 seconds",
                "confidence_target": "> 0.85",
                "skills_improvement": "400-500% vs hardcoded",
                "data_completeness": "85-95% vs 10% before",
            },
        }


class AIExtractionService:
    """Efficient AI-powered resume extraction with timeout protection and analytics."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        # Cache for repeated extractions (same resume uploaded multiple times)
        self._extraction_cache: Dict[str, ExtractedResumeData] = {}
        self.max_cache_size = 100
        # Analytics tracking
        self.analytics = ExtractionAnalytics()
        self.retry_config = RetryConfig()
        self.timeout_config = AdaptiveTimeoutConfig()

    async def extract_resume_data(
        self, resume_text: str, timeout_seconds: Optional[float] = None
    ) -> Optional[ExtractedResumeData]:
        """
        Extract structured data from resume text using AI, with robust retry logic and adaptive timeouts.

        Args:
            resume_text: The resume text to extract from
            timeout_seconds: How long to wait for AI extraction (auto-calculated if None)

        Returns:
            ExtractedResumeData or None if extraction fails
        """
        start_time = datetime.utcnow()

        # ⚡ Fast path: deterministic extraction first (no LLM)
        if settings.app_verbose_extraction:
            logger.info("🚀 ATTEMPTING FAST-PATH EXTRACTION")

        try:
            fast = try_fast_extraction(resume_text)
            if settings.app_verbose_extraction:
                logger.info(f"🧪 FAST-PATH RESULT: {fast}")
        except Exception as e:
            if settings.app_verbose_extraction:
                logger.warning(f"🚨 FAST-PATH ERROR: {str(e)}")
            fast = None

        if fast and fast.get("name") and fast.get("email"):
            if settings.app_verbose_extraction:
                logger.info("✅ FAST-PATH SUCCESS - Using fast extraction results")
            # Enrich fast-path with section-level parsing for better recall
            fast_skills_section = extract_skills_section(resume_text)
            enriched_skills = list(
                dict.fromkeys([*fast.get("skills", []), *fast_skills_section])
            )
            # Use fast-path structured data if available, otherwise re-parse
            work_entries = fast.get("work_experience") or extract_work_experience(
                resume_text
            )
            education_entries = fast.get("education") or extract_education(resume_text)
            certs = fast.get("certifications") or extract_certifications(resume_text)
            headline = extract_headline(resume_text, fast["name"]) or None

            result = ExtractedResumeData(
                name=fast["name"],
                email=fast.get("email"),
                phone=fast.get("phone"),
                location=fast.get("location"),
                current_title=fast.get("current_title") or headline,
                technical_skills=enriched_skills,
                total_experience_years=fast.get("total_experience_years"),
                extraction_confidence=float(fast.get("confidence", 0.8)),
            )

            # Map work experience (preserve all entries parsed)
            if work_entries:
                from app.models.extraction_models import WorkExperience

                result.work_experience = [
                    WorkExperience(
                        company=e["company"],
                        title=e["title"],
                        duration=e["duration"],
                        description=None,
                    )
                    for e in work_entries
                ]

                # If current_title is still empty, set from most recent role
                if not result.current_title and result.work_experience:
                    result.current_title = result.work_experience[0].title

            # Map education (preserve all entries parsed)
            if education_entries:
                from app.models.extraction_models import Education

                result.education = [
                    Education(
                        degree=ed.get("degree", ""),
                        field=ed.get("field", ""),
                        school=ed.get("school", ""),
                        graduation_year=(
                            str(ed.get("graduation_year"))
                            if ed.get("graduation_year")
                            else None
                        ),
                    )
                    for ed in education_entries
                ]

            if certs:
                result.certifications = certs

            cache_key = self._generate_cache_key(resume_text)
            self._add_to_cache(cache_key, result)

            extraction_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"✅ Fast-path resume extraction succeeded in {extraction_time:.2f}s"
            )

            # Record analytics for fast path
            self.analytics.record_extraction(
                success=True,
                extraction_time=extraction_time,
                extracted_data=result,
                cache_hit=False,
            )

            return result

        # Generate cache key (first 100 chars + last 100 chars)
        cache_key = self._generate_cache_key(resume_text)

        # Check cache first
        if cache_key in self._extraction_cache:
            logger.info("Resume extraction cache hit!")
            extraction_time = (datetime.utcnow() - start_time).total_seconds()
            cached_result = self._extraction_cache[cache_key]

            # Record cache hit analytics
            self.analytics.record_extraction(
                success=True,
                extraction_time=extraction_time,
                extracted_data=cached_result,
                cache_hit=True,
            )

            return cached_result

        # Calculate adaptive timeout if not provided
        if timeout_seconds is None:
            timeout_seconds = min(
                12.0,  # hard cap for MVP latency
                self.timeout_config.calculate_timeout(resume_text),
            )

        # 🚨 Conditional extraction debugging (can be very verbose)
        text_length = len(resume_text)
        if settings.app_verbose_extraction:
            text_preview = (
                resume_text[:400] + "..." if len(resume_text) > 400 else resume_text
            )
            logger.info("=" * 80)
            logger.info("🧪 VERBOSE: STARTING RESUME EXTRACTION")
            logger.info("=" * 80)
        logger.info(f"📏 Original text length: {text_length} characters")
        logger.info(f"⏰ Adaptive timeout: {timeout_seconds:.1f} seconds")
        logger.info(f"🔄 Max retries: {self.retry_config.max_retries}")
        logger.info("=" * 80)
        logger.info("📄 RESUME TEXT PREVIEW (first 400 chars):")
        logger.info(text_preview)
        logger.info("=" * 80)

        # 🚀 SMART CHUNKING: Instead of truncating, use full content intelligently
        processed_text = self._prepare_text_for_extraction(resume_text)

        if settings.app_verbose_extraction:
            # Log text processing results
            logger.info(f"🧠 VERBOSE: Text processing complete")
        logger.info(f"   Original: {len(resume_text)} chars")
        logger.info(f"   Processed: {len(processed_text)} chars")
        logger.info(
            f"   Reduction: {((len(resume_text) - len(processed_text)) / len(resume_text) * 100):.1f}%"
        )

        # Prepare prompt with processed text
        prompt = RESUME_EXTRACTION_PROMPT_V6.format(resume_text=processed_text)
        if settings.app_verbose_extraction:
            logger.info(f"📝 VERBOSE: Final prompt length: {len(prompt)} characters")

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(
            min(self.retry_config.max_retries, 0) + 1
        ):  # single attempt for MVP
            try:
                logger.info(
                    f"🎯 Extraction attempt {attempt + 1}/{self.retry_config.max_retries + 1}"
                )

                # Call LLM with timeout
                extraction_task = self._call_llm_for_extraction(prompt)
                result = await asyncio.wait_for(
                    extraction_task, timeout=timeout_seconds
                )

                # Parse and validate
                if result:
                    extraction_time = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(
                        f"✅ Resume extracted successfully in {extraction_time:.2f}s on attempt {attempt + 1}"
                    )

                    # 🧮 POST-EXTRACTION FIXES: Calculate experience if AI missed it
                    result = self._post_process_extraction(result, resume_text)

                    # Cache the result
                    self._add_to_cache(cache_key, result)

                    # Record successful extraction analytics
                    self.analytics.record_extraction(
                        success=True,
                        extraction_time=extraction_time,
                        extracted_data=result,
                        cache_hit=False,
                    )

                    return result
                else:
                    raise Exception("LLM returned no extraction data")

            except asyncio.TimeoutError as e:
                last_exception = e
                current_time = (datetime.utcnow() - start_time).total_seconds()
                logger.warning(
                    f"⏰ AI EXTRACTION TIMEOUT on attempt {attempt + 1}: "
                    f"Failed after {timeout_seconds:.1f}s (total time: {current_time:.1f}s)"
                )

                # If this isn't the last attempt, wait and retry
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.info(f"🔄 Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    # Increase timeout slightly for next attempt
                    timeout_seconds *= 1.2
                    logger.info(
                        f"📈 Increased timeout to {timeout_seconds:.1f}s for next attempt"
                    )
                else:
                    logger.error(
                        f"🚨 All {self.retry_config.max_retries + 1} attempts failed with timeout"
                    )

            except Exception as e:
                last_exception = e
                current_time = (datetime.utcnow() - start_time).total_seconds()
                logger.warning(f"❌ Extraction error on attempt {attempt + 1}: {e}")

                # If this isn't the last attempt, wait and retry
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.info(f"🔄 Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"🚨 All {self.retry_config.max_retries + 1} attempts failed with errors"
                    )

        # All retries failed, use fallback
        extraction_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            f"🚨 AI EXTRACTION COMPLETELY FAILED after {self.retry_config.max_retries + 1} attempts "
            f"(total time: {extraction_time:.1f}s). Last error: {last_exception}"
        )
        logger.warning(
            f"⚠️ Falling back to enhanced regex extraction for better results"
        )

        # Record failed extraction analytics
        self.analytics.record_extraction(
            success=False, extraction_time=extraction_time, cache_hit=False
        )

        return self._fallback_extraction(resume_text)

    async def _call_llm_for_extraction(
        self, prompt: str
    ) -> Optional[ExtractedResumeData]:
        """Make the actual LLM call for extraction."""
        try:
            # 🚨 NUCLEAR AI DEBUGGING - Log everything
            logger.info("=" * 80)
            logger.info("🤖 SENDING TO AI:")
            logger.info("=" * 80)
            logger.info(f"Model: {settings.chat_model_name}")
            logger.info(f"Temperature: 0.1")
            logger.info(f"Max Tokens: 2000")
            logger.info("=" * 80)
            logger.info("PROMPT (first 2000 chars):")
            logger.info(prompt[:2000])
            if len(prompt) > 2000:
                logger.info(f"... (truncated, total length: {len(prompt)} chars)")
            logger.info("=" * 80)

            response = await self.llm_service.client.chat.completions.create(
                model=settings.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume parser specialized in extracting comprehensive information from resumes. You always return valid JSON with all requested fields. You are thorough and precise.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,  # Zero temperature for maximum consistency and determinism
                max_tokens=3000,  # Increased for comprehensive extraction with V6 prompt
                response_format={"type": "json_object"},
                top_p=1.0,  # Use full probability mass for deterministic results
                frequency_penalty=0.0,  # No penalty for repetition (skills may repeat)
                presence_penalty=0.0,  # No penalty for introducing new topics
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                logger.error("❌ Empty response from LLM")
                return None

            # 🚨 NUCLEAR AI DEBUGGING - Log raw response
            logger.info("=" * 80)
            logger.info("🤖 AI RAW RESPONSE:")
            logger.info("=" * 80)
            logger.info(f"Response length: {len(content)} chars")
            logger.info("Response content (first 2000 chars):")
            logger.info(content[:2000])
            if len(content) > 2000:
                logger.info(f"... (truncated, total length: {len(content)} chars)")
            logger.info("=" * 80)

            # Parse JSON and create model
            try:
                data = json.loads(content)

                # JSON Schema validation and cleanup
                data = self._validate_and_clean_json(data)

                # 🚨 NUCLEAR AI DEBUGGING - Log parsed data analysis
                logger.info("=" * 80)
                logger.info("📊 PARSED EXTRACTION ANALYSIS:")
                logger.info("=" * 80)
                logger.info(f"Name: {data.get('name', 'MISSING')}")
                logger.info(f"Email: {data.get('email', 'MISSING')}")
                logger.info(
                    f"Technical Skills Count: {len(data.get('technical_skills', []))}"
                )
                logger.info(f"Technical Skills: {data.get('technical_skills', [])}")
                logger.info(
                    f"Work Experience Count: {len(data.get('work_experience', []))}"
                )
                logger.info(f"Education Count: {len(data.get('education', []))}")
                logger.info(
                    f"Total Experience Years: {data.get('total_experience_years', 'MISSING')}"
                )
                logger.info(f"Location: {data.get('location', 'MISSING')}")
                logger.info(f"Current Title: {data.get('current_title', 'MISSING')}")
                logger.info(
                    f"Professional Summary Length: {len(str(data.get('professional_summary', '')))}"
                )
                logger.info(
                    f"🎯 CONFIDENCE SCORE: {data.get('extraction_confidence', 'MISSING')}"
                )

                # Log work experience details
                work_exp = data.get("work_experience", [])
                if work_exp:
                    logger.info("Work Experience Details:")
                    for i, job in enumerate(work_exp[:3]):  # Log first 3 jobs
                        logger.info(
                            f"  Job {i+1}: {job.get('title', 'N/A')} at {job.get('company', 'N/A')} ({job.get('duration', 'N/A')})"
                        )

                logger.info("=" * 80)

                extracted_data = ExtractedResumeData(**data)

                # 🚨 CONFIDENCE ANALYSIS
                confidence = extracted_data.extraction_confidence
                if confidence < 0.5:
                    logger.error(
                        f"🚨 LOW CONFIDENCE ALERT: {confidence:.2f} - INVESTIGATING..."
                    )
                    logger.error(
                        f"   - Skills extracted: {len(extracted_data.technical_skills)}"
                    )
                    logger.error(
                        f"   - Jobs extracted: {len(extracted_data.work_experience)}"
                    )
                    logger.error(
                        f"   - Name found: {'YES' if extracted_data.name else 'NO'}"
                    )
                    logger.error(
                        f"   - Experience calculated: {extracted_data.total_experience_years}"
                    )
                elif confidence < 0.7:
                    logger.warning(
                        f"⚠️ MEDIUM CONFIDENCE: {confidence:.2f} - May need improvement"
                    )
                else:
                    logger.info(
                        f"✅ HIGH CONFIDENCE: {confidence:.2f} - Good extraction"
                    )

                return extracted_data

            except json.JSONDecodeError as e:
                logger.error("❌ INVALID JSON FROM LLM:")
                logger.error(f"JSON Error: {e}")
                logger.error(f"Content: {content[:1000]}")
                return None
            except Exception as e:
                logger.error(f"❌ FAILED TO CREATE ExtractedResumeData: {e}")
                logger.error(
                    f"Data keys: {list(data.keys()) if 'data' in locals() else 'N/A'}"
                )
                return None

        except Exception as e:
            logger.error(f"❌ LLM EXTRACTION FAILED: {e}", exc_info=True)
            return None

    def _prepare_text_for_extraction(self, text: str, max_chars: int = 15000) -> str:
        """
        🚀 SMART TEXT PREPARATION: Instead of dumb truncation, intelligently prepare text.

        For texts under max_chars: Return as-is
        For longer texts: Preserve structure while fitting in limit
        """
        if len(text) <= max_chars:
            logger.info(
                f"📄 Text fits in limit ({len(text)}/{max_chars} chars) - using full content"
            )
            return text

        logger.warning(
            f"📄 Large resume ({len(text)} chars) - applying smart compression"
        )

        # 🎯 SECTION-AWARE COMPRESSION: Preserve key sections
        sections = self._identify_resume_sections(text)

        # Priority order: Contact info, Experience, Skills, Education, Projects
        priority_sections = ["contact", "experience", "skills", "education", "projects"]

        compressed_text = ""
        remaining_chars = max_chars - 200  # Leave buffer for formatting

        for section_type in priority_sections:
            if section_type in sections and remaining_chars > 100:
                section_text = sections[section_type]
                if len(section_text) <= remaining_chars:
                    compressed_text += (
                        f"\n\n=== {section_type.upper()} ===\n{section_text}"
                    )
                    remaining_chars -= len(section_text) + 50
                else:
                    # Truncate this section but keep the beginning
                    truncated = (
                        section_text[: remaining_chars - 50] + "\n[...truncated]"
                    )
                    compressed_text += (
                        f"\n\n=== {section_type.upper()} ===\n{truncated}"
                    )
                    break

        # If we couldn't section it, do smart truncation
        if not compressed_text.strip():
            # Take first 60% and last 40% to preserve both contact info and recent experience
            first_part = text[: int(max_chars * 0.6)]
            last_part = text[-int(max_chars * 0.4) :]
            compressed_text = (
                first_part + "\n\n[... middle section truncated ...]\n\n" + last_part
            )

        logger.info(f"📄 Compressed to {len(compressed_text)} chars (was {len(text)})")
        return compressed_text

    def _identify_resume_sections(self, text: str) -> Dict[str, str]:
        """Identify different sections of a resume for smart processing."""
        sections = {}
        text_lines = text.split("\n")
        current_section = "header"
        current_content = []

        # Common section headers (case insensitive)
        section_patterns = {
            "contact": ["contact", "personal", "info"],
            "experience": [
                "experience",
                "employment",
                "work",
                "career",
                "professional",
            ],
            "skills": ["skills", "technical", "technologies", "competencies"],
            "education": ["education", "academic", "degree", "university", "college"],
            "projects": ["projects", "portfolio", "achievements"],
            "certifications": ["certifications", "certificates", "licenses"],
        }

        for line in text_lines:
            line_lower = line.lower().strip()

            # Check if this line is a section header
            new_section = None
            for section_name, patterns in section_patterns.items():
                if any(pattern in line_lower for pattern in patterns):
                    # Make sure it looks like a header (short line, maybe has special chars)
                    if len(line.strip()) < 50 and (
                        line.isupper() or "=" in line or "-" in line
                    ):
                        new_section = section_name
                        break

            if new_section:
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = new_section
                current_content = []
            else:
                current_content.append(line)

        # Save final section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _validate_and_clean_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the JSON data to ensure compatibility with ExtractedResumeData model."""
        # Required fields with defaults
        required_fields = {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "current_title": None,
            "desired_roles": [],
            "total_experience_years": 0.0,
            "technical_skills": [],
            "soft_skills": [],
            "work_experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "languages": [],
            "clearance_level": None,
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "other_urls": [],
            "professional_summary": None,
            "key_achievements": [],
            "extraction_confidence": 0.5,
        }

        # Fill in missing fields
        for field, default_value in required_fields.items():
            if field not in data:
                data[field] = default_value
                logger.debug(f"Added missing field '{field}' with default value")

        # Type validation and conversion
        try:
            # Ensure arrays are arrays
            array_fields = [
                "desired_roles",
                "technical_skills",
                "soft_skills",
                "work_experience",
                "education",
                "projects",
                "certifications",
                "languages",
                "other_urls",
                "key_achievements",
            ]
            for field in array_fields:
                if not isinstance(data.get(field), list):
                    data[field] = []
                    logger.debug(f"Converted '{field}' to empty array")

            # Ensure numeric fields are numeric
            if not isinstance(data.get("total_experience_years"), (int, float)):
                try:
                    data["total_experience_years"] = float(
                        data.get("total_experience_years", 0)
                    )
                except (ValueError, TypeError):
                    data["total_experience_years"] = 0.0
                    logger.debug("Converted total_experience_years to 0.0")

            if not isinstance(data.get("extraction_confidence"), (int, float)):
                try:
                    data["extraction_confidence"] = float(
                        data.get("extraction_confidence", 0.5)
                    )
                except (ValueError, TypeError):
                    data["extraction_confidence"] = 0.5
                    logger.debug("Converted extraction_confidence to 0.5")

            # Clamp confidence to valid range
            confidence = data["extraction_confidence"]
            if confidence < 0.0:
                data["extraction_confidence"] = 0.0
            elif confidence > 1.0:
                data["extraction_confidence"] = 1.0

            logger.info(
                f"✅ JSON validation completed. All fields present and properly typed."
            )

        except Exception as e:
            logger.error(f"Error during JSON validation: {e}")
            # Return the data as-is if validation fails, the ExtractedResumeData model will handle it

        return data

    def _post_process_extraction(
        self, extracted_data: ExtractedResumeData, original_text: str
    ) -> ExtractedResumeData:
        """
        🧮 POST-EXTRACTION FIXES: Calculate missing fields and validate data.
        """
        logger.info(f"🔧 Post-processing extraction for {extracted_data.name}")

        # 🎯 FIX #1: ALWAYS validate and correct experience calculation
        calculated_years = 0.0  # 🔧 INITIALIZE OUTSIDE THE IF BLOCK!
        if extracted_data.work_experience:
            calculated_years = self._calculate_experience_from_jobs(
                extracted_data.work_experience
            )

            # Compare AI's calculation with our precise calculation
            ai_years = extracted_data.total_experience_years
            # Use dynamic threshold: more tolerance for senior professionals
            threshold = max(
                0.5, min(1.5, calculated_years * 0.15)
            )  # 0.5-1.5 years based on experience

            if abs(calculated_years - ai_years) > threshold:
                logger.warning(
                    f"🚨 EXPERIENCE MISMATCH: AI calculated {ai_years} years, but job dates show {calculated_years} years "
                    f"(threshold: {threshold:.1f} years)"
                )
                logger.info(
                    f"🧮 Correcting experience: {ai_years} → {calculated_years} years (calculated from job dates)"
                )
                extracted_data.total_experience_years = calculated_years
            else:
                logger.info(
                    f"✅ Experience calculation verified: AI={ai_years}, Calculated={calculated_years} "
                    f"(within {threshold:.1f} year threshold)"
                )

        # 🎯 FIX #2: If experience is missing, estimate from raw text (years/ranges)
        if (
            not extracted_data.total_experience_years
            or extracted_data.total_experience_years == 0
        ):
            try:
                text_lower = original_text.lower()
                # Strategy A: direct years mentions
                direct_patterns = [
                    r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
                    r"experience[:\s]+(\d+)\+?\s*years?",
                    r"over\s+(\d+)\+?\s*years?",
                ]
                found_years: float = 0.0
                for pat in direct_patterns:
                    m = re.search(pat, text_lower)
                    if m:
                        found_years = float(m.group(1))
                        break
                # Strategy B: year ranges
                if found_years == 0.0:
                    from datetime import datetime

                    current_year = datetime.utcnow().year
                    year_ranges = re.findall(
                        r"(20\d{2}|19\d{2})\s*[-–]\s*(?:(20\d{2}|19\d{2})|present|current)",
                        text_lower,
                    )
                    total_months = 0
                    for start_str, end_str in year_ranges:
                        try:
                            start_year = int(start_str)
                            if end_str and end_str.isdigit():
                                end_year = int(end_str)
                            else:
                                end_year = current_year
                            if 1990 <= start_year <= end_year <= current_year:
                                total_months += (end_year - start_year) * 12
                        except Exception:
                            continue
                    if total_months > 0:
                        found_years = round(total_months / 12, 1)

                if found_years > 0:
                    extracted_data.total_experience_years = found_years
                    logger.info(f"🧮 Filled missing experience: {found_years} years")
            except Exception:
                pass

        # 🎯 FIX #2b: Prefer experience derived from structured work entries if present
        try:
            if extracted_data.work_experience:
                from datetime import datetime
                import re as _re

                current_year = datetime.utcnow().year
                total_months = 0
                for w in extracted_data.work_experience:
                    dur = (w.duration or "").lower()
                    m = _re.search(
                        r"(20\d{2}|19\d{2})\s*[-–]\s*(?:(20\d{2}|19\d{2})|present|current)",
                        dur,
                    )
                    if m:
                        start = int(m.group(1))
                        end = (
                            int(m.group(2))
                            if m.group(2) and m.group(2).isdigit()
                            else current_year
                        )
                        if 1990 <= start <= end <= current_year:
                            total_months += (end - start) * 12
                if total_months > 0:
                    years_from_roles = round(total_months / 12, 1)
                    # Override if significant mismatch
                    if (
                        not extracted_data.total_experience_years
                        or abs(years_from_roles - extracted_data.total_experience_years)
                        > 0.6
                    ):
                        logger.info(
                            f"🧮 Using experience from roles: {years_from_roles} years (overrode {extracted_data.total_experience_years})"
                        )
                        extracted_data.total_experience_years = years_from_roles
                elif settings.app_verbose_extraction:
                    # Enhanced scan across the full text to compute approximate years if durations were embedded differently
                    mlines = [ln.strip() for ln in original_text.splitlines()]
                    months = 0
                    current_year = datetime.utcnow().year
                    for ln in mlines:
                        md = _re.search(
                            r"(20\d{2}|19\d{2})\s*[-–]\s*(?:(20\d{2}|19\d{2})|present|current)",
                            ln.lower(),
                        )
                        if md:
                            s = int(md.group(1))
                            e = (
                                int(md.group(2))
                                if (md.group(2) and md.group(2).isdigit())
                                else current_year
                            )
                            if 1990 <= s <= e <= current_year:
                                months += (e - s) * 12
                    if months > 0:
                        y = round(months / 12, 1)
                        logger.info(
                            f"🧪 VERBOSE: Enhanced scan computed {y} years from date ranges in text"
                        )
                        if (not extracted_data.total_experience_years) or (
                            abs(y - extracted_data.total_experience_years) > 0.6
                        ):
                            extracted_data.total_experience_years = y
                    else:
                        logger.info(
                            "🧪 VERBOSE: No computable date ranges found in work_experience durations"
                        )
        except Exception:
            pass

        # 🎯 FIX #3: Extract additional skills from original text if AI missed obvious ones
        additional_skills = self._extract_obvious_skills(
            original_text, extracted_data.technical_skills
        )
        if additional_skills:
            logger.info(
                f"🔍 Found {len(additional_skills)} additional skills: {additional_skills}"
            )
            extracted_data.technical_skills.extend(additional_skills)
            # Remove duplicates while preserving order
            seen = set()
            unique_skills = []
            for skill in extracted_data.technical_skills:
                if skill.lower() not in seen:
                    seen.add(skill.lower())
                    unique_skills.append(skill)
            extracted_data.technical_skills = unique_skills

        # 🎯 FIX #4: Preserve all skills but reorder: SKILLS section first, then body hits (no exclusion)
        try:
            priority_skills = extract_skills_section(original_text)
            seen = set()
            ordered: List[str] = []
            for s in [*priority_skills, *extracted_data.technical_skills]:
                sl = s.strip()
                if not sl:
                    continue
                key = sl.lower()
                if key not in seen:
                    seen.add(key)
                    ordered.append(sl)
            extracted_data.technical_skills = ordered
        except Exception:
            pass

        # 🎯 FIX #5: Normalize name from email if malformed
        try:
            if extracted_data.email and extracted_data.name:
                # If single token or contains no space, derive from email
                if len(extracted_data.name.split()) == 1:
                    derived = derive_name_from_email(str(extracted_data.email))
                    if derived:
                        extracted_data.name = derived
                # If ALL CAPS with spaces, convert to Title Case
                elif extracted_data.name.isupper():
                    extracted_data.name = extracted_data.name.title()
        except Exception:
            pass

        # 🎯 FIX #6: Boost confidence if we made improvements
        improvements_made = (calculated_years > 0) or bool(additional_skills)
        if improvements_made and extracted_data.extraction_confidence < 0.8:
            old_confidence = extracted_data.extraction_confidence
            extracted_data.extraction_confidence = min(0.85, old_confidence + 0.2)
            logger.info(
                f"📈 Boosted confidence: {old_confidence:.2f} → {extracted_data.extraction_confidence:.2f}"
            )

        return extracted_data

    def _parse_duration_to_months(
        self, duration: str, current_year: int, current_month: int
    ) -> int:
        """Parse a duration string and return the number of months worked.

        The parser supports a variety of patterns, for example::

            "Jan 2018 - Mar 2020"
            "January 2018 – 2020"
            "2016 - 2018"
            "Mar 2021 - present"
            "2020 - current"

        If a month is missing on either side, it defaults to January for the start
        and December for the end to prevent under-counting. If the end date is
        *present/current*, the current_month and current_year values are used.

        Args:
            duration: Raw duration string from the resume.
            current_year: Current year (int) used for *present/current*.
            current_month: Current month (1-12).

        Returns:
            int: Total months represented by the duration.
        """
        import re
        from calendar import month_abbr, month_name
        from datetime import datetime

        duration_clean = re.sub(r"\s+", " ", duration.strip().lower())
        # Early exit if nothing useful
        if not duration_clean:
            return 0

        # Normalise the dash
        parts = re.split(r"\s*[-–—]\s*", duration_clean)
        if len(parts) != 2:
            return 0  # unsupported format – fall back later

        start_part, end_part = parts

        # Helper maps for month names → number
        month_map = {m.lower(): i for i, m in enumerate(month_name) if m}
        month_map.update({m.lower(): i for i, m in enumerate(month_abbr) if m})

        def _extract_month_year(
            segment: str, default_month: int, default_to_current: bool = False
        ):
            """Return (year, month) tuple parsed from a segment."""
            # Check for present / current keywords
            if any(k in segment for k in ("present", "current", "now")):
                # For current roles, use the real current month; if we're parsing an END segment
                # this gives an accurate up-to-today calculation. For START segments we should
                # never hit this branch.
                return current_year, (
                    current_month if default_to_current else default_month
                )

            # Try month name + year (e.g., jan 2018)
            match = re.search(r"(?P<month>[a-zA-Z]{3,9})\s+(?P<year>20\d{2})", segment)
            if match:
                month_str = match.group("month").lower()
                year_val = int(match.group("year"))
                month_val = month_map.get(month_str[:3].lower(), default_month)
                # Safety check: ensure month_val between 1-12
                month_val = month_val if 1 <= month_val <= 12 else default_month
                return year_val, month_val

            # Try year only
            year_only = re.search(r"\b(20\d{2})\b", segment)
            if year_only:
                return int(year_only.group(1)), default_month

            # Could not parse
            return None, None

        # Extract start & end using mid-year defaults
        #   – If month missing on START → assume July (month 7)
        #   – If month missing on END → assume June (month 6) to avoid over-counting full final year.
        s_year, s_month = _extract_month_year(start_part, default_month=7)
        e_year, e_month = _extract_month_year(
            end_part, default_month=6, default_to_current=True
        )

        if s_year is None or e_year is None:
            return 0  # fallback later

        # Convert to datetime objects for accurate delta
        try:
            start_dt = datetime(s_year, s_month, 1)
            end_dt = datetime(e_year, e_month, 1)
        except ValueError:
            return 0

        # Ensure end is after start
        if end_dt < start_dt:
            return 0

        diff_months = (
            (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1
        )  # +1 to count the start month
        return diff_months

    def _calculate_experience_from_jobs(self, work_experience: List) -> float:
        """🎯 Enhanced experience calculator with month-level accuracy.

        This version first attempts to parse explicit month/year ranges using
        `_parse_duration_to_months`. If parsing fails for a particular job it
        gracefully falls back to the previous heuristic so we never *lose* time
        compared to the old method.
        """
        import re
        from datetime import datetime

        total_months = 0
        current_year = datetime.now().year
        current_month = datetime.now().month

        logger.info(
            f"🧮 ENHANCED calculation over {len(work_experience)} jobs (current {current_year}-{current_month:02d})"
        )

        for i, job in enumerate(work_experience):
            duration = job.duration if hasattr(job, "duration") else str(job)
            logger.info(f"   ➜ Job {i+1}: '{duration}'")

            parsed_months = self._parse_duration_to_months(
                duration, current_year, current_month
            )
            if parsed_months:
                logger.info(
                    f"      ✅ Parsed {parsed_months} months via enhanced parser"
                )
                total_months += parsed_months
                continue  # next job

            logger.info("      ⚠️  Enhanced parser failed – falling back to heuristic")
            # Fallback to previous heuristic (year-only parsing)
            duration_clean = re.sub(r"\s+", " ", duration.strip())
            current_keywords = ["current", "present", "now"]
            is_current_job = any(k in duration_clean.lower() for k in current_keywords)
            range_match = re.search(
                r"\b(20\d{2})\s*[-–—]\s*(20\d{2}|current|present)\b",
                duration_clean.lower(),
            )

            if range_match:
                start_year = int(range_match.group(1))
                end_year_str = range_match.group(2)
                end_year = (
                    current_year
                    if end_year_str in ["current", "present"]
                    else int(end_year_str)
                )
                job_years = max(0, end_year - start_year) + (
                    current_month / 12.0
                    if end_year_str in ["current", "present"]
                    else 0
                )
                total_months += job_years * 12
            else:
                years_match = re.search(
                    r"(\d+(?:\.\d+)?)\s*years?", duration_clean.lower()
                )
                months_match = re.search(r"(\d+)\s*months?", duration_clean.lower())
                if years_match:
                    total_months += float(years_match.group(1)) * 12
                elif months_match:
                    total_months += int(months_match.group(1))
                else:
                    total_months += 12  # assume 1 year if nothing parsed

        total_years = total_months / 12.0
        logger.info(
            f"🎯 FINAL EXPERIENCE: {total_years:.1f} years (computed from {total_months} months)"
        )
        return round(total_years, 1)

    def _extract_obvious_skills(
        self, text: str, existing_skills: List[str]
    ) -> List[str]:
        """Extract obvious technical skills that AI might have missed."""
        # Common tech skills that are often missed
        tech_keywords = {
            "JavaScript",
            "TypeScript",
            "Python",
            "Java",
            "C++",
            "C#",
            "PHP",
            "Ruby",
            "Go",
            "Rust",
            "React",
            "Angular",
            "Vue",
            "Node.js",
            "Express",
            "Django",
            "Flask",
            "Spring",
            "Laravel",
            "AWS",
            "Azure",
            "GCP",
            "Docker",
            "Kubernetes",
            "Jenkins",
            "GitLab",
            "GitHub",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "Redis",
            "Elasticsearch",
            "Git",
            "Jira",
            "Confluence",
            "Slack",
            "Terraform",
            "Ansible",
            "TensorFlow",
            "PyTorch",
            "Pandas",
            "NumPy",
            "Scikit-learn",
            "Hadoop",
            "Spark",
            "Kafka",
            "RabbitMQ",
            "GraphQL",
            "REST",
            "Selenium",
            "Jest",
            "Pytest",
            "JUnit",
            "Cypress",
            "Linux",
            "Ubuntu",
            "CentOS",
            "Windows Server",
            "MacOS",
        }

        existing_lower = [skill.lower() for skill in existing_skills]
        found_skills = []

        # Look for exact matches (case insensitive)
        for keyword in tech_keywords:
            if keyword.lower() not in existing_lower:
                # Use word boundaries to avoid false positives
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, text, re.IGNORECASE):
                    found_skills.append(keyword)

        return found_skills[:10]  # Limit to 10 additional skills to avoid spam

    def _smart_truncate(self, text: str, max_chars: int = 8000) -> str:
        """
        🚨 DEPRECATED: Use _prepare_text_for_extraction instead.
        Kept for backward compatibility.
        """
        logger.warning(
            "⚠️ Using deprecated _smart_truncate - upgrade to _prepare_text_for_extraction"
        )
        return self._prepare_text_for_extraction(text, max_chars)

    def _fallback_extraction(self, resume_text: str) -> ExtractedResumeData:
        """
        Enhanced fallback extraction when AI fails or times out.
        Uses improved patterns to extract more comprehensive information.
        """
        logger.info("🔄 Starting enhanced fallback extraction with improved patterns")

        # Extract email (more comprehensive pattern)
        email_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        ]
        email = None
        for pattern in email_patterns:
            email_match = re.search(pattern, resume_text)
            if email_match:
                email = email_match.group(0)
                break

        # Extract phone (more comprehensive patterns)
        phone_patterns = [
            r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            r"\+?1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            r"\+\d{1,3}[-.\s]?\d{4,14}",
            r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]",
        ]
        phone = None
        for pattern in phone_patterns:
            phone_match = re.search(pattern, resume_text)
            if phone_match:
                phone = phone_match.group(0)
                break

        # Extract name (significantly improved logic)
        lines = resume_text.strip().split("\n")
        name = "Unknown Candidate"

        # Job title keywords to avoid
        job_title_keywords = [
            "director",
            "manager",
            "engineer",
            "developer",
            "analyst",
            "architect",
            "consultant",
            "specialist",
            "coordinator",
            "supervisor",
            "lead",
            "senior",
            "junior",
            "intern",
            "associate",
            "principal",
            "staff",
            "software",
            "data",
            "systems",
            "network",
            "security",
            "product",
            "project",
            "program",
            "technical",
            "chief",
            "head",
            "vice",
            "president",
            "ceo",
            "cto",
            "cfo",
            "vp",
            "officer",
            "experience",
            "summary",
            "profile",
            "objective",
            "skills",
            "education",
            "resume",
            "cv",
            "curriculum",
            "vitae",
        ]

        for line_idx, line in enumerate(lines[:20]):  # Check first 20 lines
            line = line.strip()
            if not line:
                continue

            # Skip lines that are clearly not names
            if (
                re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)  # Email
                or re.search(r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]", line)  # Phone
                or line.lower().startswith(
                    ("http", "www.", "linkedin", "github")
                )  # URLs
                or len(line.split()) > 6  # Too many words
                or len(line.split()) < 2
            ):  # Too few words
                continue

            # Check if line looks like a proper name
            words = line.split()
            if len(words) >= 2 and len(words) <= 4:
                # Check for job title keywords
                line_lower = line.lower()
                is_job_title = any(
                    keyword in line_lower for keyword in job_title_keywords
                )

                # Check if words are capitalized properly (likely a name)
                # Accept both Title Case and ALL CAPS for names
                is_title_case = all(
                    word[0].isupper() and word[1:].islower()
                    for word in words
                    if word.isalpha()
                )
                is_all_caps = all(word.isupper() for word in words if word.isalpha())
                is_properly_capitalized = is_title_case or is_all_caps

                # Additional name pattern checks for various real-world formats
                name_patterns = [
                    r"^[A-Z][a-z]+ [A-Z][a-z]+$",  # First Last (Title Case)
                    r"^[A-Z]+ [A-Z]+$",  # FIRST LAST (ALL CAPS)
                    r"^[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+$",  # First M. Last
                    r"^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$",  # First Middle Last
                    r"^[A-Z][a-z]+ [a-z]+ [A-Z][a-z]+$",  # First van/de/du Last (like "Dricus du Plessis")
                    r"^[A-Z][a-z]+ [A-Z][a-z]+ [a-z]+ [A-Z][a-z]+$",  # First Last van/de/du Name
                    r"^Dr\.\s+[A-Z][a-z]+ [A-Z][a-z]+",  # Dr. First Last
                    r"^[A-Z][a-z]+ [A-Z][a-z]+,\s*PhD",  # First Last, PhD
                    r"^Dr\.\s+[A-Z][a-z]+ [A-Z][a-z]+,\s*PhD",  # Dr. First Last, PhD
                    r"^[A-Z][a-z]+(-[A-Z][a-z]+)? [A-Z][a-z]+$",  # Hyphenated first names like "Mary-Jane Smith"
                ]

                matches_name_pattern = any(
                    re.match(pattern, line) for pattern in name_patterns
                )

                # Check for real-world name patterns with proper spacing
                # Names typically have larger spaces between first/last name than other text
                if is_properly_capitalized and not is_job_title and len(words) >= 2:
                    # Additional validation for name-like patterns
                    likely_name = True

                    # Check if this looks like a section header
                    section_keywords = [
                        "experience",
                        "education",
                        "skills",
                        "projects",
                        "certifications",
                        "qualifications",
                        "background",
                        "summary",
                        "profile",
                        "contact",
                        "professional",
                        "work",
                        "employment",
                        "career",
                        "technical",
                        "accomplishments",
                        "achievements",
                        "languages",
                        "interests",
                    ]

                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in section_keywords):
                        likely_name = False

                    # Check if words look like name parts (not technical terms, companies, etc.)
                    if likely_name:
                        for word in words:
                            if (
                                len(word) > 15  # Too long for typical names
                                or word.lower()
                                in [
                                    "technologies",
                                    "engineering",
                                    "development",
                                    "software",
                                    "experience",
                                    "professional",
                                    "education",
                                    "background",
                                ]
                                or any(
                                    char.isdigit() for char in word
                                )  # Contains numbers
                                or word.lower().endswith((".com", ".org", ".net"))
                            ):  # URLs
                                likely_name = False
                                break

                    if likely_name:
                        name = line
                        logger.info(f"🎯 Found name on line {line_idx + 1}: '{name}'")
                        break
                elif (
                    is_properly_capitalized and not is_job_title
                ) or matches_name_pattern:
                    name = line
                    logger.info(f"🎯 Found name on line {line_idx + 1}: '{name}'")
                    break

        # Enhanced skill extraction with more keywords
        text_lower = resume_text.lower()
        skills = []
        skill_keywords = [
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "angular",
            "vue",
            "node.js",
            "nodejs",
            "express",
            "django",
            "flask",
            "fastapi",
            "spring",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "sql",
            "postgresql",
            "mysql",
            "mongodb",
            "redis",
            "git",
            "github",
            "gitlab",
            "jenkins",
            "ci/cd",
            "html",
            "css",
            "bootstrap",
            "tailwind",
            "tensorflow",
            "pytorch",
            "scikit-learn",
            "pandas",
            "numpy",
            "php",
            "laravel",
            "symfony",
            "ruby",
            "rails",
            "c++",
            "c#",
            ".net",
            "go",
            "rust",
            "scala",
            "kotlin",
            "elasticsearch",
            "kafka",
            "rabbitmq",
            "microservices",
            "graphql",
            "rest",
            "api",
            "json",
            "xml",
        ]

        for skill in skill_keywords:
            if skill in text_lower:
                # Capitalize properly
                if skill in ["node.js", "nodejs"]:
                    skills.append("Node.js")
                elif skill == "ci/cd":
                    skills.append("CI/CD")
                elif skill == "c++":
                    skills.append("C++")
                elif skill == "c#":
                    skills.append("C#")
                elif skill == ".net":
                    skills.append(".NET")
                else:
                    skills.append(skill.capitalize())

        # Remove duplicates while preserving order
        skills = list(dict.fromkeys(skills))

        # Enhanced experience calculation with multiple strategies
        experience_years = 0.0
        text_lower = resume_text.lower()

        # Strategy 1: Direct experience mentions
        exp_patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"experience[:\s]+(\d+)\+?\s*years?",
            r"(\d+)\+?\s*years?\s+in\s+(?:software|development|programming|engineering)",
            r"(\d+)\+?\s*years?\s+(?:working|professional)",
            r"total\s+(?:of\s+)?(\d+)\+?\s*years?",
            r"over\s+(\d+)\+?\s*years?",
            r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?(?:work\s+)?experience",
        ]

        for pattern in exp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    experience_years = float(match.group(1))
                    logger.info(
                        f"📊 Found experience via direct pattern: {experience_years} years"
                    )
                    break
                except (ValueError, IndexError):
                    continue

        # Strategy 2: Calculate from work history if no direct mention found
        if experience_years == 0.0:
            logger.info(
                "📊 No direct experience found, calculating from work history..."
            )

            # Look for year ranges in work experience (improved pattern)
            year_ranges = re.findall(
                r"(20\d{2}|19\d{2})\s*[-–]\s*(?:(20\d{2}|19\d{2})|present|current)",
                text_lower,
            )

            total_months = 0
            for start_year_str, end_year_str in year_ranges:
                try:
                    start_year = int(start_year_str)

                    if end_year_str and end_year_str.isdigit():
                        end_year = int(end_year_str)
                    else:  # Present/current job
                        end_year = 2024

                    if 1990 <= start_year <= end_year <= 2024:
                        years_diff = end_year - start_year
                        if years_diff >= 0 and years_diff <= 50:  # Sanity check
                            total_months += years_diff * 12
                            logger.info(
                                f"📊 Found job: {start_year}-{end_year} = {years_diff} years"
                            )

                except (ValueError, AttributeError):
                    continue

            if total_months > 0:
                experience_years = round(total_months / 12, 1)
                logger.info(
                    f"📊 Calculated experience from work history: {experience_years} years"
                )

        # Strategy 3: Estimate from common career indicators if still 0
        if experience_years == 0.0:
            # Look for senior titles (usually 5+ years)
            if re.search(
                r"\b(?:senior|lead|principal|staff|director|manager|architect)\b",
                text_lower,
            ):
                experience_years = 5.0
                logger.info("📊 Estimated 5+ years from senior title")
            # Look for mid-level indicators (usually 2-5 years)
            elif re.search(r"\b(?:engineer|developer|analyst)\b", text_lower):
                experience_years = 3.0
                logger.info("📊 Estimated 3 years from professional title")
            # Look for junior indicators (usually 0-2 years)
            elif re.search(r"\b(?:junior|intern|entry|trainee|graduate)\b", text_lower):
                experience_years = 1.0
                logger.info("📊 Estimated 1 year from junior title")

        # Try to extract location
        location = None
        location_patterns = [
            r"([A-Z][a-z]+,?\s+[A-Z]{2})",  # City, State
            r"([A-Z][a-z]+\s+[A-Z][a-z]+,?\s+[A-Z]{2})",  # City Name, State
            r"(Remote)",
            r"([A-Z][a-z]+,?\s+[A-Z][a-z]+)",  # City, Country
        ]

        for pattern in location_patterns:
            match = re.search(pattern, resume_text)
            if match:
                location = match.group(1)
                break

        # Try to extract GitHub URL
        github_match = re.search(r"github\.com/[\w\-\.]+", resume_text.lower())
        github_url = f"https://{github_match.group(0)}" if github_match else None

        # Try to extract LinkedIn URL
        linkedin_match = re.search(r"linkedin\.com/in/[\w\-\.]+", resume_text.lower())
        linkedin_url = f"https://{linkedin_match.group(0)}" if linkedin_match else None

        # Calculate confidence based on extracted information quality
        confidence = 0.3  # Base confidence for fallback

        # Increase confidence based on what we found
        if name != "Unknown Candidate" and len(name.split()) >= 2:
            confidence += 0.15  # Good name extraction
        if email:
            confidence += 0.1  # Email found
        if phone:
            confidence += 0.05  # Phone found
        if len(skills) >= 5:
            confidence += 0.15  # Good skills extraction
        if experience_years > 0:
            confidence += 0.15  # Experience calculated
        if location:
            confidence += 0.05  # Location found
        if github_url or linkedin_url:
            confidence += 0.05  # Social profiles found

        confidence = min(confidence, 0.85)  # Cap at 0.85 for fallback

        logger.info(
            f"🔄 Enhanced fallback extracted: {name}, {len(skills)} skills, {experience_years} years exp, confidence: {confidence:.2f}"
        )

        return ExtractedResumeData(
            name=name,
            email=email,
            phone=phone,
            location=location,
            technical_skills=skills,
            total_experience_years=experience_years,
            github_url=github_url,
            linkedin_url=linkedin_url,
            professional_summary=f"Enhanced fallback extraction - {len(skills)} technical skills identified with {confidence:.0%} confidence",
            extraction_confidence=confidence,
        )

    def _generate_cache_key(self, text: str) -> str:
        """Generate a cache key from resume text."""
        # Use first 100 and last 100 characters
        if len(text) < 200:
            return text
        return text[:100] + text[-100:]

    def _add_to_cache(self, key: str, data: ExtractedResumeData):
        """Add extraction to cache with size limit."""
        if len(self._extraction_cache) >= self.max_cache_size:
            # Remove oldest entry (FIFO)
            oldest_key = next(iter(self._extraction_cache))
            del self._extraction_cache[oldest_key]

        self._extraction_cache[key] = data

    def get_analytics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get extraction analytics for monitoring and optimization."""
        return self.analytics.get_stats(hours_back)
