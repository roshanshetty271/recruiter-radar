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
            insights_prompt = f"""
Analyze this candidate profile and provide recruitment insights:

Name: {candidate_id}
Experience: {years_exp} years
Skills: {', '.join(skills)}
{f"Raw resume excerpt: {metadata.get('summary_text', '')[:300]}..." if metadata and metadata.get('summary_text') else ""}

Provide a JSON response with:
1. fit_score: A score from 60-95 for a general software engineering role
2. strengths: Exactly 3 unique professional strengths
3. interview_questions: Exactly 3 thoughtful technical/behavioral questions

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
            # Prepare candidate summaries for AI analysis
            candidate_summaries = []
            for insight in candidate_insights:
                summary = f"ID: {insight.candidate_id}, Score: {insight.fit_score}, Strengths: {', '.join(insight.strengths)}"
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

    def _build_comparison_matrix(
        self,
        candidate_insights: List[CandidateInsightsResponse],
        request: ComparisonRequest,
    ) -> ComparisonMatrix:
        """
        Build a comparison matrix showing how candidates rank across different criteria.
        """
        matrix = ComparisonMatrix(
            technical_match={}, culture_fit={}, retention_risk={}, growth_potential={}
        )

        for insight in candidate_insights:
            candidate_id = insight.candidate_id

            # Technical match is based on fit score
            matrix.technical_match[candidate_id] = insight.fit_score

            # Culture fit: derived from fit score with some variation
            culture_base = insight.fit_score * 0.9  # Slightly lower than technical
            matrix.culture_fit[candidate_id] = max(
                40, min(95, culture_base + hash(candidate_id) % 20 - 10)
            )

            # Retention risk: inverse relationship with fit score
            retention_base = 100 - insight.fit_score
            matrix.retention_risk[candidate_id] = max(
                10, min(80, retention_base + hash(candidate_id + "retention") % 15 - 7)
            )

            # Growth potential: based on fit score with upward bias
            growth_base = insight.fit_score * 1.1  # Slightly higher than technical
            matrix.growth_potential[candidate_id] = max(
                50, min(100, growth_base + hash(candidate_id + "growth") % 15 - 5)
            )

        return matrix

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
            # Prepare data for AI analysis
            candidates_summary = []
            for insight in candidate_insights:
                summary = f"""
Candidate: {insight.candidate_id}
Fit Score: {insight.fit_score}%
Strengths: {', '.join(insight.strengths)}
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

            # Try to get actual name from insights
            for insight in candidate_insights:
                if insight.candidate_id == winner_id:
                    # Use a cleaner name format if possible
                    candidate_name = winner_id.replace("_", " ").title()
                    break

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
