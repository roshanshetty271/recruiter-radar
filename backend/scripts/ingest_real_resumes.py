#!/usr/bin/env python3
"""
Ingest Real Resumes Script

Processes all PDF resumes from backend/test_files/ directory and creates
a realistic candidate database to replace the synthetic demo data.

This script:
1. Extracts text from all PDF resumes
2. Uses LLM to extract structured candidate data
3. Generates embeddings for each resume
4. Stores everything in ChromaDB for realistic demo experience
5. Creates a JSON backup of the extracted data

Usage:
    cd backend
    python scripts/ingest_real_resumes.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from app.services.chroma_connector import ChromaConnector

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RealResumeIngestor:
    """Processes real PDF resumes and creates a realistic candidate database."""

    def __init__(self):
        self.llm_service = LLMService()
        self.pdf_service = PDFService()
        self.chroma = ChromaConnector()
        self.test_files_dir = Path("test_files")
        self.output_file = Path("app/data/real_candidate_profiles.json")

        # Ensure directories exist
        self.test_files_dir.mkdir(exist_ok=True)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    async def extract_candidate_from_pdf(
        self, pdf_path: Path
    ) -> Optional[Dict[str, Any]]:
        """Extract structured candidate data from a single PDF resume."""
        try:
            logger.info(f"Processing: {pdf_path.name}")

            # Extract text from PDF
            with open(pdf_path, "rb") as file:
                pdf_text = await self.pdf_service.extract_text_from_pdf(file.read())

            if not pdf_text or len(pdf_text.strip()) < 100:
                logger.warning(f"Insufficient text extracted from {pdf_path.name}")
                return None

            # Use LLM to extract structured data
            extracted_data = await self.llm_service.extract_structured_resume_data(
                pdf_text
            )

            if not extracted_data:
                logger.warning(
                    f"Failed to extract structured data from {pdf_path.name}"
                )
                return None

            # Generate embedding for the full text
            embedding = await self.llm_service.get_embedding(pdf_text)

            # Create candidate profile
            candidate = {
                "id": f"real_{pdf_path.stem.lower().replace('-', '_')}",
                "name": extracted_data.name or "Unknown Candidate",
                "title": extracted_data.title or "Software Engineer",
                "location": extracted_data.location or "Remote",
                "summary_text": (
                    pdf_text[:1000] + "..." if len(pdf_text) > 1000 else pdf_text
                ),
                "skills": extracted_data.skills or ["Software Development"],
                "experience_years": extracted_data.experience_years or 0,
                "visa_status": "Unknown",
                "email": extracted_data.email,
                "phone": extracted_data.phone,
                "summary": extracted_data.summary,
                "source_file": pdf_path.name,
                "is_demo": True,  # Mark as demo data
                "embedding": embedding,
            }

            logger.info(
                f"✅ Extracted: {candidate['name']} - {candidate['title']} ({len(candidate['skills'])} skills)"
            )
            return candidate

        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            return None

    async def process_all_resumes(self) -> List[Dict[str, Any]]:
        """Process all PDF resumes in the test_files directory."""
        pdf_files = list(self.test_files_dir.glob("*.pdf"))

        # Filter out non-resume files (like the Amazon OA Questions)
        resume_files = [
            f
            for f in pdf_files
            if "resume" in f.name.lower() or "engineer" in f.name.lower()
        ]

        logger.info(f"Found {len(resume_files)} resume files to process")

        candidates = []
        for pdf_file in resume_files:
            candidate = await self.extract_candidate_from_pdf(pdf_file)
            if candidate:
                candidates.append(candidate)

        logger.info(f"Successfully processed {len(candidates)} candidates")
        return candidates

    def save_to_json(self, candidates: List[Dict[str, Any]]):
        """Save extracted candidates to JSON file (without embeddings for readability)."""
        # Create a clean version without embeddings for JSON storage
        clean_candidates = []
        for candidate in candidates:
            clean_candidate = {k: v for k, v in candidate.items() if k != "embedding"}
            clean_candidates.append(clean_candidate)

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(clean_candidates, f, indent=2, ensure_ascii=False)

        logger.info(
            f"💾 Saved {len(clean_candidates)} candidates to {self.output_file}"
        )

    async def store_in_chromadb(self, candidates: List[Dict[str, Any]]):
        """Store candidates in ChromaDB for search functionality."""
        logger.info("Storing candidates in ChromaDB...")

        # Clear existing demo data
        try:
            self.chroma.collection.delete(where={"is_demo": True})
            logger.info("Cleared existing demo data from ChromaDB")
        except Exception as e:
            logger.warning(f"Could not clear existing data: {e}")

        # Store new candidates
        for candidate in candidates:
            try:
                metadata = {
                    k: v
                    for k, v in candidate.items()
                    if k not in ["embedding", "summary_text"]
                }

                self.chroma.collection.add(
                    ids=[candidate["id"]],
                    embeddings=[candidate["embedding"]],
                    documents=[candidate["summary_text"]],
                    metadatas=[metadata],
                )

            except Exception as e:
                logger.error(f"Failed to store candidate {candidate['id']}: {e}")

        logger.info(f"✅ Stored {len(candidates)} candidates in ChromaDB")

    async def run(self):
        """Main execution method."""
        logger.info("🚀 Starting Real Resume Ingestion")
        logger.info(f"Looking for resumes in: {self.test_files_dir.absolute()}")

        # Check if test_files directory exists and has PDFs
        if not self.test_files_dir.exists():
            logger.error(f"Directory {self.test_files_dir} does not exist!")
            return

        pdf_files = list(self.test_files_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"No PDF files found in {self.test_files_dir}")
            return

        # Process all resumes
        candidates = await self.process_all_resumes()

        if not candidates:
            logger.error("No candidates were successfully processed!")
            return

        # Save to both JSON and ChromaDB
        self.save_to_json(candidates)
        await self.store_in_chromadb(candidates)

        # Print summary
        logger.info("=" * 60)
        logger.info("🎉 REAL RESUME INGESTION COMPLETE!")
        logger.info(f"📊 Processed: {len(candidates)} real candidates")
        logger.info(f"💾 JSON saved to: {self.output_file}")
        logger.info(f"🔍 ChromaDB updated with real data")
        logger.info("=" * 60)

        # Show candidate summary
        logger.info("\n📋 CANDIDATE SUMMARY:")
        for candidate in candidates[:10]:  # Show first 10
            logger.info(
                f"  • {candidate['name']} - {candidate['title']} ({candidate['experience_years']} years)"
            )

        if len(candidates) > 10:
            logger.info(f"  ... and {len(candidates) - 10} more candidates")


async def main():
    """Main entry point."""
    ingestor = RealResumeIngestor()
    await ingestor.run()


if __name__ == "__main__":
    asyncio.run(main())
