#!/usr/bin/env python3
"""
Direct Real Resume Ingestion

This script processes the real PDF resumes from test_files/ directory
and directly stores them in ChromaDB, bypassing the upload API to avoid
timeout issues. This creates realistic demo data for testing.

Usage:
    cd backend
    python scripts/ingest_real_resumes_direct.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.pdf_service import PDFService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.chroma_connector import ChromaConnector

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_resume_pdf(
    pdf_path: Path, llm_service: LLMService, rag_service: RAGService
) -> Dict[str, Any]:
    """Process a single resume PDF and return extracted data."""

    logger.info(f"📄 Processing: {pdf_path.name}")

    try:
        # Extract text from PDF
        with open(pdf_path, "rb") as file:
            file_content = file.read()

        pdf_service = PDFService()
        extraction_result = await pdf_service.extract_text_from_pdf(file_content)

        if not extraction_result.success:
            logger.warning(
                f"❌ PDF extraction failed for {pdf_path.name}: {extraction_result.error_message}"
            )
            return {
                "filename": pdf_path.name,
                "success": False,
                "error": extraction_result.error_message,
            }

        text = extraction_result.text

        # Generate embedding
        logger.info(f"🧠 Generating embedding for {pdf_path.name}")
        embedding = await llm_service.get_embedding(text)

        # Extract structured data using LLM
        logger.info(f"🔍 Extracting structured data for {pdf_path.name}")
        extracted_data = await llm_service.extract_structured_resume_data(text)

        if not extracted_data:
            logger.warning(f"❌ LLM extraction failed for {pdf_path.name}")
            # Create minimal data with defaults
            extracted_data = {
                "name": pdf_path.stem.replace("-", " ").title(),
                "title": "Software Engineer",
                "skills": ["Software Development"],
                "location": "Remote",
                "experience_years": 3,
                "email": None,
                "phone": None,
                "summary": f"Professional resume from {pdf_path.name}",
            }

        # Create candidate profile
        candidate_id = f"real_resume_{hash(pdf_path.name) % 100000}"

        # Store in ChromaDB
        logger.info(f"💾 Storing {pdf_path.name} in ChromaDB")

        # Create metadata for ChromaDB (handle both ExtractedResumeData object and dict)
        if hasattr(extracted_data, "name"):  # ExtractedResumeData object
            metadata = {
                "candidate_id": candidate_id,
                "session_id": "demo_real_resumes",
                "filename": pdf_path.name,
                "source": "real_resume",
                "name": extracted_data.name,
                "title": extracted_data.title,
                "skills": ",".join(extracted_data.skills),
                "location": extracted_data.location or "Unknown",
                "experience_years": extracted_data.experience_years,
                "email": extracted_data.email or "",
                "phone": extracted_data.phone or "",
                "summary": extracted_data.summary or "",
            }
        else:  # Dictionary (fallback case)
            metadata = {
                "candidate_id": candidate_id,
                "session_id": "demo_real_resumes",
                "filename": pdf_path.name,
                "source": "real_resume",
                "name": extracted_data.get("name", "Unknown"),
                "title": extracted_data.get("title", "Unknown Role"),
                "skills": ",".join(extracted_data.get("skills", [])),
                "location": extracted_data.get("location", "Unknown"),
                "experience_years": extracted_data.get("experience_years", 0),
                "email": extracted_data.get("email", ""),
                "phone": extracted_data.get("phone", ""),
                "summary": extracted_data.get("summary", ""),
            }

        # Store in ChromaDB
        try:
            await rag_service.add_candidate_to_collection(
                candidate_id=candidate_id,
                embedding=embedding,
                metadata=metadata,
                document_text=text,
            )
            success = True
        except Exception as e:
            logger.error(f"❌ Failed to store in ChromaDB: {e}")
            success = False

        if success:
            name = (
                extracted_data.name
                if hasattr(extracted_data, "name")
                else extracted_data.get("name", "Unknown")
            )
            logger.info(f"✅ Successfully processed {pdf_path.name} → {name}")
            return {
                "filename": pdf_path.name,
                "success": True,
                "candidate_id": candidate_id,
                "extracted_data": extracted_data,
            }
        else:
            logger.error(f"❌ Failed to store {pdf_path.name} in ChromaDB")
            return {
                "filename": pdf_path.name,
                "success": False,
                "error": "ChromaDB storage failed",
            }

    except Exception as e:
        logger.error(f"💥 Error processing {pdf_path.name}: {e}", exc_info=True)
        return {"filename": pdf_path.name, "success": False, "error": str(e)}


async def main():
    """Main execution function."""
    logger.info("🚀 Starting Direct Real Resume Ingestion")

    # Find resume files
    test_files_dir = Path("test_files")
    if not test_files_dir.exists():
        logger.error(f"Directory {test_files_dir} does not exist!")
        return

    # Get all resume PDF files
    pdf_files = list(test_files_dir.glob("*.pdf"))
    resume_files = [
        f
        for f in pdf_files
        if any(
            keyword in f.name.lower() for keyword in ["resume", "engineer", "developer"]
        )
        and "questions" not in f.name.lower()  # Filter out Amazon OA Questions
    ]

    if not resume_files:
        logger.error(f"No resume PDF files found in {test_files_dir}")
        return

    logger.info(f"📊 Found {len(resume_files)} resume files to process")

    # Initialize services
    logger.info("🔧 Initializing services...")

    try:
        llm_service = LLMService(settings)
        chroma_connector = ChromaConnector(settings)
        rag_service = RAGService(settings, chroma_connector)

        # Process all resumes
        results = []
        successful_count = 0

        for resume_file in resume_files:
            result = await process_resume_pdf(resume_file, llm_service, rag_service)
            results.append(result)

            if result["success"]:
                successful_count += 1

            # Small delay between processing
            await asyncio.sleep(0.5)

        # Save results to JSON file
        results_file = Path("real_resume_ingestion_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Print summary
        logger.info("=" * 60)
        logger.info("🎉 DIRECT REAL RESUME INGESTION COMPLETE!")
        logger.info(f"📊 Total files processed: {len(resume_files)}")
        logger.info(f"✅ Successful ingestions: {successful_count}")
        logger.info(f"❌ Failed ingestions: {len(resume_files) - successful_count}")
        logger.info(f"💾 Results saved to: {results_file.absolute()}")
        logger.info("=" * 60)

        # Show successful candidates
        if successful_count > 0:
            logger.info("\n🎯 SUCCESSFULLY INGESTED CANDIDATES:")
            for result in results:
                if result["success"]:
                    extracted = result.get("extracted_data", {})
                    if hasattr(extracted, "name"):  # ExtractedResumeData object
                        name = extracted.name
                        title = extracted.title
                        skills = extracted.skills[:3]
                    else:  # Dictionary
                        name = extracted.get("name", "Unknown")
                        title = extracted.get("title", "Unknown Role")
                        skills = extracted.get("skills", [])[:3]
                    logger.info(f"  ✅ {name} - {title} - Skills: {', '.join(skills)}")

            logger.info("\n🔍 HOW TO TEST WITH REAL DATA:")
            logger.info("1. Start your frontend and backend")
            logger.info(
                "2. Try searches like: 'senior engineers', 'Python developers', 'security engineers'"
            )
            logger.info("3. You should see real candidates from actual resumes!")
            logger.info("4. The data is much more realistic than synthetic candidates!")

        # Show failed ones
        failed_results = [r for r in results if not r["success"]]
        if failed_results:
            logger.info("\n❌ FAILED INGESTIONS:")
            for result in failed_results:
                logger.info(
                    f"  ❌ {result['filename']}: {result.get('error', 'Unknown error')}"
                )

    except Exception as e:
        logger.error(f"💥 Critical error during ingestion: {e}", exc_info=True)


if __name__ == "__main__":
    # Load and validate configuration
    try:
        from app.core.config import settings

        # This will validate all config including the OpenAI API key
        logger.info("✅ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file and ensure API_OPENAI_API_KEY is set")
        sys.exit(1)

    asyncio.run(main())
