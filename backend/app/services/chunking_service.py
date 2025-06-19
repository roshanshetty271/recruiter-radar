"""
Service for intelligently chunking resumes for optimal embedding generation.

This service breaks large resumes into manageable chunks that:
1. Fit within token limits for embedding models
2. Preserve semantic meaning
3. Enable better search results
"""

import re
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

from app.models.chunk_models import ChunkType, ChunkMetadata, ChunkedResumeResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Service for breaking resumes into searchable chunks.

    Supports multiple strategies:
    - simple_two_chunk: Split in half at paragraph boundary
    - semantic: Identify sections (future enhancement)
    """

    def __init__(self):
        """Initialize the chunking service with configuration."""
        self.chunk_strategy = settings.chunk_strategy
        self.max_chunks = settings.max_chunks_per_resume
        self.target_chunk_size = settings.chunk_size_chars
        self.max_embedding_chars = settings.embedding_text_limit

        logger.info(
            f"ChunkingService initialized - Strategy: {self.chunk_strategy}, "
            f"Max chunks: {self.max_chunks}, Target size: {self.target_chunk_size}"
        )

    async def chunk_resume(
        self, text: str, candidate_id: str, filename: str
    ) -> ChunkedResumeResult:
        """
        Chunk a resume based on the configured strategy.

        Args:
            text: Full resume text
            candidate_id: Unique ID for the candidate
            filename: Original filename for logging

        Returns:
            ChunkedResumeResult with chunks and metadata
        """
        start_time = datetime.utcnow()
        total_chars = len(text)

        logger.info(
            f"Chunking resume {filename} ({total_chars} chars) "
            f"using {self.chunk_strategy} strategy"
        )

        # Choose chunking strategy
        if total_chars <= self.max_embedding_chars:
            # Small resume - single chunk
            chunks = self._create_single_chunk(text, candidate_id)
        elif self.chunk_strategy == "simple_two_chunk":
            chunks = self._simple_two_chunk_strategy(text, candidate_id)
        else:
            # Default to simple strategy
            chunks = self._simple_two_chunk_strategy(text, candidate_id)

        # Ensure we don't exceed max chunks
        if len(chunks) > self.max_chunks:
            logger.warning(
                f"Chunking produced {len(chunks)} chunks, "
                f"limiting to {self.max_chunks}"
            )
            chunks = chunks[: self.max_chunks]

        # Mark the first chunk as primary (usually contains name/summary)
        if chunks:
            chunks[0]["metadata"]["is_primary"] = True

        processing_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Chunked {filename} into {len(chunks)} chunks "
            f"in {processing_time:.2f} seconds"
        )

        return ChunkedResumeResult(
            chunks=chunks,
            chunk_count=len(chunks),
            total_chars=total_chars,
            chunking_strategy=self.chunk_strategy,
            primary_chunk_index=0,
        )

    def _create_single_chunk(
        self, text: str, candidate_id: str
    ) -> List[Dict[str, Any]]:
        """Create a single chunk for small resumes."""
        chunk_id = f"{candidate_id}_chunk_0"

        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            parent_id=candidate_id,
            chunk_type=ChunkType.FULL,
            chunk_index=0,
            total_chunks=1,
            char_count=len(text),
            is_primary=True,
        )

        return [
            {"content": text, "metadata": metadata.model_dump(), "chunk_id": chunk_id}
        ]

    def _simple_two_chunk_strategy(
        self, text: str, candidate_id: str
    ) -> List[Dict[str, Any]]:
        """
        Simple strategy: Split resume into two roughly equal chunks.

        Tries to split at a natural boundary (paragraph or section).
        """
        chunks = []
        text_length = len(text)

        # Find a good split point near the middle
        target_split = text_length // 2

        # Look for paragraph breaks near the middle
        search_start = max(0, target_split - 500)
        search_end = min(text_length, target_split + 500)
        search_text = text[search_start:search_end]

        # Find the best split point (prefer double newline, then single)
        split_patterns = [
            "\n\n",  # Paragraph break
            "\n",  # Line break
            ". ",  # Sentence end
            " ",  # Word boundary
        ]

        best_split = None
        for pattern in split_patterns:
            splits = [m.start() for m in re.finditer(re.escape(pattern), search_text)]
            if splits:
                # Find split closest to middle
                middle = len(search_text) // 2
                best_in_pattern = min(splits, key=lambda x: abs(x - middle))
                best_split = search_start + best_in_pattern + len(pattern)
                break

        # Fallback to exact middle if no good split found
        if best_split is None:
            best_split = target_split

        # Create two chunks
        chunk1_text = text[:best_split].strip()
        chunk2_text = text[best_split:].strip()

        # Chunk 1 - Usually contains header, summary, early experience
        if chunk1_text:
            chunk1_id = f"{candidate_id}_chunk_0"
            metadata1 = ChunkMetadata(
                chunk_id=chunk1_id,
                parent_id=candidate_id,
                chunk_type=ChunkType.HEADER,  # First chunk likely has header
                chunk_index=0,
                total_chunks=2,
                char_count=len(chunk1_text),
                is_primary=True,
            )
            chunks.append(
                {
                    "content": chunk1_text,
                    "metadata": metadata1.model_dump(),
                    "chunk_id": chunk1_id,
                }
            )

        # Chunk 2 - Usually contains additional experience, education, skills
        if chunk2_text:
            chunk2_id = f"{candidate_id}_chunk_1"
            metadata2 = ChunkMetadata(
                chunk_id=chunk2_id,
                parent_id=candidate_id,
                chunk_type=ChunkType.MIXED,  # Second chunk is mixed content
                chunk_index=1,
                total_chunks=2,
                char_count=len(chunk2_text),
                is_primary=False,
            )
            chunks.append(
                {
                    "content": chunk2_text,
                    "metadata": metadata2.model_dump(),
                    "chunk_id": chunk2_id,
                }
            )

        logger.debug(
            f"Split resume into {len(chunks)} chunks: "
            f"[{len(chunk1_text)}, {len(chunk2_text)}] chars"
        )

        return chunks

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Rule of thumb: 1 token ≈ 4 characters for English text.
        """
        return len(text) // 4
