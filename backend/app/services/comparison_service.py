"""
AI Comparison Service

This service handles multi-candidate analysis for the AI Hiring Advisor feature.
It leverages the existing candidate insights infrastructure and adds comparison-specific logic.
"""

import logging
import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.models.api_models import (
    ComparisonAnalysisResponse,
    ComparisonRequest,
    ComparisonWinner,
    ComparisonMatrix,
    HiddenInsight,
    CandidateInsightsResponse,
)

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    Service for analyzing multiple candidates and providing AI-powered hiring recommendations.

    This service leverages existing candidate insights functionality and extends it
    to provide comparative analysis, hidden insights, and hiring recommendations.
    """

    def __init__(self, llm_service: LLMService, rag_service: RAGService):
        """
        Initialize the ComparisonService.

        Args:
            llm_service: Service for LLM interactions
            rag_service: Service for candidate data retrieval
        """
        self.llm_service = llm_service
        self.rag_service = rag_service

    async def analyze_candidates_comparison(
        self, request: ComparisonRequest
    ) -> ComparisonAnalysisResponse:
        """
        Analyze multiple candidates and provide comprehensive comparison insights.

        Args:
            request: ComparisonRequest containing candidate IDs and job context

        Returns:
            ComparisonAnalysisResponse with winner, individual insights, and comparison data

        Raises:
            ValueError: If candidates not found or analysis fails
        """
        start_time = datetime.now()
        processing_start = asyncio.get_event_loop().time()

        logger.info(
            f"Starting comparison analysis for {len(request.candidate_ids)} candidates"
        )

        try:
            # Step 1: Get individual candidate insights (reuse existing logic!)
            candidate_insights = await self._get_all_candidate_insights(
                request.candidate_ids
            )

            # Step 2: Generate hidden insights using AI
            hidden_insights = await self._discover_hidden_insights(
                candidate_insights, request.job_role_title, request.job_role_description
            )

            # Step 3: Create comparison matrix
            comparison_matrix = self._build_comparison_matrix(
                candidate_insights, request
            )

            # Step 4: Determine winner using AI analysis
            winner = await self._determine_winner(
                candidate_insights, hidden_insights, request
            )

            # Step 5: Calculate processing time
            processing_time_ms = (
                asyncio.get_event_loop().time() - processing_start
            ) * 1000

            # Step 6: Build response
            response = ComparisonAnalysisResponse(
                winner=winner,
                candidates=candidate_insights,
                hidden_insights=hidden_insights,
                comparison_matrix=comparison_matrix,
                analysis_timestamp=start_time,
                processing_time_ms=processing_time_ms,
                job_context=(
                    f"{request.job_role_title}: {request.job_role_description}"
                    if request.job_role_description
                    else request.job_role_title
                ),
                ai_confidence=winner.confidence / 100.0,  # Convert to 0-1 scale
            )

            logger.info(
                f"Comparison analysis completed in {processing_time_ms:.1f}ms. Winner: {winner.candidate_name}"
            )
            return response

        except Exception as e:
            logger.error(f"Comparison analysis failed: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze candidates: {str(e)}")

    async def _get_all_candidate_insights(
        self, candidate_ids: List[str]
    ) -> List[CandidateInsightsResponse]:
        """
        Get individual insights for all candidates using existing insights logic.

        This leverages the same code path as the /insights endpoint.
        """
        insights = []

        for candidate_id in candidate_ids:
            try:
                # Use the same logic as the insights endpoint
                insight = await self._get_single_candidate_insight(candidate_id)
                insights.append(insight)
            except Exception as e:
                logger.warning(
                    f"Failed to get insights for candidate {candidate_id}: {e}"
                )
                # Create fallback insight so we don't lose the candidate completely
                fallback_insight = CandidateInsightsResponse(
                    candidate_id=candidate_id,
                    fit_score=50.0,
                    strengths=["Data unavailable", "Manual review needed"],
                    interview_questions=["Please review candidate manually"],
                )
                insights.append(fallback_insight)

        return insights

    async def _get_single_candidate_insight(
        self, candidate_id: str
    ) -> CandidateInsightsResponse:
        """
        Get insights for a single candidate (replicates insights endpoint logic).
        """
        try:
            # First try the in-memory cache (pre-loaded JSON profiles)
            candidate = await self.rag_service.get_candidate_details_by_id(candidate_id)
            skills = candidate.skills
            years_exp = candidate.experience_years
            metadata = None
        except ValueError:
            # Fallback: fetch metadata directly from Chroma
            logger.info(
                f"Candidate {candidate_id} not found in cache – trying Chroma metadata fallback."
            )

            try:
                result = await asyncio.to_thread(
                    self.rag_service.collection.get,
                    ids=[candidate_id],
                    include=["metadatas"],
                )

                meta_list = result.get("metadatas", [])
                if not meta_list or not meta_list[0]:
                    raise ValueError("Metadata not found for candidate in ChromaDB")

                metadata = meta_list[0]
                skills_str = metadata.get("skills", "")
                skills = [s.strip() for s in skills_str.split(",") if s.strip()]
                years_exp = int(float(metadata.get("experience_years", 0)))
            except Exception as e:
                logger.error(f"Chroma fallback failed for {candidate_id}: {e}")
                raise ValueError(f"Candidate {candidate_id} not found")

        # Try AI-powered insights first
        try:
            # Get rich candidate data for better AI analysis
            candidate_summary = await self._get_rich_candidate_summary(
                candidate_id, metadata
            )

            insights_prompt = f"""
