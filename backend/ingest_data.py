# File: backend/ingest_data.py

# --------------------------------------------------------------------------
# 1. IMPORTS & INITIAL SETUP
# --------------------------------------------------------------------------
import os
from dotenv import load_dotenv

# REFINED .env loading logic:
# Try loading .env from the directory of ingest_data.py (backend/) first.
# If not found, try loading from the parent directory (project root).

# Path to .env in the same directory as ingest_data.py (backend/)
env_in_backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Path to .env in the project root directory (one level up from backend/)
project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_in_project_root = os.path.join(project_root_dir, ".env")

chosen_dotenv_path = None
if os.path.exists(env_in_backend_dir):
    chosen_dotenv_path = env_in_backend_dir
elif os.path.exists(env_in_project_root):
    chosen_dotenv_path = env_in_project_root

if chosen_dotenv_path:
    # Use logger if available, otherwise print for early diagnostics
    # logger.info(f"Attempting to load environment variables from: {chosen_dotenv_path}")
    print(f"INFO: Attempting to load environment variables from: {chosen_dotenv_path}")
    load_dotenv(dotenv_path=chosen_dotenv_path, override=True)
else:
    # logger.warning(" .env file not found in backend/ or project root. Proceeding with existing system environment variables.")
    print(
        "WARNING: .env file not found in backend/ or project root. "
        "The script will rely on globally set environment variables if any."
    )

import asyncio
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from pydantic import ValidationError
from fastapi import (
    HTTPException,
)  # Keep for potential direct use if needed, though services should handle

# Project-specific imports
from app.core.config import settings
from app.models.candidate import CandidateProfile

# Import actual custom exceptions from service modules
from app.services.llm_service import (
    LLMService,
    LLMServiceError,
    EmbeddingGenerationError,
    OpenAIConfigError,
)
from app.services.rag_service import (
    RAGService,
    RAGServiceError,
    CollectionManagementError,
    DocumentStorageError,
)

# --------------------------------------------------------------------------
# 2. LOGGING CONFIGURATION
# --------------------------------------------------------------------------
# Consistent logging setup using project settings
# Defensive access to settings.log_level in case it's not configured for some reason during early init
log_level_to_set = "INFO"
if hasattr(settings, "log_level") and isinstance(settings.log_level, str):
    log_level_to_set = settings.log_level.upper()

