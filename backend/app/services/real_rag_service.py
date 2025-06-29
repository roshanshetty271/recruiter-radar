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

# Removed expensive imports - no longer needed for keyword detection!
# import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity

from app.services.document_processor import DocumentProcessor
from app.services.semantic_search import SemanticSearchEngine
from app.services.llm_service import LLMService
from app.core.prompts import RECRUITER_RADAR_SYSTEM_PROMPT, CONVERSATIONAL_INTENT_PROMPT

logger = logging.getLogger(__name__)

# 🏎️ DEPRECATED EXAMPLES - No longer used with keyword detection!
# These used to generate 40+ expensive embeddings - now replaced with simple keywords
# SEARCH_INTENT_EXAMPLES = [...]
# CONVERSATION_INTENT_EXAMPLES = [...]


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
        # Removed expensive embedding storage - using keyword detection!
        logger.info(
            "🚀 REAL RAG SERVICE INITIALIZED - Lightning-fast keyword detection!"
        )

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

            # 🧠 STEP 1: SMART Intent Detection - Greetings vs Search
            intent_result = await self._detect_intent_smart(query)

            if intent_result["intent"] == "conversation":
                # 💬 Handle conversational queries (greetings, help, etc.)
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
        🚀 VECTOR-BASED INTENT DETECTION - No more regex trench!

        Uses cosine similarity with threshold 0.25 against pre-computed intent examples.

        Returns:
            Dict with 'intent' ("conversation" or "search") and 'reason'
        """
        # Delegate to the new vector-based detection
        return await self._detect_intent_vector(message)

    async def _handle_conversational_query(self, query: str) -> str:
        """
        Handle conversational queries with smart, contextual responses.

        For greetings and help requests, provide immediate helpful responses
        without needing an LLM call for simple cases.
        """
        query_lower = query.strip().lower()

        # 👋 GREETING RESPONSES
        greetings = [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        if any(greeting in query_lower for greeting in greetings):
            return (
                "Hello! I'm your AI recruiting assistant. I can help you find the perfect candidates "
                "by searching through resumes and profiles. Try asking me something like:\n\n"
                "• 'Find Python developers'\n"
                "• 'Senior engineers with 5+ years experience'\n"
                "• 'React developers in San Francisco'\n"
                "• 'Data scientists with machine learning experience'\n\n"
                "What kind of candidate are you looking for today?"
            )

        # ❓ HELP RESPONSES
        help_words = [
            "help",
            "what can you do",
            "how does this work",
            "explain",
            "guide",
        ]
        if any(help_word in query_lower for help_word in help_words):
            return (
                "I'm RecruiterRadar, your AI-powered recruiting assistant! Here's what I can do:\n\n"
                "🔍 **Search Candidates**: Use natural language to find candidates\n"
                "   Examples: 'Python developers', 'senior engineers', 'DevOps with AWS'\n\n"
                "📊 **Smart Analysis**: I analyze skills, experience, and match quality\n\n"
                "💬 **Natural Conversation**: Ask follow-up questions about candidates\n\n"
                "Just type what you're looking for and I'll find the best matches!"
            )

        # 🙏 THANKS RESPONSES
        thanks_words = ["thank", "thanks", "appreciate"]
        if any(thanks in query_lower for thanks in thanks_words):
            return "You're welcome! Feel free to ask me to find more candidates anytime. Happy recruiting! 🚀"

        # 👋 GOODBYE RESPONSES
        goodbye_words = ["bye", "goodbye", "see you"]
        if any(goodbye in query_lower for goodbye in goodbye_words):
            return "Goodbye! Come back anytime you need help finding great candidates. Good luck with your recruiting! 👋"

        # 🤖 FALLBACK - Use LLM for complex conversational queries
        try:
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

    async def _initialize_intent_embeddings(self):
        """
        DEPRECATED: No longer needed - using lightning-fast keyword detection instead!
        This method used to generate 40+ embeddings and take 20+ seconds.
        """
        logger.info(
            "🏎️ SKIPPING expensive embedding initialization - using keyword detection!"
        )
        # No-op - keyword detection doesn't need any initialization
        pass

    async def _detect_intent_smart(self, message: str) -> Dict[str, str]:
        """
        🧠 SMART Intent Detection - Properly distinguish greetings from searches

        This fixes the "hi" -> technical analysis bug!
        """
        message_lower = message.strip().lower()

        # 👋 OBVIOUS CONVERSATIONAL PATTERNS (these should NEVER be searches)
        obvious_greetings = [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "what's up",
            "how are you",
            "greetings",
            "yo",
        ]

        obvious_help = [
            "help",
            "how does this work",
            "what can you do",
            "explain",
            "tutorial",
            "guide",
            "instructions",
            "how to",
            "what is this",
            "about",
        ]

        obvious_conversation = [
            "thank you",
            "thanks",
            "bye",
            "goodbye",
            "see you",
            "cool",
            "awesome",
            "nice",
            "great",
            "ok",
            "okay",
            "got it",
            "understood",
        ]

        # Check for obvious conversational intents first
        if any(greeting in message_lower for greeting in obvious_greetings):
            return {
                "intent": "conversation",
                "reason": f"greeting detected: '{message}'",
            }

        if any(help_word in message_lower for help_word in obvious_help):
            return {
                "intent": "conversation",
                "reason": f"help request detected: '{message}'",
            }

        if any(conv in message_lower for conv in obvious_conversation):
            return {
                "intent": "conversation",
                "reason": f"conversational response detected: '{message}'",
            }

        # 🔍 OBVIOUS SEARCH PATTERNS (these should ALWAYS be searches)
        search_indicators = [
            # Skills
            "python",
            "javascript",
            "java",
            "react",
            "angular",
            "vue",
            "node",
            "aws",
            "azure",
            "docker",
            "kubernetes",
            "sql",
            "ai",
            "machine learning",
            # Roles
            "developer",
            "engineer",
            "architect",
            "manager",
            "senior",
            "junior",
            "lead",
            "principal",
            "staff",
            "frontend",
            "backend",
            "fullstack",
            # Actions
            "find",
            "show",
            "search",
            "get",
            "looking for",
            "need",
            "want",
            "candidates",
            "who has",
            "with experience",
            "years of",
        ]

        # Count search indicators
        search_matches = sum(
            1 for indicator in search_indicators if indicator in message_lower
        )

        if search_matches >= 1:
            return {
                "intent": "search",
                "reason": f"search indicators found: {search_matches} matches",
            }

        # 🤔 AMBIGUOUS CASES - Use message length and structure as hints
        word_count = len(message.split())

        if word_count <= 2:
            # Very short messages are likely conversational
            return {
                "intent": "conversation",
                "reason": f"short message ({word_count} words) likely conversational",
            }
        elif word_count >= 5:
            # Longer messages are more likely to be searches
            return {
                "intent": "search",
                "reason": f"longer message ({word_count} words) likely search query",
            }
        else:
            # Default for medium messages - bias toward search for recruiters
            return {
                "intent": "search",
                "reason": f"medium message ({word_count} words) defaulting to search",
            }

    async def _detect_intent_vector(self, message: str) -> Dict[str, str]:
        """
        🏎️ LIGHTNING-FAST KEYWORD INTENT DETECTION - No more 40-embedding hamster wheel!

        Uses simple keyword matching - takes microseconds instead of 20+ seconds.

        Returns:
            Dict with 'intent' ("conversation" or "search") and 'reason'
        """
        try:
            message_lower = message.lower()

            # 🔍 SEARCH INTENT KEYWORDS - What recruiters actually type
            search_keywords = [
                # Skills & Technologies
                "python",
                "javascript",
                "java",
                "react",
                "angular",
                "vue",
                "node",
                "typescript",
                "golang",
                "rust",
                "c++",
                "c#",
                "php",
                "ruby",
                "swift",
                "aws",
                "azure",
                "gcp",
                "docker",
                "kubernetes",
                "sql",
                "nosql",
                "machine learning",
                "ai",
                "data science",
                "blockchain",
                "devops",
                # Job Titles & Levels
                "developer",
                "engineer",
                "architect",
                "manager",
                "lead",
                "senior",
                "junior",
                "principal",
                "staff",
                "director",
                "analyst",
                "scientist",
                "frontend",
                "backend",
                "fullstack",
                "full stack",
                "mobile",
                "web",
                # Experience & Qualifications
                "experience",
                "years",
                "exp",
                "background",
                "skills",
                "expertise",
                "degree",
                "certification",
                "portfolio",
                "projects",
                # Action Words
                "find",
                "show",
                "search",
                "get",
                "candidates",
                "who has",
                "with",
                "looking for",
                "need",
                "want",
                "hire",
                "recruit",
            ]

            # 💬 CONVERSATION INTENT KEYWORDS - Help, greetings, system questions
            conversation_keywords = [
                "hello",
                "hi",
                "hey",
                "greetings",
                "good morning",
                "good afternoon",
                "help",
                "how",
                "what",
                "explain",
                "tell me",
                "can you",
                "do you",
                "tutorial",
                "guide",
                "instructions",
                "features",
                "capabilities",
                "thank",
                "thanks",
                "bye",
                "goodbye",
                "see you",
                "appreciate",
                "system",
                "interface",
                "platform",
                "tool",
                "app",
                "work",
                "works",
            ]

            # Count keyword matches
            search_matches = sum(
                1 for keyword in search_keywords if keyword in message_lower
            )
            conversation_matches = sum(
                1 for keyword in conversation_keywords if keyword in message_lower
            )

            logger.info(
                f"⚡ Keyword matches - Search: {search_matches}, Conversation: {conversation_matches}"
            )

            # Decision logic - bias toward search for recruiters
            if search_matches > conversation_matches:
                return {
                    "intent": "search",
                    "reason": f"keyword detection: {search_matches} search terms found",
                }
            elif conversation_matches > search_matches and conversation_matches >= 2:
                return {
                    "intent": "conversation",
                    "reason": f"keyword detection: {conversation_matches} conversation terms found",
                }
            else:
                # Default to search - this is a recruiter tool!
                return {
                    "intent": "search",
                    "reason": "keyword detection: defaulting to search (recruiter-focused)",
                }

        except Exception as e:
            logger.error(f"❌ Keyword intent detection failed: {e}")
            # Safe fallback
            return {
                "intent": "search",
                "reason": "error fallback - defaulting to search",
            }

    async def _detect_intent_llm_fallback(self, message: str) -> Dict[str, str]:
        """
        Fallback LLM-based intent detection for ambiguous cases.
        Only used when vector similarity is unclear.
        """
        try:
            logger.info(f"🤖 LLM INTENT FALLBACK for ambiguous query: '{message}'")

            system_instructions = """
## INTENT DETECTION RULES
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
                logger.warning(f"Invalid LLM intent: {intent_data}")
                return {
                    "intent": "search",
                    "reason": "LLM fallback - invalid response, defaulting to search",
                }

            # Add fallback indicator
            intent_data["reason"] = (
                f"LLM fallback: {intent_data.get('reason', 'analysis')}"
            )
            return intent_data

        except Exception as e:
            logger.error(f"❌ LLM intent fallback failed: {e}")
            return {
                "intent": "search",
                "reason": "LLM fallback failed - defaulting to search",
            }

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