Analyze this candidate profile and provide detailed recruitment insights:

{candidate_summary}

Provide a comprehensive JSON response with:
1. fit_score: A score from 60-95 based on technical skills, experience level, and career trajectory
2. strengths: Exactly 3 unique professional strengths based on actual achievements and skills
3. interview_questions: Exactly 3 thoughtful questions tailored to this candidate's background

Consider:
- Technical skill depth and breadth
- Career progression and growth
- Project complexity and impact
- Leadership and communication indicators
- Specialization areas and market value

Format as JSON:
{{
    "fit_score": <number>,
    "strengths": ["strength1", "strength2", "strength3"],
    "interview_questions": ["question1", "question2", "question3"]
}}
"""

            llm_response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical recruiter with deep knowledge of software engineering roles.",
                    },
                    {"role": "user", "content": insights_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
                max_tokens=500,
            )

            insights_data = json.loads(llm_response.choices[0].message.content)

            if all(
                key in insights_data
                for key in ["fit_score", "strengths", "interview_questions"]
            ):
                return CandidateInsightsResponse(
                    candidate_id=candidate_id,
                    fit_score=float(insights_data["fit_score"]),
                    strengths=insights_data["strengths"],
                    interview_questions=insights_data["interview_questions"],
                )

        except Exception as e:
            logger.warning(
                f"LLM insights generation failed for candidate {candidate_id}: {e}"
            )

        # Fallback to heuristic approach (same as insights endpoint)
        from app.api.routers.candidate_router import calculate_enhanced_fit_score

        fit_score = calculate_enhanced_fit_score(
            skills=skills,
            years_exp=years_exp,
            has_github=bool(metadata.get("github_url")) if metadata else False,
            has_linkedin=bool(metadata.get("linkedin_url")) if metadata else False,
            profile_completeness=(
                0.7 if metadata and metadata.get("summary_text") else 0.5
            ),
        )

        strengths = (
            skills[:3]
            if len(skills) >= 3
            else skills
            + ["Communication", "Problem-solving", "Team collaboration"][
                : 3 - len(skills)
            ]
        )

        fallback_questions = [
            "Describe a challenging project you led and its outcome.",
            "How do you stay current with the technologies you use?",
            "What trade-offs did you face in your most recent architecture decision?",
        ]

        return CandidateInsightsResponse(
            candidate_id=candidate_id,
            fit_score=round(fit_score, 1),
            strengths=strengths,
            interview_questions=fallback_questions,
        )

    async def _discover_hidden_insights(
        self,
        candidate_insights: List[CandidateInsightsResponse],
        job_role_title: Optional[str],
        job_role_description: Optional[str],
    ) -> List[HiddenInsight]:
        """
        Use AI to discover hidden insights about candidates that aren't obvious from their profiles.
        """
        try:
            # Prepare rich candidate summaries for AI analysis
            candidate_summaries = []
            for insight in candidate_insights:
                # Get rich summary for each candidate
                rich_summary = await self._get_rich_candidate_summary(
                    insight.candidate_id
                )
                summary = f"=== CANDIDATE ANALYSIS ===\n{rich_summary}\nFit Score: {insight.fit_score}%\nKey Strengths: {', '.join(insight.strengths)}\n"
                candidate_summaries.append(summary)

            job_context = f"Job: {job_role_title}" + (
                f" - {job_role_description}" if job_role_description else ""
            )

            insights_prompt = f"""