logging.basicConfig(
    level=log_level_to_set,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# 3. COMMAND-LINE ARGUMENT PARSER
# --------------------------------------------------------------------------
def parse_cli_args() -> argparse.Namespace:
    """Parses command-line arguments for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="RecruiterRadar MVP Data Ingestion Script"
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Completely reset the ChromaDB collection before ingesting data. This will delete all existing candidates.",
    )

    # Use candidate_data_full_path from settings as the default for --data-file
    default_data_file = "app/data/candidate_profiles.json"  # A sensible default
    if (
        hasattr(settings, "candidate_data_full_path")
        and settings.candidate_data_full_path
    ):
        default_data_file = str(settings.candidate_data_full_path)

    parser.add_argument(
        "--data-file",
        type=str,
        default=default_data_file,
        help=f"Path to the candidate data JSON file. Defaults to: {default_data_file}",
    )
    # Future consideration: parser.add_argument("--limit", type=int, help="Limit the number of candidates to process.")
    return parser.parse_args()


# --------------------------------------------------------------------------
# 4. DATA LOADING & VALIDATION FUNCTION
# --------------------------------------------------------------------------
def load_and_validate_candidates(file_path: Path) -> List[CandidateProfile]:
    """Loads candidate data from a JSON file and validates it against the CandidateProfile model."""
    logger.info(f"Attempting to load candidate profiles from: {file_path}")
    if not file_path.exists():
        logger.error(f"CRITICAL: Candidate data file not found at {file_path}")
        raise FileNotFoundError(f"Data file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data_list = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL: Failed to decode JSON from {file_path}. Error: {e}")
        raise

    valid_candidates: List[CandidateProfile] = []
    if not isinstance(raw_data_list, list):
        logger.error(
            f"CRITICAL: Expected a list of candidates in {file_path}, but got {type(raw_data_list)}."
        )
        raise TypeError(
            f"Data file {file_path} should contain a list of candidate objects."
        )

    for index, candidate_data in enumerate(raw_data_list):
        try:
            candidate = CandidateProfile.model_validate(candidate_data)  # Pydantic v2+
            valid_candidates.append(candidate)
        except ValidationError as e:
            candidate_id = candidate_data.get("id", f"unknown_at_index_{index}")
            logger.warning(
                f"Validation failed for candidate ID '{candidate_id}'. Errors: {e.errors()}. Skipping this candidate."
            )
        except Exception as e:
            candidate_id = candidate_data.get("id", f"unknown_at_index_{index}")
            logger.warning(
                f"An unexpected error occurred validating candidate ID '{candidate_id}'. Error: {e}. Skipping this candidate."
            )

    logger.info(
        f"Successfully loaded and validated {len(valid_candidates)} out of {len(raw_data_list)} candidate profiles."
    )
    return valid_candidates


# --------------------------------------------------------------------------
# 5. SINGLE CANDIDATE PROCESSING FUNCTION
# --------------------------------------------------------------------------
async def process_single_candidate(
    candidate: CandidateProfile, llm_service: LLMService, rag_service: RAGService
) -> bool:
    """
    Processes a single candidate: generates embedding and adds to RAG service.
    Returns True if successful, False otherwise.
    """
    logger.debug(f"Processing candidate ID: {candidate.id}, Name: {candidate.name}")

    if not candidate.raw_resume_text or not candidate.raw_resume_text.strip():
        logger.warning(
            f"Candidate ID '{candidate.id}' ({candidate.name}) has empty or whitespace-only 'raw_resume_text'. Skipping embedding and storage."
        )
        return False

    try:
        # Step 5a: Generate Embedding
        logger.debug(f"Generating embedding for candidate ID: {candidate.id}...")
        embedding = await llm_service.get_embedding(candidate.raw_resume_text)
        embedding_len = len(embedding) if embedding else "N/A"
        logger.debug(
            f"Embedding generated successfully for candidate ID: {candidate.id} (Dimension: {embedding_len})"
        )

        if not embedding:  # Should ideally be handled by LLMService raising an error
            logger.error(
                f"Embedding generation returned None or empty for candidate ID: {candidate.id}"
            )
            return False

        # Step 5b: Prepare Metadata (with email normalization)
        normalized_email = candidate.email.lower().strip() if candidate.email else None

        metadata = {
            "candidate_id": str(candidate.id),
            "name": str(candidate.name or ""),
            "email": normalized_email,  # Use normalized email
            "skills": ", ".join(candidate.skills) if candidate.skills else "",
            "experience_years": (
                int(candidate.experience_years)
                if candidate.experience_years is not None
                else 0
            ),
            "visa_status": str(candidate.visa_status or "Not Specified"),
            "location": str(candidate.location or "Not Specified"),
            "github_url": str(candidate.github_url or ""),
            "linkedin_url": str(candidate.linkedin_url or ""),
        }
        logger.debug(f"Prepared metadata for candidate ID: {candidate.id}: {metadata}")

        # Step 5c: Add to RAG Service Collection
        await rag_service.add_candidate_to_collection(
            candidate_id=candidate.id,
            embedding=embedding,
            metadata=metadata,
            document_text=candidate.raw_resume_text,
        )
        logger.info(
            f"✅ Successfully processed and stored candidate ID: {candidate.id} ({candidate.name})"
        )
        return True

    except LLMServiceError as e:
        logger.error(
            f"LLM Service error while processing candidate ID '{candidate.id}': {e}"
        )
    except RAGServiceError as e:
        logger.error(
            f"RAG Service error while processing candidate ID '{candidate.id}': {e}"
        )
    except HTTPException as e:
        logger.error(
            f"HTTP Exception (likely from service) while processing candidate ID '{candidate.id}': {e.detail}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error processing candidate ID '{candidate.id}': {e}",
            exc_info=True,
        )

    return False


# --------------------------------------------------------------------------
# 6. MAIN ORCHESTRATION FUNCTION
# --------------------------------------------------------------------------
async def run_ingestion_pipeline():
    """Main function to run the data ingestion pipeline."""
    args = parse_cli_args()
    logger.info("🚀 RecruiterRadar Data Ingestion Pipeline Initializing...")
    logger.info(
        f"CLI Arguments: Reset DB = {args.reset_db}, Data File = {args.data_file}"
    )

    # Step 6a: Initialize Services
    # NOTE: Service initialization was previously incorrect.
    # It needs to use the DI-like pattern or ensure settings are fully resolved.
    # The Pydantic error likely happens before this point, during `from app.core.config import settings`.
    # However, ensuring services are initialized correctly after settings are loaded is also key.

    llm_service: LLMService
    rag_service: RAGService

    try:
        logger.info("Initializing LLMService...")
        llm_service = LLMService(settings_obj=settings)  # Corrected: pass settings_obj
        logger.info("LLMService initialized.")

        logger.info("Initializing RAGService (which includes ChromaConnector)...")
        # RAGService's get_rag_service() equivalent for standalone script:
        # 1. Create ChromaConnector
        from app.services.chroma_connector import (
            ChromaConnector,
        )  # Import here if not at top

        try:
            connector = ChromaConnector(settings_obj=settings)
        except Exception as e_conn:
            logger.critical(
                f"CRITICAL: Failed to initialize ChromaConnector. Error: {e_conn}",
                exc_info=True,
            )
            return

        # 2. Create RAGService with the connector
        try:
            rag_service = RAGService(settings_obj=settings, connector=connector)
        except Exception as e_rag:
            logger.critical(
                f"CRITICAL: Failed to initialize RAGService with ChromaConnector. Error: {e_rag}",
                exc_info=True,
            )
            return

        logger.info("RAGService (and ChromaConnector) initialized.")

    except OpenAIConfigError as e:  # More specific error from LLMService init
        logger.critical(
            f"CRITICAL: OpenAI Configuration Error for LLMService. Aborting. Error: {e}",
            exc_info=True,
        )
        return
    except Exception as e:  # Catch-all for other service init issues
        logger.critical(
            f"CRITICAL: Failed to initialize core services. Aborting. Error: {e}",
            exc_info=True,
        )
        return

    # Step 6b: Handle DB Reset
    if args.reset_db:
        logger.warning(
            f"⚠️ ATTENTION: --reset-db flag is set. Attempting to reset ChromaDB collection: '{settings.chroma_collection_name}'..."
        )
        try:
            await rag_service.reset_collection()
            logger.info(
                f"ChromaDB collection '{settings.chroma_collection_name}' reset successfully."
            )
        except CollectionManagementError as e:
            logger.error(
                f"Failed to reset ChromaDB collection. Proceeding with existing data (if any). Error: {e}"
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during DB reset. Proceeding cautiously. Error: {e}",
                exc_info=True,
            )

    # Step 6c: Load and Validate Candidate Data
    try:
        candidate_profiles = load_and_validate_candidates(Path(args.data_file))
        if not candidate_profiles:
            logger.warning(
                "No valid candidate profiles loaded. Check data file and validation logs. Exiting."
            )
            return
    except FileNotFoundError:
        logger.error(f"Candidate data file not found at '{args.data_file}'. Exiting.")
        return
    except Exception as e:
        logger.error(
            f"Failed to load or validate candidate data from '{args.data_file}'. Error: {e}. Exiting.",
            exc_info=True,
        )
        return

    # Step 6d: Process Candidates
    logger.info(
        f"Starting processing of {len(candidate_profiles)} candidate profiles..."
    )
    successful_ingestions = 0
    failed_ingestions = 0

    # Sequential processing for MVP to keep it simple and avoid overwhelming services
    # For higher throughput, asyncio.gather could be used with a semaphore for concurrency control.
    for i, candidate in enumerate(candidate_profiles):
        logger.info(
            f"Processing candidate {i+1}/{len(candidate_profiles)}: ID '{candidate.id}'..."
        )
        try:
            if await process_single_candidate(candidate, llm_service, rag_service):
                successful_ingestions += 1
            else:
                failed_ingestions += 1
        except Exception as e:  # Catch unexpected errors from process_single_candidate
            logger.error(
                f"Unhandled exception processing candidate ID '{candidate.id}'. Error: {e}",
                exc_info=True,
            )
            failed_ingestions += 1

        # Optional: Add a small delay to be kind to external APIs if processing very fast
        # await asyncio.sleep(0.1)

    # Step 6e: Log Summary
    logger.info("🏁 RecruiterRadar Data Ingestion Pipeline Finished.")
    logger.info(f"Total candidates processed: {len(candidate_profiles)}")
    logger.info(f"Successfully ingested: {successful_ingestions}")
    logger.info(f"Failed to ingest: {failed_ingestions}")
    if failed_ingestions > 0:
        logger.warning("Some candidates failed to ingest. Check logs for details.")


# --------------------------------------------------------------------------
# 7. SCRIPT EXECUTION ENTRY POINT
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Ensure event loop is handled correctly for async operations
    # For Python 3.7+
    asyncio.run(run_ingestion_pipeline())

    # Older Python versions might need:
    # loop = asyncio.get_event_loop()
    # try:
    #     loop.run_until_complete(run_ingestion_pipeline())
    # finally:
    #     loop.close()
