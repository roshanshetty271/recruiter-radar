"""
Enhanced AI Extraction Service with Performance Optimizations

Key improvements:
- orjson for 2-3x faster JSON parsing
- tenacity for intelligent retry logic
- json-repair for handling malformed AI responses
- Shorter, optimized prompts for faster responses
- Progressive timeout strategy
- Better error classification and fallbacks
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import re
from collections import defaultdict, Counter
import time  # Added for time.time() in extract_structured_profile_data

# Performance optimizations
import orjson  # 2-3x faster JSON parsing
import json_repair  # Fix malformed JSON
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.services.llm_service import LLMService
from app.models.extraction_models import ExtractedResumeData
from app.core.config import settings

logger = structlog.get_logger(__name__)


class EnhancedExtractionAnalytics:
    """Enhanced analytics tracking with more detailed metrics."""

    def __init__(self):
        self.extractions: List[Dict[str, Any]] = []
        self.max_stored_extractions = 1000
        self.error_counts = defaultdict(int)
        self.retry_counts = defaultdict(int)

    def record_extraction(
        self,
        success: bool,
        extraction_time: float,
        extracted_data: Optional[ExtractedResumeData] = None,
        cache_hit: bool = False,
        retry_count: int = 0,
        error_type: Optional[str] = None,
        prompt_length: int = 0,
        response_length: int = 0,
    ):
        """Record extraction with enhanced metrics."""
        record = {
            "timestamp": datetime.utcnow(),
            "success": success,
            "extraction_time": extraction_time,
            "cache_hit": cache_hit,
            "retry_count": retry_count,
            "error_type": error_type,
            "prompt_length": prompt_length,
            "response_length": response_length,
            "skills_count": (
                len(extracted_data.technical_skills) + len(extracted_data.soft_skills)
                if extracted_data
                else 0
            ),
            "jobs_count": len(extracted_data.work_experience) if extracted_data else 0,
            "confidence": (
                extracted_data.extraction_confidence if extracted_data else 0.0
            ),
        }

        self.extractions.append(record)

        if error_type:
            self.error_counts[error_type] += 1
        if retry_count > 0:
            self.retry_counts[retry_count] += 1

        # Keep only recent extractions
        if len(self.extractions) > self.max_stored_extractions:
            self.extractions = self.extractions[-self.max_stored_extractions :]

    def get_enhanced_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get enhanced extraction analytics."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        recent_extractions = [
            e for e in self.extractions if e["timestamp"] >= cutoff_time
        ]

        if not recent_extractions:
            return {"total_extractions": 0, "message": "No extractions in time window"}

        successful = [e for e in recent_extractions if e["success"]]

        # Calculate performance metrics
        avg_time = (
            sum(e["extraction_time"] for e in successful) / len(successful)
            if successful
            else 0
        )
        avg_confidence = (
            sum(e["confidence"] for e in successful) / len(successful)
            if successful
            else 0
        )

        # Error analysis
        recent_errors = [e["error_type"] for e in recent_extractions if e["error_type"]]
        error_breakdown = Counter(recent_errors)

        # Retry analysis
        retry_analysis = Counter(e["retry_count"] for e in recent_extractions)

        return {
            "time_window_hours": hours_back,
            "total_extractions": len(recent_extractions),
            "successful_extractions": len(successful),
            "success_rate": (
                len(successful) / len(recent_extractions) if recent_extractions else 0
            ),
            "performance_metrics": {
                "avg_extraction_time_seconds": round(avg_time, 2),
                "avg_confidence_score": round(avg_confidence, 3),
                "avg_skills_extracted": (
                    sum(e["skills_count"] for e in successful) / len(successful)
                    if successful
                    else 0
                ),
                "avg_jobs_extracted": (
                    sum(e["jobs_count"] for e in successful) / len(successful)
                    if successful
                    else 0
                ),
            },
            "error_analysis": dict(error_breakdown),
            "retry_analysis": dict(retry_analysis),
            "optimization_stats": {
                "cache_hit_rate": (
                    len([e for e in recent_extractions if e["cache_hit"]])
                    / len(recent_extractions)
                    if recent_extractions
                    else 0
                ),
                "avg_prompt_length": (
                    sum(e["prompt_length"] for e in recent_extractions)
                    / len(recent_extractions)
                    if recent_extractions
                    else 0
                ),
                "avg_response_length": (
                    sum(e["response_length"] for e in recent_extractions)
                    / len(recent_extractions)
                    if recent_extractions
                    else 0
                ),
            },
        }


class EnhancedAIExtractionService:
    """Enhanced AI extraction service with significant performance improvements."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.analytics = EnhancedExtractionAnalytics()

        # Optimized prompts for faster responses
        self.fast_prompt_template = """Extract key info from this resume in JSON format:

{resume_text}

Return JSON with: name, email, technical_skills (array), total_experience_years, location, current_title, professional_summary, extraction_confidence (0.0-1.0).

Focus on accuracy and speed. Extract ALL technical skills mentioned."""

        self.comprehensive_prompt_template = """Extract comprehensive information from this resume:

{resume_text}

Return detailed JSON with all fields from ExtractedResumeData model. Calculate total_experience_years by adding up ALL job durations. Extract EVERY technical skill mentioned."""

        logger.info("EnhancedAIExtractionService initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def extract_resume_data_enhanced(
        self, resume_text: str, timeout_seconds: int = 15, use_fast_mode: bool = False
    ) -> Optional[ExtractedResumeData]:
        """
        Enhanced AI extraction with progressive timeouts and better error handling.

        Args:
            resume_text: Raw resume text
            timeout_seconds: Maximum time for extraction
            use_fast_mode: Use faster, simpler prompt for quick results
        """
        start_time = datetime.utcnow()
        retry_count = 0

        try:
            # Choose prompt based on mode
            if use_fast_mode or len(resume_text) > 10000:
                prompt = self.fast_prompt_template.format(
                    resume_text=resume_text[:8000]
                )
                logger.info(
                    "Using fast extraction mode",
                    text_length=len(resume_text),
                    timeout=timeout_seconds,
                )
            else:
                prompt = self.comprehensive_prompt_template.format(
                    resume_text=resume_text
                )
                logger.info(
                    "Using comprehensive extraction mode",
                    text_length=len(resume_text),
                    timeout=timeout_seconds,
                )

            # Progressive timeout strategy
            extraction_task = self._call_llm_enhanced(prompt, use_fast_mode)
            result = await asyncio.wait_for(extraction_task, timeout=timeout_seconds)

            extraction_time = (datetime.utcnow() - start_time).total_seconds()

            if result:
                # Record successful extraction
                self.analytics.record_extraction(
                    success=True,
                    extraction_time=extraction_time,
                    extracted_data=result,
                    prompt_length=len(prompt),
                    response_length=0,  # Will be set in _call_llm_enhanced
                )

                logger.info(
                    "Enhanced AI extraction successful",
                    extraction_time=extraction_time,
                    confidence=result.extraction_confidence,
                    skills_count=len(result.technical_skills),
                )

                return result
            else:
                raise Exception("LLM returned no extraction data")

        except asyncio.TimeoutError:
            extraction_time = (datetime.utcnow() - start_time).total_seconds()
            logger.warning(
                "AI extraction timeout, trying fallback",
                timeout_seconds=timeout_seconds,
                extraction_time=extraction_time,
            )

            # Record timeout
            self.analytics.record_extraction(
                success=False,
                extraction_time=extraction_time,
                error_type="timeout",
                prompt_length=len(prompt) if "prompt" in locals() else 0,
            )

            # Try super fast extraction as fallback
            if not use_fast_mode:
                return await self.extract_resume_data_enhanced(
                    resume_text, timeout_seconds=8, use_fast_mode=True
                )
            else:
                return self._enhanced_fallback_extraction(resume_text)

        except Exception as e:
            extraction_time = (datetime.utcnow() - start_time).total_seconds()
            error_type = type(e).__name__

            logger.error(
                "Enhanced AI extraction failed",
                error=str(e),
                error_type=error_type,
                extraction_time=extraction_time,
            )

            # Record error
            self.analytics.record_extraction(
                success=False,
                extraction_time=extraction_time,
                error_type=error_type,
                prompt_length=len(prompt) if "prompt" in locals() else 0,
            )

            return self._enhanced_fallback_extraction(resume_text)

    async def _call_llm_enhanced(
        self, prompt: str, fast_mode: bool = False
    ) -> Optional[ExtractedResumeData]:
        """Enhanced LLM call with orjson and better error handling."""
        try:
            # Optimized parameters for speed
            max_tokens = 1000 if fast_mode else 2000
            temperature = 0.1

            logger.info(
                "Calling LLM with enhanced settings",
                model=settings.chat_model_name,
                fast_mode=fast_mode,
                max_tokens=max_tokens,
                prompt_length=len(prompt),
            )

            response = await self.llm_service.client.chat.completions.create(
                model=settings.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume parser. Extract information accurately and return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                logger.error("Empty response from LLM")
                return None

            response_length = len(content)
            logger.info(
                "LLM response received",
                response_length=response_length,
                truncated=len(content) >= max_tokens * 0.95,
            )

            # Parse with orjson (2-3x faster than standard json)
            try:
                data = orjson.loads(content)
            except orjson.JSONDecodeError as e:
                logger.warning(
                    "Invalid JSON from LLM, attempting repair", json_error=str(e)
                )
                try:
                    # Attempt to repair malformed JSON
                    repaired_content = json_repair.repair_json(content)
                    data = orjson.loads(repaired_content)
                    logger.info("Successfully repaired malformed JSON")
                except Exception as repair_error:
                    logger.error(
                        "JSON repair failed",
                        repair_error=str(repair_error),
                        original_error=str(e),
                    )
                    return None

            # Create ExtractedResumeData with validation
            try:
                extracted_data = ExtractedResumeData(**data)

                # Validate and enhance the data
                if not extracted_data.name or len(extracted_data.name.strip()) < 2:
                    logger.warning(
                        "Low quality name extraction", name=extracted_data.name
                    )
                    extracted_data.extraction_confidence *= 0.8

                if len(extracted_data.technical_skills) < 3:
                    logger.warning(
                        "Few technical skills extracted",
                        skills_count=len(extracted_data.technical_skills),
                    )
                    extracted_data.extraction_confidence *= 0.9

                # Update analytics with response length
                if (
                    hasattr(self.analytics, "extractions")
                    and self.analytics.extractions
                ):
                    self.analytics.extractions[-1]["response_length"] = response_length

                return extracted_data

            except Exception as validation_error:
                logger.error(
                    "Failed to create ExtractedResumeData",
                    validation_error=str(validation_error),
                    data_keys=(
                        list(data.keys()) if isinstance(data, dict) else "not_dict"
                    ),
                )
                return None

        except Exception as e:
            logger.error("Enhanced LLM call failed", error=str(e))
            return None

    def _enhanced_fallback_extraction(self, text: str) -> Optional[ExtractedResumeData]:
        """Enhanced fallback extraction with better regex patterns."""
        logger.info("Using enhanced fallback extraction", text_length=len(text))

        try:
            # Enhanced regex patterns
            name_patterns = [
                r"^([A-Z][a-z]+ [A-Z][a-z]+)",  # First Last
                r"^([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)",  # First M. Last
                r"Name:\s*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:\n|\r)",  # Name at start of line
            ]

            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            phone_patterns = [
                r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            ]

            # Enhanced skill extraction with broader patterns
            tech_skills_patterns = [
                r"\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|PHP|Ruby|Swift|Kotlin)\b",
                r"\b(?:React|Vue|Angular|Node\.js|Express|Django|Flask|Spring|Laravel)\b",
                r"\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitLab|GitHub)\b",
                r"\b(?:MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|Oracle|SQLite)\b",
                r"\b(?:HTML|CSS|SASS|LESS|Bootstrap|Tailwind|Material-UI)\b",
                r"\b(?:Git|SVN|Mercurial|Perforce|Bazaar)\b",
                r"\b(?:Linux|Unix|Windows|macOS|Ubuntu|CentOS|Debian)\b",
                r"\b(?:TensorFlow|PyTorch|scikit-learn|Pandas|NumPy|Matplotlib)\b",
                r"\b(?:REST|GraphQL|gRPC|SOAP|JSON|XML|YAML)\b",
                r"\b(?:Agile|Scrum|Kanban|DevOps|CI/CD|TDD|BDD)\b",
            ]

            # Extract information
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    break

            email_match = re.search(email_pattern, text, re.IGNORECASE)
            email = email_match.group(0) if email_match else None

            phone = None
            for pattern in phone_patterns:
                match = re.search(pattern, text)
                if match:
                    phone = match.group(0)
                    break

            # Extract technical skills
            skills = set()
            for pattern in tech_skills_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        skills.update(match)
                    else:
                        skills.add(match)

            # Convert to proper case
            skills = [skill.strip() for skill in skills if skill.strip()]
            skills = list(set(skills))  # Remove duplicates

            # Extract experience (simplified)
            experience_patterns = [
                r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
                r"experience:\s*(\d+)\+?\s*years?",
                r"(\d+)\+?\s*years?\s*in\s*(?:software|development|programming)",
            ]

            experience_years = 0.0
            for pattern in experience_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    experience_years = float(match.group(1))
                    break

            # Enhanced location extraction
            location_patterns = [
                r"(?:Location|Address):\s*([^,\n]+(?:,\s*[A-Z]{2})?)",
                r"([A-Z][a-z]+,\s*[A-Z]{2}(?:\s+\d{5})?)",  # City, ST or City, ST ZIP
                r"([A-Z][a-z]+\s*[A-Z][a-z]*,\s*[A-Z][a-z]+)",  # City, State
                r"Remote|Work from home|Distributed",
            ]

            location = None
            for pattern in location_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    location = match.group(1 if match.groups() else 0).strip()
                    break

            # URL extraction
            github_match = re.search(
                r"github\.com/([A-Za-z0-9_-]+)", text, re.IGNORECASE
            )
            github_url = (
                f"https://github.com/{github_match.group(1)}" if github_match else None
            )

            linkedin_match = re.search(
                r"linkedin\.com/in/([A-Za-z0-9_-]+)", text, re.IGNORECASE
            )
            linkedin_url = (
                f"https://linkedin.com/in/{linkedin_match.group(1)}"
                if linkedin_match
                else None
            )

            confidence = 0.6  # Base confidence for fallback

            # Adjust confidence based on extracted data quality
            if name and len(name.split()) >= 2:
                confidence += 0.1
            if email:
                confidence += 0.1
            if len(skills) >= 5:
                confidence += 0.1
            if experience_years > 0:
                confidence += 0.1

            logger.info(
                "Enhanced fallback extraction completed",
                name=name,
                email=email,
                skills_count=len(skills),
                experience_years=experience_years,
                confidence=confidence,
            )

            return ExtractedResumeData(
                name=name or "Unknown",
                email=email,
                phone=phone,
                location=location,
                technical_skills=skills,
                total_experience_years=experience_years,
                github_url=github_url,
                linkedin_url=linkedin_url,
                professional_summary="Enhanced fallback extraction - partial data available",
                extraction_confidence=min(confidence, 1.0),
            )

        except Exception as e:
            logger.error("Enhanced fallback extraction failed", error=str(e))
            return None

    def get_enhanced_analytics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get enhanced extraction analytics."""
        return self.analytics.get_enhanced_stats(hours_back)

    async def batch_extract_resumes(
        self, resume_texts: List[str], fast_mode: bool = True
    ) -> List[Optional[ExtractedResumeData]]:
        """Extract multiple resumes efficiently."""
        logger.info(
            "Starting batch extraction",
            batch_size=len(resume_texts),
            fast_mode=fast_mode,
        )

        # Process with limited concurrency to avoid rate limits
        semaphore = asyncio.Semaphore(3)

        async def extract_with_semaphore(text: str) -> Optional[ExtractedResumeData]:
            async with semaphore:
                return await self.extract_resume_data_enhanced(
                    text,
                    timeout_seconds=10 if fast_mode else 15,
                    use_fast_mode=fast_mode,
                )

        tasks = [extract_with_semaphore(text) for text in resume_texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, ExtractedResumeData))
        failed = len(results) - successful

        logger.info(
            "Batch extraction completed",
            total=len(resume_texts),
            successful=successful,
            failed=failed,
            success_rate=successful / len(resume_texts) if resume_texts else 0,
        )

        # Return results, converting exceptions to None
        return [r if isinstance(r, ExtractedResumeData) else None for r in results]

    async def extract_structured_profile_data(
        self,
        candidate_id: str,
        raw_resume_text: str,
        candidate_name: str,
        fast_path_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured profile data optimized for the View Profile modal.

        Args:
            candidate_id: Unique candidate identifier
            raw_resume_text: Raw resume text to parse
            candidate_name: Candidate's name for context
            fast_path_data: Optional fast-path extraction results to use as fallback

        Returns:
            Dictionary with structured data including work_experience, education,
            professional_summary, certifications, etc.
        """
        logger.info(f"🔧 Extracting structured profile data for {candidate_name}")
        start_time = time.time()

        # Check cache first
        cache_key = f"profile_extraction_{candidate_id}"

        try:
            # Enhanced prompt for comprehensive data extraction
            extraction_prompt = f"""
You are an expert resume parser. Extract structured data from this resume for candidate profile display.

CANDIDATE: {candidate_name}
FULL RESUME TEXT:
{raw_resume_text}

EXTRACT ALL INFORMATION and format as JSON:

EXAMPLE OUTPUT FORMAT:
{{
    "professional_summary": "Brief summary of background and expertise",
    "current_title": "Most recent job title",
    "work_experience": [
        {{
            "company": "Actual Company Name",
            "position": "Actual Job Title", 
            "duration": "Jan 2023 - Present",
            "description": "Key achievements and responsibilities",
            "technologies": ["Python", "React", "AWS"]
        }}
    ],
    "education": [
        {{
            "institution": "University Name",
            "degree": "Bachelor of Science",
            "field": "Computer Science", 
            "year": "2020"
        }}
    ],
    "certifications": ["AWS Certified", "Google Analytics"],
    "languages": ["Python", "JavaScript", "English", "Spanish"],
    "key_achievements": ["Led team of 5", "Increased efficiency by 40%"],
    "extraction_confidence": 0.95
}}

CRITICAL INSTRUCTIONS:
1. Look for sections like "PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE", "EXPERIENCE", "EMPLOYMENT"
2. Look for sections like "EDUCATION", "ACADEMIC BACKGROUND", "DEGREES"
3. Extract EVERY job and education entry you find - don't skip any
4. For work experience: extract company name, job title, dates, and key accomplishments
5. For education: extract school name, degree type, field of study, graduation year
6. If dates are embedded with company/location, parse them out (e.g., "Company, City Jan 2020 - Dec 2022")
7. Be thorough - scan the ENTIRE resume text for all relevant information
8. If you find education or work experience, the arrays must NOT be empty
9. Even partial information is better than empty arrays

RETURN VALID JSON ONLY - NO OTHER TEXT."""

            # Make AI extraction call with optimized settings
            llm_response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume parser. You MUST extract ALL work experience and education entries found in resumes. Never return empty arrays if data exists. Always return valid JSON.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"},
                max_tokens=3000,  # Increased for full extraction
                timeout=15,  # Increased timeout for longer processing
            )

            # Parse the JSON response
            raw_json = llm_response.choices[0].message.content

            # 🚨 DEBUG: Log raw OpenAI response
            logger.info(f"🤖 RAW OpenAI RESPONSE for {candidate_name}:")
            logger.info(f"📄 Response length: {len(raw_json)} characters")
            logger.info(
                f"📄 Raw JSON: {raw_json[:1000]}{'...' if len(raw_json) > 1000 else ''}"
            )

            structured_data = orjson.loads(raw_json)

            # 🚨 DEBUG: Log parsed data before validation
            logger.info(f"🔍 PARSED DATA BEFORE VALIDATION:")
            logger.info(
                f"   Work Experience entries: {len(structured_data.get('work_experience', []))}"
            )
            logger.info(
                f"   Education entries: {len(structured_data.get('education', []))}"
            )
            if structured_data.get("work_experience"):
                for i, exp in enumerate(structured_data.get("work_experience", [])[:3]):
                    logger.info(f"   Work Exp {i+1}: {exp}")
            if structured_data.get("education"):
                for i, edu in enumerate(structured_data.get("education", [])[:3]):
                    logger.info(f"   Education {i+1}: {edu}")

            # Validate and clean the extracted data
            structured_data = self._validate_structured_data(structured_data)

            # 🚨 DEBUG: Log data after validation
            logger.info(f"🔍 PARSED DATA AFTER VALIDATION:")
            logger.info(
                f"   Work Experience entries: {len(structured_data.get('work_experience', []))}"
            )
            logger.info(
                f"   Education entries: {len(structured_data.get('education', []))}"
            )
            if structured_data.get("work_experience"):
                for i, exp in enumerate(structured_data.get("work_experience", [])[:3]):
                    logger.info(f"   Final Work Exp {i+1}: {exp}")
            if structured_data.get("education"):
                for i, edu in enumerate(structured_data.get("education", [])[:3]):
                    logger.info(f"   Final Education {i+1}: {edu}")

            # 🚀 ENHANCED FALLBACK: Use fast-path data if AI extraction returned empty arrays
            if fast_path_data and self._should_use_fast_path_fallback(structured_data):
                logger.info(
                    f"🔄 Enhanced extraction returned empty arrays - using fast-path fallback for {candidate_name}"
                )
                structured_data = self._merge_with_fast_path_data(
                    structured_data, fast_path_data
                )

                logger.info(f"🚀 FALLBACK APPLIED:")
                logger.info(
                    f"   Work Experience entries: {len(structured_data.get('work_experience', []))}"
                )
                logger.info(
                    f"   Education entries: {len(structured_data.get('education', []))}"
                )

            # Record successful extraction
            self.analytics.record_extraction(
                success=True,
                extraction_time=time.time() - start_time,
                extracted_data=None,  # We don't have ExtractedResumeData object here
                cache_hit=False,
            )

            logger.info(
                f"✅ Structured extraction completed for {candidate_name} "
                f"(confidence: {structured_data.get('extraction_confidence', 0):.2f})"
            )

            return structured_data

        except orjson.JSONDecodeError as e:
            logger.warning(
                f"JSON parsing failed for {candidate_name}, attempting repair: {e}"
            )
            try:
                # Try to fix malformed JSON
                repaired_json = json_repair.repair_json(raw_json)
                structured_data = orjson.loads(repaired_json)
                structured_data = self._validate_structured_data(structured_data)
                return structured_data
            except Exception as repair_error:
                logger.error(f"JSON repair failed for {candidate_name}: {repair_error}")
                return self._get_fallback_structured_data(
                    candidate_name, raw_resume_text
                )

        except Exception as e:
            logger.error(f"Structured extraction failed for {candidate_name}: {e}")
            self.analytics.record_extraction(
                success=False,
                extraction_time=time.time() - start_time,
                error_type=type(e).__name__,
            )
            return self._get_fallback_structured_data(candidate_name, raw_resume_text)

    def _validate_structured_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted structured data."""
        # Set defaults for missing fields
        defaults = {
            "professional_summary": "",
            "current_title": "",
            "work_experience": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "key_achievements": [],
            "extraction_confidence": 0.5,
        }

        # Apply defaults
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value

        # Validate work experience structure
        if isinstance(data.get("work_experience"), list):
            validated_experience = []
            for exp in data["work_experience"]:
                if isinstance(exp, dict):
                    # More flexible validation - accept if we have basic info
                    company = str(exp.get("company", "")).strip()
                    # Handle both 'title' and 'position' field names for compatibility
                    position = str(exp.get("title", exp.get("position", ""))).strip()

                    # Accept entry if we have at least company OR position
                    if company or position:
                        validated_exp = {
                            "company": company or "Company name not specified",
                            "position": position or "Position not specified",
                            "duration": str(
                                exp.get("duration", "Duration not specified")
                            ),
                            "description": str(exp.get("description", ""))[
                                :300
                            ],  # Limit length
                            "technologies": (
                                exp.get("technologies", [])
                                if isinstance(exp.get("technologies"), list)
                                else []
                            ),
                        }
                        validated_experience.append(validated_exp)

                        # 🚀 DEBUG: Log successful validation
                        from app.core.config import settings

                        if settings.app_verbose_extraction:
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.info(f"✅ WORK EXP VALIDATED: {validated_exp}")
                    else:
                        # 🚨 DEBUG: Log rejected entries
                        from app.core.config import settings

                        if settings.app_verbose_extraction:
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.warning(f"❌ WORK EXP REJECTED: {exp}")

            data["work_experience"] = validated_experience[:10]  # Limit to 10 entries

        # Validate education structure
        if isinstance(data.get("education"), list):
            validated_education = []
            for edu in data["education"]:
                if isinstance(edu, dict):
                    # More flexible validation - accept if we have basic education info
                    institution = str(edu.get("institution", "")).strip()
                    degree = str(edu.get("degree", "")).strip()

                    # Accept entry if we have at least institution OR degree
                    if institution or degree:
                        validated_edu = {
                            "institution": institution or "Institution not specified",
                            "degree": degree or "Degree not specified",
                            "field": (
                                str(edu.get("field", "")).strip()
                                if edu.get("field")
                                else None
                            ),
                            "year": (
                                str(edu.get("year", "")).strip()
                                if edu.get("year")
                                else None
                            ),
                        }
                        validated_education.append(validated_edu)

                        # 🚀 DEBUG: Log successful validation
                        from app.core.config import settings

                        if settings.app_verbose_extraction:
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.info(f"✅ EDUCATION VALIDATED: {validated_edu}")
                    else:
                        # 🚨 DEBUG: Log rejected entries
                        from app.core.config import settings

                        if settings.app_verbose_extraction:
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.warning(f"❌ EDUCATION REJECTED: {edu}")

            data["education"] = validated_education[:5]  # Limit to 5 entries

        # Ensure confidence is a valid float
        try:
            data["extraction_confidence"] = float(
                data.get("extraction_confidence", 0.5)
            )
            data["extraction_confidence"] = max(
                0.0, min(1.0, data["extraction_confidence"])
            )
        except (ValueError, TypeError):
            data["extraction_confidence"] = 0.5

        return data

    def _should_use_fast_path_fallback(self, structured_data: Dict[str, Any]) -> bool:
        """Check if we should use fast-path data as fallback for enhanced extraction."""
        work_exp_empty = (
            not structured_data.get("work_experience")
            or len(structured_data.get("work_experience", [])) == 0
        )
        education_empty = (
            not structured_data.get("education")
            or len(structured_data.get("education", [])) == 0
        )

        # Use fallback if both work experience and education are empty
        return work_exp_empty and education_empty

    def _merge_with_fast_path_data(
        self, enhanced_data: Dict[str, Any], fast_path_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge enhanced extraction with fast-path data as fallback."""
        merged_data = enhanced_data.copy()

        # Use fast-path work experience if enhanced is empty
        if not merged_data.get("work_experience"):
            fast_work_exp = fast_path_data.get("work_experience", [])
            if fast_work_exp:
                # Convert fast-path format to enhanced format
                enhanced_work_exp = []
                for exp in fast_work_exp:
                    enhanced_exp = {
                        "company": exp.get("company", ""),
                        "position": exp.get(
                            "title", exp.get("position", "")
                        ),  # Handle both field names
                        "duration": exp.get("duration", ""),
                        "description": f"Professional role at {exp.get('company', 'company')}",
                        "technologies": exp.get("technologies", []),
                    }
                    enhanced_work_exp.append(enhanced_exp)
                merged_data["work_experience"] = enhanced_work_exp
                logger.info(
                    f"🚀 FALLBACK: Added {len(enhanced_work_exp)} work experience entries from fast-path"
                )

        # Use fast-path education if enhanced is empty
        if not merged_data.get("education"):
            fast_education = fast_path_data.get("education", [])
            if fast_education:
                # Convert fast-path format to enhanced format
                enhanced_education = []
                for edu in fast_education:
                    enhanced_edu = {
                        "institution": edu.get(
                            "school", edu.get("institution", "")
                        ),  # Handle both field names
                        "degree": edu.get("degree", ""),
                        "field": edu.get("field"),
                        "year": edu.get("graduation_year", edu.get("year")),
                    }
                    enhanced_education.append(enhanced_edu)
                merged_data["education"] = enhanced_education
                logger.info(
                    f"🚀 FALLBACK: Added {len(enhanced_education)} education entries from fast-path"
                )

        # Update confidence if we used fallback data
        if fast_path_data.get("confidence"):
            # Boost confidence since we have real extracted data
            original_confidence = merged_data.get("extraction_confidence", 0.5)
            fast_path_confidence = fast_path_data.get("confidence", 0.9)
            merged_confidence = max(
                original_confidence, fast_path_confidence * 0.9
            )  # Slightly lower than original fast-path
            merged_data["extraction_confidence"] = merged_confidence
            logger.info(
                f"🚀 FALLBACK: Updated confidence from {original_confidence:.2f} to {merged_confidence:.2f}"
            )

        return merged_data

    def _get_fallback_structured_data(
        self, candidate_name: str, raw_resume_text: str
    ) -> Dict[str, Any]:
        """Generate fallback structured data when AI extraction fails."""
        logger.info(f"🔄 Generating fallback structured data for {candidate_name}")

        # Use basic regex patterns as fallback
        work_experience = []
        education = []

        # Try to extract basic work experience
        if raw_resume_text:
            # Look for common patterns in work experience
            experience_pattern = r"(\d{4})\s*[-–]\s*(\d{4}|Present|Current)"
            experience_matches = re.findall(
                experience_pattern, raw_resume_text, re.IGNORECASE
            )

            if experience_matches:
                # Create basic work experience entry
                work_experience.append(
                    {
                        "company": "Experience details in resume",
                        "position": "Multiple positions",
                        "duration": f"Professional experience spanning {len(experience_matches)} roles",
                        "description": "Full details available in resume text",
                        "technologies": [],
                    }
                )

        # Try to extract basic education
        education_keywords = [
            "university",
            "college",
            "bachelor",
            "master",
            "phd",
            "degree",
        ]
        for keyword in education_keywords:
            if keyword.lower() in raw_resume_text.lower():
                education.append(
                    {
                        "institution": "Educational background in resume",
                        "degree": "Degree information available",
                        "field": None,
                        "year": None,
                    }
                )
                break

        return {
            "professional_summary": f"Professional with experience across multiple domains. Full details available in resume.",
            "current_title": "Professional",
            "work_experience": work_experience,
            "education": education,
            "certifications": [],
            "languages": [],
            "key_achievements": [
                "Professional experience",
                "Educational background",
                "Technical skills",
            ],
            "extraction_confidence": 0.3,  # Low confidence for fallback
        }