You are an expert recruiter with deep market knowledge. Analyze these candidates and discover hidden insights that would help make hiring decisions.

{job_context}

Candidates:
{chr(10).join(candidate_summaries)}

Discover 2-3 hidden insights that aren't obvious from basic profiles. Focus on:
- Rare skill combinations and their market value
- Potential risks (visa status, job hopping, overqualification)
- Hidden strengths (GitHub activity, specific project experience)
- Market positioning and salary expectations

Return a JSON array of insights:
[
  {{
    "candidate_id": "candidate_id",
    "insight_type": "rare_skill_combo|risk_factor|hidden_strength|market_position",
    "title": "🔥 Brief impactful title (use relevant emoji)",
    "description": "Detailed explanation of this insight and its impact",
    "impact_level": "high|medium|low"
  }}
]
"""

            llm_response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical recruiter with deep knowledge of the software engineering market and hiring patterns.",
                    },
                    {"role": "user", "content": insights_prompt},
                ],
                temperature=0.8,  # Higher temperature for creativity
                response_format={"type": "json_object"},
                max_tokens=800,
            )

            insights_data = json.loads(llm_response.choices[0].message.content)

            # Parse the insights array (handle both direct array and wrapped object)
            insights_array = (
                insights_data
                if isinstance(insights_data, list)
                else insights_data.get("insights", [])
            )

            hidden_insights = []
            for insight_data in insights_array[:5]:  # Limit to 5 insights
                try:
                    insight = HiddenInsight(
                        candidate_id=insight_data["candidate_id"],
                        insight_type=insight_data["insight_type"],
                        title=insight_data["title"],
                        description=insight_data["description"],
                        impact_level=insight_data["impact_level"],
                    )
                    hidden_insights.append(insight)
                except (KeyError, ValueError) as e:
                    logger.warning(
                        f"Failed to parse insight: {insight_data}, error: {e}"
                    )
                    continue

            return hidden_insights

        except Exception as e:
            logger.warning(f"Failed to generate hidden insights: {e}")
            # Return fallback insights based on candidate data
            return self._generate_fallback_insights(candidate_insights)

    def _generate_fallback_insights(
        self, candidate_insights: List[CandidateInsightsResponse]
    ) -> List[HiddenInsight]:
        """Generate fallback insights when AI analysis fails."""
        insights = []

        # Find highest scoring candidate
        if candidate_insights:
            best_candidate = max(candidate_insights, key=lambda c: c.fit_score)
            insights.append(
                HiddenInsight(
                    candidate_id=best_candidate.candidate_id,
                    insight_type="top_performer",
                    title=f"⭐ Top performer with {best_candidate.fit_score}% fit score",
                    description=f"This candidate scored highest in our technical assessment with notable strengths in {', '.join(best_candidate.strengths[:2])}.",
                    impact_level="high",
                )
            )

        return insights

    async def _get_rich_candidate_summary(
        self, candidate_id: str, metadata: Optional[Dict] = None
    ) -> str:
        """Get a rich summary of candidate data for AI analysis."""
        try:
            # Try to get full candidate details
            candidate = await self.rag_service.get_candidate_details_by_id(candidate_id)

            summary_parts = [
                f"Candidate ID: {candidate_id}",
                f"Name: {candidate.name}",
                f"Location: {candidate.location}",
                f"Experience: {candidate.experience_years} years",
                f"Current Title: {getattr(candidate, 'current_title', 'Not specified')}",
                f"Skills ({len(candidate.skills)}): {', '.join(candidate.skills[:20])}{'...' if len(candidate.skills) > 20 else ''}",
            ]

            # Add work experience details
            if hasattr(candidate, "work_experience") and candidate.work_experience:
                summary_parts.append("\nWork Experience:")
                for i, exp in enumerate(candidate.work_experience[:3]):  # Show top 3
                    summary_parts.append(
                        f"  {i+1}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})"
                    )
                    if exp.get("description"):
                        summary_parts.append(f"     - {exp['description'][:150]}...")

            # Add education details
            if hasattr(candidate, "education") and candidate.education:
                summary_parts.append("\nEducation:")
                for edu in candidate.education:
                    degree = edu.get("degree", "N/A")
                    field = edu.get("field", "")
                    school = edu.get("school") or edu.get("institution", "N/A")
                    summary_parts.append(
                        f"  - {degree}{f' in {field}' if field else ''} from {school}"
                    )
                    if edu.get("description"):
                        summary_parts.append(
                            f"    Details: {edu['description'][:100]}..."
                        )

            return "\n".join(summary_parts)

        except Exception as e:
            logger.warning(f"Failed to get rich candidate data for {candidate_id}: {e}")

            # Fallback to metadata-based summary
            if metadata:
                summary_parts = [
                    f"Candidate ID: {candidate_id}",
                    f"Name: {metadata.get('name', 'Unknown')}",
                    f"Experience: {metadata.get('experience_years', 0)} years",
                    f"Skills: {metadata.get('skills', 'Not specified')}",
                    f"Location: {metadata.get('location', 'Not specified')}",
                ]

                if metadata.get("summary_text"):
                    summary_parts.append(
                        f"\nResume Summary: {metadata['summary_text'][:300]}..."
                    )

                return "\n".join(summary_parts)

            # Basic fallback
            return f"Candidate ID: {candidate_id}\nLimited data available - manual review recommended"

    def _build_comparison_matrix(
        self,
        candidate_insights: List[CandidateInsightsResponse],
        request: ComparisonRequest,
    ) -> ComparisonMatrix:
        """
        Build a comparison matrix showing how candidates rank across different criteria using actual candidate data.
        """
        matrix = ComparisonMatrix(
            technical_match={}, culture_fit={}, retention_risk={}, growth_potential={}
        )

        for insight in candidate_insights:
            candidate_id = insight.candidate_id

            # Technical match is based on fit score
            matrix.technical_match[candidate_id] = insight.fit_score

            # Get actual candidate data for realistic scoring
            try:
                candidate = asyncio.get_event_loop().run_until_complete(
                    asyncio.to_thread(
                        self.rag_service.get_candidate_details_by_id, candidate_id
                    )
                )

                # Culture fit: based on soft skills, education, and experience diversity
                culture_score = self._calculate_culture_fit(candidate, insight)
                matrix.culture_fit[candidate_id] = culture_score

                # Retention risk: based on job history, experience level, and market factors
                retention_score = self._calculate_retention_risk(candidate, insight)
                matrix.retention_risk[candidate_id] = retention_score

                # Growth potential: based on learning trajectory, skills breadth, and career progression
                growth_score = self._calculate_growth_potential(candidate, insight)
                matrix.growth_potential[candidate_id] = growth_score

            except Exception as e:
                logger.warning(
                    f"Failed to get candidate data for matrix calculation {candidate_id}: {e}"
                )
                # Fallback to basic calculation if candidate data unavailable
                matrix.culture_fit[candidate_id] = min(
                    85, max(60, insight.fit_score * 0.9)
                )
                matrix.retention_risk[candidate_id] = min(
                    40, max(15, 45 - (insight.fit_score * 0.3))
                )
                matrix.growth_potential[candidate_id] = min(
                    90, max(65, insight.fit_score * 0.95)
                )

        return matrix

    def _calculate_culture_fit(self, candidate, insight) -> float:
        """Calculate culture fit based on actual candidate characteristics."""
        base_score = 70

        # Education diversity bonus (different fields/levels)
        if hasattr(candidate, "education") and len(candidate.education) > 1:
            base_score += 5

        # Experience diversity (different companies/roles)
        if hasattr(candidate, "work_experience") and len(candidate.work_experience) > 1:
            base_score += 5

        # Communication skills (inferred from role types)
        communication_roles = ["lead", "senior", "manager", "architect", "consultant"]
        if any(
            role in str(candidate.current_title).lower() for role in communication_roles
        ):
            base_score += 8

        # Soft skills from strengths
        soft_skills = [
            "communication",
            "collaboration",
            "leadership",
            "mentoring",
            "teamwork",
        ]
        soft_skill_count = sum(
            1
            for strength in insight.strengths
            for skill in soft_skills
            if skill.lower() in strength.lower()
        )
        base_score += soft_skill_count * 3

        # Location stability (local candidates may fit better)
        if hasattr(candidate, "location") and "boston" in candidate.location.lower():
            base_score += 3

        return min(95, max(45, base_score))

    def _calculate_retention_risk(self, candidate, insight) -> float:
        """Calculate retention risk based on actual candidate characteristics."""
        base_risk = 30  # Start with low risk

        # Job hopping pattern (high frequency = higher risk)
        if hasattr(candidate, "work_experience") and len(candidate.work_experience) > 2:
            # If more than 2 jobs and less than 2 years each on average
            if candidate.experience_years / len(candidate.work_experience) < 2:
                base_risk += 15

        # Overqualification risk (very senior for potential role level)
        if candidate.experience_years > 8 and insight.fit_score > 90:
            base_risk += 10

        # Underqualification risk (may leave for better opportunities)
        if candidate.experience_years < 2 and insight.fit_score < 75:
            base_risk += 8

        # Skills mismatch (may not enjoy the work)
        if insight.fit_score < 70:
            base_risk += 12

        # High performers in competitive fields (AI/ML) have higher market demand
        ai_skills = ["ai", "ml", "machine learning", "tensorflow", "pytorch", "openai"]
        if any(
            skill.lower() in " ".join(candidate.skills).lower() for skill in ai_skills
        ):
            base_risk += 8

        return min(80, max(10, base_risk))

    def _calculate_growth_potential(self, candidate, insight) -> float:
        """Calculate growth potential based on actual candidate characteristics."""
        base_potential = 75

        # Learning trajectory (diverse skills = learning mindset)
        if len(candidate.skills) > 15:
            base_potential += 8

        # Modern technology adoption
        modern_tech = [
            "react",
            "typescript",
            "docker",
            "kubernetes",
            "aws",
            "microservices",
        ]
        modern_count = sum(
            1
            for skill in candidate.skills
            for tech in modern_tech
            if tech.lower() in skill.lower()
        )
        base_potential += min(10, modern_count * 2)

        # Educational background (advanced degrees show learning capacity)
        if hasattr(candidate, "education"):
            for edu in candidate.education:
                if (
                    "master" in edu.get("degree", "").lower()
                    or "phd" in edu.get("degree", "").lower()
                ):
                    base_potential += 5
                    break

        # Career progression (title advancement)
        if hasattr(candidate, "work_experience") and len(candidate.work_experience) > 1:
            # Look for progression indicators in titles
            progression_terms = ["junior", "senior", "lead", "principal", "staff"]
            titles = [exp.get("title", "") for exp in candidate.work_experience]
            if any(term in " ".join(titles).lower() for term in progression_terms):
                base_potential += 6

        # High technical fit suggests growth alignment
        if insight.fit_score > 85:
            base_potential += 5

        return min(100, max(50, base_potential))

    async def _determine_winner(
        self,
        candidate_insights: List[CandidateInsightsResponse],
        hidden_insights: List[HiddenInsight],
        request: ComparisonRequest,
    ) -> ComparisonWinner:
        """
        Use AI to determine the best candidate with detailed reasoning.
        """
        if not candidate_insights:
            raise ValueError("No candidate insights available for winner determination")

        try:
            # Prepare rich data for AI analysis
            candidates_summary = []
            for insight in candidate_insights:
                rich_summary = await self._get_rich_candidate_summary(
                    insight.candidate_id
                )
                summary = f"""
