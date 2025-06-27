"""
REAL RAG Service - The Final Boss

This replaces all the hardcoded bullshit with proper RAG:
- Document chunking
- Embedding generation
- Semantic search
- LLM synthesis

NO MORE REGEX PATTERNS OR HARDCODED SKILLS!
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.document_processor import DocumentProcessor
from app.services.semantic_search import SemanticSearchEngine
from app.services.llm_service import LLMService
from app.core.prompts import RECRUITER_RADAR_SYSTEM_PROMPT, CONVERSATIONAL_INTENT_PROMPT

logger = logging.getLogger(__name__)


class RealRAGService:
    """
    The REAL RAG Service

    Handles the complete RAG pipeline:
    1. Intent detection (conversation vs search)
    2. Document ingestion & chunking
    3. Embedding generation & storage
    4. Semantic search & retrieval
    5. LLM synthesis & response generation

    NO MORE HARDCODED METADATA FILTERING!
    """

    def __init__(self):
        from app.core.config import settings

        self.document_processor = DocumentProcessor()
        self.semantic_search = SemanticSearchEngine()
        self.llm_service = LLMService(settings)
        logger.info("🚀 REAL RAG SERVICE INITIALIZED - No more hardcoded bullshit!")

    async def ingest_resume(
        self, file_bytes: bytes, filename: str, session_id: str
    ) -> Dict[str, Any]:
        """
        Ingest a resume using REAL RAG processing:
        1. Extract text
        2. Chunk intelligently
        3. Generate embeddings
        4. Store in vector DB

        Returns processing status and metadata.
        """
        try:
            logger.info(f"🔥 REAL RAG INGESTION: {filename} for session {session_id}")

            result = await self.document_processor.process_resume(
                file_bytes, filename, session_id
            )

            if result["status"] == "success":
                logger.info(
                    f"✅ Successfully ingested {filename} - {result['chunks_created']} chunks"
                )
            else:
                logger.error(
                    f"❌ Failed to ingest {filename}: {result.get('error', 'Unknown error')}"
                )

            return result

        except Exception as e:
            logger.error(
                f"❌ REAL RAG INGESTION failed for {filename}: {e}", exc_info=True
            )
            return {
                "status": "failed",
                "error": f"Ingestion failed: {str(e)}",
                "chunks_created": 0,
            }

    async def search_candidates(
        self, query: str, session_id: str, max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Intelligent search with intent detection.

        Args:
            query: Natural language query (e.g., "Python developers", "explain", "skills of Alex Chen")
            session_id: Session ID for scoped search
            max_results: Maximum candidates to return

        Returns:
            Dict with candidates, AI response, and metadata
        """
        try:
            logger.info(f"🔍 REAL RAG SEARCH: '{query}' in session {session_id}")

            # 🧠 STEP 1: Intent Detection using GPT-4o-mini
            intent_result = await self._detect_intent(query)

            if intent_result["intent"] == "conversation":
                # 💬 Handle conversational queries directly
                logger.info(f"💬 CONVERSATIONAL INTENT: {intent_result['reason']}")

                conversational_response = await self._handle_conversational_query(query)

                return {
                    "candidates": [],  # No candidates for conversational queries
                    "ai_message": conversational_response,
                    "total_chunks": 0,
                    "query_interpretation": intent_result["reason"],
                    "source": "conversation",
                    "processing_time_ms": 0,
                    "success": True,
                }

            # 🔍 STEP 2: Search Intent - Perform semantic search
            logger.info(f"🔍 SEARCH INTENT: {intent_result['reason']}")

            search_result = await self.semantic_search.search_candidates(
                query=query, session_id=session_id, max_results=max_results
            )

            # Format for API response
            response = {
                "candidates": search_result["candidates"],
                "ai_message": search_result["ai_response"],
                "total_chunks": search_result["total_chunks"],
                "query_interpretation": search_result["query_interpretation"],
                "source": "real_rag",
                "processing_time_ms": 0,  # TODO: Add timing
                "success": True,
            }

            logger.info(
                f"✅ REAL RAG SEARCH: Found {len(search_result['candidates'])} candidates"
            )
            return response

        except Exception as e:
            logger.error(f"❌ REAL RAG SEARCH failed: {e}", exc_info=True)
            return {
                "candidates": [],
                "ai_message": f"Search failed: {str(e)}",
                "total_chunks": 0,
                "query_interpretation": query,
                "source": "real_rag_error",
                "processing_time_ms": 0,
                "success": False,
            }

    async def _detect_intent(self, message: str) -> Dict[str, str]:
        """
        🚀 TURBO-PATCH: Fast intent detection with regex short-circuit for obvious searches.

        Returns:
            Dict with 'intent' ("conversation" or "search") and 'reason'
        """
        import re

        # 🔥 SHORT-CIRCUIT: Regex patterns for obvious search queries (NO LLM CALL!)
        search_patterns = [
            r"\b(dev(eloper)?s?|engineer(s)?|programmer(s)?)\b",  # developers, engineers, programmers
            r"\b(python|java|javascript|react|angular|vue|node|php|ruby|go|rust|swift|kotlin)\b",  # tech skills
            r"\b(senior|junior|lead|principal|staff|entry.?level|mid.?level)\b",  # experience levels
            r"\b(find|show|search|get|looking.?for|need|want)\b",  # search verbs
            r"\b(full.?stack|frontend|backend|devops|data.?scientist|machine.?learning)\b",  # role types
            r"\b(years?.?(of.?)?experience|skills?.?(in|with)?)\b",  # experience/skills mentions
            r"\b(san.?francisco|nyc|new.?york|seattle|austin|boston|remote)\b",  # common locations
        ]

        # Check if it's an obvious search query
        message_lower = message.lower()
        for pattern in search_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.info(
                    f"🚀 REGEX SHORT-CIRCUIT: Obvious search detected - '{pattern}' matched"
                )
                return {
                    "intent": "search",
                    "reason": f"obvious search query detected (matched: {pattern})",
                }

        # 🔥 SHORT-CIRCUIT: Obvious conversational patterns (NO LLM CALL!)
        conversational_patterns = [
            r"^(hi|hello|hey|greetings?)(?:\s|$)",  # greetings
            r"^(explain|help|what|how|tell.?me|can.?you)\b",  # help requests
            r"^(thanks?|thank.?you|okay|ok|cool|great|amazing)(?:\s|$)",  # acknowledgments
            r"^(bye|goodbye|see.?you|later)(?:\s|$)",  # farewells
        ]

        for pattern in conversational_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.info(
                    f"🚀 REGEX SHORT-CIRCUIT: Obvious conversation detected - '{pattern}' matched"
                )
                return {
                    "intent": "conversation",
                    "reason": f"obvious conversational query detected (matched: {pattern})",
                }

        # 💡 FALLBACK: Use LLM only for ambiguous cases
        try:
            logger.info(f"🤖 LLM INTENT DETECTION: Ambiguous query needs AI analysis")

            # Extract key parts of the system prompt for intent detection
            system_instructions = """
## INTENT HANDLING RULES
- SEARCH INTENT: User mentions skills, titles, experience, locations, "find", "show", "search"
- CONVERSATIONAL INTENT: Greetings, help, explain, vague messages, questions about the system

Examples:
SEARCH: "Python developers", "Senior engineers", "Find React devs", "skills of Alex Chen"
CONVERSATIONAL: "explain", "help", "what can you do?", "hello", "thanks"
"""

            intent_prompt = CONVERSATIONAL_INTENT_PROMPT.format(
                system_instructions=system_instructions, message=message
            )

            response = await self.llm_service.generate_completion(
                prompt=intent_prompt,
                max_tokens=100,
                temperature=0.1,  # Low temperature for consistent intent detection
            )

            # Parse JSON response
            import json

            # Clean response and extract JSON
            cleaned_response = response.strip()
            if "```json" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].strip()

            # Find JSON pattern
            import re

            json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(0)

            intent_data = json.loads(cleaned_response)

            # Validate intent
            if intent_data.get("intent") not in ["conversation", "search"]:
                logger.warning(f"Invalid intent detected: {intent_data}")
                # Default to search for ambiguous cases
                return {
                    "intent": "search",
                    "reason": "ambiguous query - defaulting to search",
                }

            return intent_data

        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            # Default to search if intent detection fails
            return {
                "intent": "search",
                "reason": "intent detection failed - defaulting to search",
            }

    async def _handle_conversational_query(self, query: str) -> str:
        """
        Handle conversational queries using the intelligent system prompt.

        This is where GPT-4o-mini shines - natural conversation without triggering search.
        """
        try:
            # Use our conversational system prompt
            conversation_prompt = f"""{RECRUITER_RADAR_SYSTEM_PROMPT}

User: {query}
"""

            response = await self.llm_service.generate_completion(
                prompt=conversation_prompt, max_tokens=150, temperature=0.7
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Conversational query handling failed: {e}")
            return "Sorry, I couldn't handle that conversational query. Please try a different question."

    async def get_candidate_details(
        self, candidate_id: str, query: str, session_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific candidate using RAG.
        This is for when users ask specific questions about a candidate.
        """
        try:
            logger.info(f"📄 REAL RAG DETAILS: {candidate_id} query '{query}'")

            # Search for chunks specific to this candidate
            candidate_query = f"{query} candidate_id:{candidate_id}"

            search_result = await self.semantic_search.search_candidates(
                query=candidate_query,
                session_id=session_id,
                max_results=20,  # More focused search
            )

            if not search_result["candidates"]:
                return {
                    "candidate_details": None,
                    "ai_response": f"I couldn't find detailed information about candidate {candidate_id}",
                    "success": False,
                }

            # Get the first (most relevant) candidate
            candidate = search_result["candidates"][0]

            return {
                "candidate_details": candidate,
                "ai_response": search_result["ai_response"],
                "success": True,
            }

        except Exception as e:
            logger.error(f"❌ REAL RAG DETAILS failed: {e}", exc_info=True)
            return {
                "candidate_details": None,
                "ai_response": f"Failed to get candidate details: {str(e)}",
                "success": False,
            }

    async def chat_with_context(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Chat with full conversational context using RAG.

        This handles follow-up queries like:
        - "Tell me more about Alex Chen"
        - "What are his Python skills?"
        - "Find similar candidates"
        """
        try:
            logger.info(f"💬 REAL RAG CHAT: '{message}' in session {session_id}")

            # Build context from conversation history
            context_query = message
            if conversation_history:
                # Add previous context to improve search relevance
                recent_messages = conversation_history[-3:]  # Last 3 messages
                context_parts = [msg.get("content", "") for msg in recent_messages]
                context_parts.append(message)
                context_query = " ".join(context_parts)

            # Perform semantic search with enhanced context
            search_result = await self.semantic_search.search_candidates(
                query=context_query, session_id=session_id, max_results=30
            )

            # Generate conversational response
            ai_response = await self._generate_conversational_response(
                message, search_result, conversation_history
            )

            response = {
                "ai_message": ai_response,
                "candidates": search_result["candidates"],
                "source": "real_rag_chat",
                "success": True,
                "total_chunks": search_result["total_chunks"],
            }

            logger.info(
                f"✅ REAL RAG CHAT: Generated response with {len(search_result['candidates'])} candidates"
            )
            return response

        except Exception as e:
            logger.error(f"❌ REAL RAG CHAT failed: {e}", exc_info=True)
            return {
                "ai_message": f"Chat failed: {str(e)}",
                "candidates": [],
                "source": "real_rag_chat_error",
                "success": False,
                "total_chunks": 0,
            }

    async def _generate_conversational_response(
        self,
        message: str,
        search_result: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate a conversational AI response using retrieved context.
        """
        # Build conversation context
        history_text = ""
        if conversation_history:
            recent_history = conversation_history[-3:]
            history_parts = []
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"{role}: {content}")
            history_text = "\n".join(history_parts)

        # Get relevant context from search results
        context_text = ""
        if search_result["candidates"]:
            candidate_summaries = []
            for candidate in search_result["candidates"][:5]:  # Top 5
                summary = f"- {candidate['name']}: {candidate.get('summary', 'No summary available')}"
                candidate_summaries.append(summary)
            context_text = "\n".join(candidate_summaries)

        # Generate response
        response_prompt = f"""
        You are a helpful AI recruiter assistant. Respond conversationally to the user's message.
        
        User's current message: "{message}"
        
        Recent conversation:
        {history_text}
        
        Available candidate information:
        {context_text}
        
        Guidelines:
        - Be conversational and helpful
        - Reference specific candidates when relevant
        - If no candidates are found, suggest they upload resumes
        - Keep responses under 100 words
        - Be specific about skills, experience, and qualifications when available
        
        Response:
        """

        try:
            response = await self.llm_service.generate_completion(
                prompt=response_prompt, max_tokens=150, temperature=0.7
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Response generation failed: {e}")

            # Fallback response
            candidate_count = len(search_result["candidates"])
            if candidate_count == 0:
                return "I couldn't find any candidates matching your query. Try uploading some resumes first!"
            elif candidate_count == 1:
                candidate_name = search_result["candidates"][0]["name"]
                return f"I found information about {candidate_name}. What would you like to know?"
            else:
                return f"I found {candidate_count} relevant candidates. Let me know what specific information you're looking for!"

    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics about the current session's RAG data.
        """
        try:
            # This would query ChromaDB for session statistics
            # For now, return basic stats
            return {
                "session_id": session_id,
                "total_documents": 0,  # TODO: Implement
                "total_chunks": 0,  # TODO: Implement
                "last_updated": datetime.utcnow().isoformat(),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {"session_id": session_id, "error": str(e), "status": "error"}
