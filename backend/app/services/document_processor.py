"""
Real RAG Document Processor

Handles PDF ingestion, intelligent chunking, and embedding generation.
NO MORE HARDCODED METADATA FILTERING - Pure semantic search!
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import re
import uuid
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from app.services.chroma_connector import ChromaConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    REAL RAG Document Processor

    - Intelligently chunks resume documents
    - Generates semantic embeddings
    - Stores in vector database for similarity search
    - NO hardcoded metadata filtering!
    """

    def __init__(self):
        self.llm_service = LLMService(settings)
        self.pdf_service = PDFService()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks for better granularity
            chunk_overlap=50,  # Some overlap to maintain context
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

    async def process_resume(
        self, file_bytes: bytes, filename: str, session_id: str
    ) -> Dict[str, Any]:
        """
        Process a resume PDF with REAL RAG:
        1. Extract text
        2. Intelligent chunking
        3. Generate embeddings
        4. Store in vector DB

        Returns processing results with chunk count and metadata.
        """
        try:
            logger.info(f"🔥 REAL RAG: Processing {filename} for session {session_id}")

            # 1. Extract raw text
            raw_text = await self.pdf_service.extract_text_from_pdf(file_bytes)
            if not raw_text or len(raw_text.strip()) < 50:
                return {
                    "status": "failed",
                    "error": "Could not extract meaningful text from PDF",
                    "chunks_created": 0,
                }

            # 2. Extract basic candidate info with LLM (minimal metadata)
            candidate_info = await self._extract_basic_info(raw_text, filename)

            # 3. Intelligent document chunking
            chunks = await self._chunk_document(raw_text, candidate_info)

            # 4. Generate embeddings and store
            chunk_count = await self._embed_and_store_chunks(
                chunks, candidate_info, session_id, filename
            )

            logger.info(
                f"✅ REAL RAG: Processed {filename} - {chunk_count} chunks created"
            )

            return {
                "status": "success",
                "candidate_name": candidate_info.get("name", "Unknown"),
                "chunks_created": chunk_count,
                "candidate_id": candidate_info["candidate_id"],
            }

        except Exception as e:
            logger.error(
                f"❌ REAL RAG: Failed to process {filename}: {e}", exc_info=True
            )
            return {"status": "failed", "error": str(e), "chunks_created": 0}

    async def _extract_basic_info(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Extract minimal candidate info using LLM - just enough for identification.
        NO MORE HARDCODED SKILL LISTS!
        """
        prompt = f"""
        Extract basic information from this resume text. Return ONLY a JSON object.
        
        {{
            "name": "Full candidate name",
            "title": "Current or most recent job title", 
            "email": "email if found, null otherwise",
            "location": "location if found, null otherwise"
        }}
        
        Resume text:
        {text[:2000]}  # First 2000 chars for identification
        
        JSON:
        """

        try:
            # Use LLM to extract basic info
            response = await self.llm_service.generate_completion(
                prompt=prompt, max_tokens=200, temperature=0.1
            )

            # Parse JSON response
            info = json.loads(response.strip())

            # Add unique candidate ID
            info["candidate_id"] = f"cand_{uuid.uuid4().hex[:12]}"
            info["processed_at"] = datetime.utcnow().isoformat()
            info["filename"] = filename

            return info

        except Exception as e:
            logger.warning(f"LLM extraction failed for {filename}: {e}")
            # Fallback to basic info
            return {
                "candidate_id": f"cand_{uuid.uuid4().hex[:12]}",
                "name": filename.replace(".pdf", "").replace("_", " ").title(),
                "title": "Unknown",
                "email": None,
                "location": None,
                "processed_at": datetime.utcnow().isoformat(),
                "filename": filename,
            }

    async def _chunk_document(self, text: str, candidate_info: Dict) -> List[Document]:
        """
        Intelligently chunk the resume into semantic pieces.
        Each chunk will be embedded separately for granular search.
        """
        # Create langchain documents for better chunking
        doc = Document(
            page_content=text,
            metadata={
                "candidate_id": candidate_info["candidate_id"],
                "candidate_name": candidate_info["name"],
                "filename": candidate_info["filename"],
                "type": "resume",
            },
        )

        # Use recursive character splitter for intelligent chunking
        chunks = self.text_splitter.split_documents([doc])

        # Add chunk-specific metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "chunk_id": f"{candidate_info['candidate_id']}_chunk_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )

        logger.info(
            f"📄 Chunked {candidate_info['filename']} into {len(chunks)} pieces"
        )
        return chunks

    async def _embed_and_store_chunks(
        self,
        chunks: List[Document],
        candidate_info: Dict,
        session_id: str,
        filename: str,
    ) -> int:
        """
        Generate embeddings for each chunk and store in ChromaDB.
        This enables true semantic search!
        """
        if not chunks:
            return 0

        try:
            # Initialize ChromaDB connection
            chroma_connector = ChromaConnector(settings_obj=settings)
            session_collection = chroma_connector.get_or_create_session_collection(
                session_id
            )

            # Prepare batch data for ChromaDB
            ids = []
            embeddings = []
            metadatas = []
            documents = []

            for chunk in chunks:
                # Generate embedding for this chunk
                embedding = await self.llm_service.get_embedding(chunk.page_content)

                ids.append(chunk.metadata["chunk_id"])
                embeddings.append(embedding)
                documents.append(chunk.page_content)
                metadatas.append(
                    {
                        **chunk.metadata,
                        # Store minimal metadata - let embeddings handle semantic search
                        "candidate_name": candidate_info["name"],
                        "filename": filename,
                        "session_id": session_id,
                    }
                )

            # Batch insert into ChromaDB
            await asyncio.to_thread(
                session_collection.add,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(
                f"🚀 Stored {len(chunks)} embedded chunks for {candidate_info['name']}"
            )
            return len(chunks)

        except Exception as e:
            logger.error(f"Failed to embed/store chunks: {e}", exc_info=True)
            raise