=== CANDIDATE PROFILE ===
{rich_summary}

ASSESSMENT RESULTS:
- Fit Score: {insight.fit_score}%
- Key Strengths: {', '.join(insight.strengths)}
- Recommended Interview Questions: {', '.join(insight.interview_questions)}
"""
                candidates_summary.append(summary)

            insights_summary = []
            for hidden in hidden_insights:
                if hidden.impact_level == "high":
                    insights_summary.append(
                        f"{hidden.candidate_id}: {hidden.title} - {hidden.description}"
                    )

            job_context = request.job_role_title or "software engineering role"

            winner_prompt = f"""
You are an expert hiring manager. Analyze these candidates for a {job_context} position and recommend the best hire.

CANDIDATES:
{chr(10).join(candidates_summary)}

HIGH-IMPACT INSIGHTS:
{chr(10).join(insights_summary) if insights_summary else "No special insights discovered."}

Consider:
1. Technical fit and skills match
2. Experience level appropriateness
3. Any hidden insights or special factors
4. Potential risks vs opportunities

Recommend the best candidate with detailed reasoning. Return JSON:
{{
    "candidate_id": "best_candidate_id",
    "candidate_name": "Best Candidate Name",
    "confidence": 85,
    "reasoning": "Detailed explanation of why this candidate is the best choice",
    "key_advantages": ["advantage1", "advantage2", "advantage3"],
    "potential_risks": ["risk1", "risk2"]
}}
"""

            llm_response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert hiring manager with 15+ years of experience making successful technical hires.",
                    },
                    {"role": "user", "content": winner_prompt},
                ],
                temperature=0.3,  # Lower temperature for consistent decision-making
                response_format={"type": "json_object"},
                max_tokens=600,
            )

            winner_data = json.loads(llm_response.choices[0].message.content)

            # Extract candidate name from insights if not provided by AI
            winner_id = winner_data["candidate_id"]
            candidate_name = winner_data.get("candidate_name", winner_id)

            # Try to get actual candidate name from RAG service
            try:
                candidate = await self.rag_service.get_candidate_details_by_id(
                    winner_id
                )
                candidate_name = candidate.name
            except Exception:
                # Fallback: try to get name from ChromaDB metadata
                try:
                    result = await asyncio.to_thread(
                        self.rag_service.collection.get,
                        ids=[winner_id],
                        include=["metadatas"],
                    )
                    meta_list = result.get("metadatas", [])
                    if meta_list and meta_list[0]:
                        metadata = meta_list[0]
                        candidate_name = metadata.get(
                            "name", winner_id.replace("_", " ").title()
                        )
                    else:
                        candidate_name = winner_id.replace("_", " ").title()
                except Exception:
                    candidate_name = winner_id.replace("_", " ").title()

            return ComparisonWinner(
                candidate_id=winner_id,
                candidate_name=candidate_name,
                confidence=min(
                    95, max(60, winner_data.get("confidence", 75))
                ),  # Clamp confidence
                reasoning=winner_data["reasoning"],
                key_advantages=winner_data.get(
                    "key_advantages", ["Strong technical fit"]
                ),
                potential_risks=winner_data.get(
                    "potential_risks", ["Standard hiring risks"]
                ),
            )

        except Exception as e:
            logger.warning(f"AI winner determination failed: {e}")
            # Fallback: choose highest scoring candidate
            best_candidate = max(candidate_insights, key=lambda c: c.fit_score)
            return ComparisonWinner(
                candidate_id=best_candidate.candidate_id,
                candidate_name=best_candidate.candidate_id.replace("_", " ").title(),
                confidence=min(best_candidate.fit_score, 95),
                reasoning=f"Highest technical fit score of {best_candidate.fit_score}% with strong expertise in {', '.join(best_candidate.strengths[:2])}.",
                key_advantages=best_candidate.strengths[:3],
                potential_risks=[
                    "Standard technical role risks",
                    "Requires technical interview validation",
                ],
            )
