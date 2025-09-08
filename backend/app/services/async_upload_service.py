"""
Async Upload Service for Resume Processing

This service provides immediate user response while processing resumes in the background.
Key features:
- Immediate task ID return to user
- Background processing with progress tracking
- Real-time status updates
- Error recovery and retry logic
"""

import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import structlog
from fastapi import BackgroundTasks

from ..models.extraction_models import ExtractedResumeData
from ..models.candidate import CandidateProfile
from ..services.optimized_resume_parser import OptimizedResumeParser
from ..services.llm_service import LLMService
from ..services.rag_service import RAGService

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileStatus(str, Enum):
    """Individual file processing status."""

    PENDING = "pending"
    EXTRACTING_TEXT = "extracting_text"
    AI_PROCESSING = "ai_processing"
    GENERATING_EMBEDDING = "generating_embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileTask:
    """Individual file processing task."""

    file_id: str
    filename: str
    file_size: int
    status: FileStatus = FileStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    extracted_data: Optional[ExtractedResumeData] = None
    candidate_id: Optional[str] = None
    processing_time_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()

        # Include confidence and basic extraction info (but remove full extracted_data)
        if self.extracted_data:
            data["extracted_name"] = self.extracted_data.name
            data["extracted_email"] = self.extracted_data.email
            data["extraction_confidence"] = self.extracted_data.extraction_confidence
            data["extracted_skills"] = self.extracted_data.technical_skills[
                :5
            ]  # First 5 skills
            data["total_skills_count"] = len(self.extracted_data.technical_skills)

        # Remove full extracted_data from response (too large)
        data.pop("extracted_data", None)
        return data


@dataclass
class UploadTask:
    """Batch upload task with multiple files."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    files: List[FileTask] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.files is None:
            self.files = []

    @property
    def progress(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files + self.failed_files) / self.total_files * 100

    @property
    def processing_time_seconds(self) -> Optional[float]:
        """Calculate total processing time."""
        if not self.start_time:
            return None
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "progress": self.progress,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time_seconds": self.processing_time_seconds,
            "error": self.error,
            "files": [file_task.to_dict() for file_task in self.files],
        }


class AsyncUploadService:
    """Service for handling async resume uploads with real-time progress tracking."""

    # Class-level task storage (shared across all instances)
    _shared_tasks: Dict[str, UploadTask] = {}

    def __init__(self, llm_service: LLMService, rag_service: RAGService):
        """Initialize the async upload service."""
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.resume_parser = OptimizedResumeParser(llm_service)

        # Use shared task storage
        self.tasks = self._shared_tasks

        # Cleanup completed tasks after 1 hour
        self.task_cleanup_interval = timedelta(hours=1)

        logger.info("AsyncUploadService initialized")

    async def start_batch_upload(
        self, files_data: List[Dict[str, Any]], background_tasks: BackgroundTasks
    ) -> str:
        """
        Start batch upload processing and return task ID immediately.

        Args:
            files_data: List of file data dictionaries with 'content', 'filename', 'size'
            background_tasks: FastAPI BackgroundTasks for async processing

        Returns:
            task_id: Unique identifier for tracking progress
        """
        task_id = f"upload_{uuid.uuid4().hex[:12]}"

        # Create upload task
        upload_task = UploadTask(
            task_id=task_id, total_files=len(files_data), start_time=datetime.utcnow()
        )

        # Create file tasks
        for i, file_data in enumerate(files_data):
            file_task = FileTask(
                file_id=f"{task_id}_file_{i}",
                filename=file_data["filename"],
                file_size=file_data["size"],
            )
            upload_task.files.append(file_task)

        # Store task
        self.tasks[task_id] = upload_task

        # Start background processing
        background_tasks.add_task(self._process_batch_upload, task_id, files_data)

        logger.info(
            "Batch upload task started", task_id=task_id, total_files=len(files_data)
        )

        return task_id

    async def _process_batch_upload(
        self, task_id: str, files_data: List[Dict[str, Any]]
    ):
        """Process batch upload in the background."""
        upload_task = self.tasks.get(task_id)
        if not upload_task:
            logger.error("Upload task not found", task_id=task_id)
            return

        upload_task.status = TaskStatus.PROCESSING

        try:
            # Process files in parallel (limit concurrency to avoid overwhelming OpenAI API)
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent file processing

            tasks = []
            for i, file_data in enumerate(files_data):
                task = self._process_single_file_with_semaphore(
                    semaphore, upload_task.files[i], file_data
                )
                tasks.append(task)

            # Wait for all files to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Update final status
            upload_task.end_time = datetime.utcnow()

            if upload_task.failed_files == 0:
                upload_task.status = TaskStatus.COMPLETED
                logger.info(
                    "Batch upload completed successfully",
                    task_id=task_id,
                    completed_files=upload_task.completed_files,
                    processing_time=upload_task.processing_time_seconds,
                )
            else:
                upload_task.status = TaskStatus.COMPLETED  # Partial success
                logger.warning(
                    "Batch upload completed with errors",
                    task_id=task_id,
                    completed_files=upload_task.completed_files,
                    failed_files=upload_task.failed_files,
                )

        except Exception as e:
            upload_task.status = TaskStatus.FAILED
            upload_task.error = str(e)
            upload_task.end_time = datetime.utcnow()

            logger.error("Batch upload failed", task_id=task_id, error=str(e))

    async def _process_single_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file_task: FileTask,
        file_data: Dict[str, Any],
    ):
        """Process a single file with concurrency control."""
        async with semaphore:
            await self._process_single_file(file_task, file_data)

    async def _process_single_file(
        self, file_task: FileTask, file_data: Dict[str, Any]
    ):
        """Process a single file through the complete pipeline."""
        file_task.start_time = datetime.utcnow()

        try:
            # Step 1: Text Extraction
            file_task.status = FileStatus.EXTRACTING_TEXT
            file_task.progress = 10.0

            file_type = file_data["filename"].split(".")[-1].lower()
            text = await self.resume_parser._extract_text_optimized(
                file_data["content"], f".{file_type}"
            )

            if not text or len(text.strip()) < 20:
                raise Exception("Failed to extract meaningful text from file")

            logger.info(
                "Text extraction completed",
                file_id=file_task.file_id,
                text_length=len(text),
            )

            # Step 2: AI Processing
            file_task.status = FileStatus.AI_PROCESSING
            file_task.progress = 30.0

            extracted_data = await self.resume_parser._extract_with_ai_optimized(
                text, timeout_seconds=15
            )

            if not extracted_data:
                raise Exception("AI extraction failed to return data")

            # Apply post-processing to improve quality and consistency with single-upload
            try:
                extracted_data = (
                    self.resume_parser.ai_extractor._post_process_extraction(
                        extracted_data, text
                    )
                )
            except Exception:
                pass

            file_task.extracted_data = extracted_data

            logger.info(
                "AI extraction completed",
                file_id=file_task.file_id,
                candidate_name=extracted_data.name,
                confidence=extracted_data.extraction_confidence,
                skills_count=len(extracted_data.technical_skills),
            )

            # Step 3: Generate Embedding
            file_task.status = FileStatus.GENERATING_EMBEDDING
            file_task.progress = 60.0

            embedding_text = f"""
            {extracted_data.name}
            {extracted_data.current_title or ''}
            {extracted_data.professional_summary or ''}
            Skills: {', '.join(extracted_data.technical_skills)}
            Experience: {extracted_data.total_experience_years} years
            Location: {extracted_data.location or ''}
            """.strip()

            embedding = await self.llm_service.get_embedding(embedding_text)

            logger.info(
                "Embedding generated",
                file_id=file_task.file_id,
                embedding_dimension=len(embedding),
            )

            # Step 4: Store in Database
            file_task.status = FileStatus.STORING
            file_task.progress = 80.0

            candidate_id = f"uploaded_{uuid.uuid4().hex[:8]}"
            file_task.candidate_id = candidate_id

            # Prepare metadata (preserve counts and current title)
            metadata = {
                "candidate_id": candidate_id,
                "name": extracted_data.name or "Unknown",
                "email": (
                    extracted_data.email.lower().strip()
                    if extracted_data.email
                    else None
                ),
                "experience_years": extracted_data.total_experience_years or 0.0,
                "skills": ",".join(extracted_data.technical_skills),
                "location": extracted_data.location or "Not Specified",
                "current_title": extracted_data.current_title or "",
                "work_exp_count": len(extracted_data.work_experience or []),
                "education_count": len(extracted_data.education or []),
                "certs_count": len(extracted_data.certifications or []),
                "source": "async_upload",
                "upload_timestamp": datetime.utcnow().isoformat(),
                "original_filename": file_data["filename"],
                # 🚀 ENHANCED: Store fast-path extraction data for fallback in profile view
                "fast_path_extraction": {
                    "work_experience": [
                        {
                            "title": exp.title,  # Fixed: Use correct attribute name
                            "company": exp.company,
                            "duration": exp.duration,
                            "location": getattr(exp, "location", ""),
                            "technologies": getattr(exp, "technologies", []),
                            "description": getattr(exp, "description", None),
                        }
                        for exp in (extracted_data.work_experience or [])
                    ],
                    "education": [
                        {
                            "degree": edu.degree,
                            "field": getattr(edu, "field", ""),
                            "school": edu.school,  # Fixed: Use correct attribute name
                            "graduation_year": getattr(edu, "graduation_year", None),
                        }
                        for edu in (extracted_data.education or [])
                    ],
                    "professional_summary": extracted_data.professional_summary or "",
                    "certifications": extracted_data.certifications or [],
                    "key_achievements": extracted_data.key_achievements or [],
                    "languages": extracted_data.languages or ["English"],
                    "confidence": extracted_data.extraction_confidence,
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "raw_resume_text": text,  # Store original text for detailed parsing
                },
            }

            # Create document text
            document_text = f"""
            Name: {extracted_data.name}
            Current Title: {extracted_data.current_title or 'Not specified'}
            Location: {extracted_data.location or 'Not specified'}
            Experience: {extracted_data.total_experience_years} years
            
            Professional Summary:
            {extracted_data.professional_summary or 'Not available'}
            
            Technical Skills: {', '.join(extracted_data.technical_skills)}
            Soft Skills: {', '.join(extracted_data.soft_skills)}
            
            Contact:
            Email: {extracted_data.email or 'Not provided'}
            Phone: {extracted_data.phone or 'Not provided'}
            LinkedIn: {extracted_data.linkedin_url or 'Not provided'}
            GitHub: {extracted_data.github_url or 'Not provided'}
            """.strip()

            # Store in ChromaDB (capture canonical id returned by upsert)
            final_id = await self.rag_service.add_candidate_to_collection(
                candidate_id=candidate_id,
                embedding=embedding,
                metadata=metadata,
                document_text=document_text,
            )

            logger.info(
                "Candidate stored successfully",
                file_id=file_task.file_id,
                candidate_id=final_id,
            )
            # Update task and metadata with canonical id
            file_task.candidate_id = final_id
            metadata["candidate_id"] = final_id

            # Step 5: Complete
            file_task.status = FileStatus.COMPLETED
            file_task.progress = 100.0
            file_task.end_time = datetime.utcnow()
            file_task.processing_time_seconds = (
                file_task.end_time - file_task.start_time
            ).total_seconds()

            # Update upload task counters
            upload_task = self.tasks.get(file_task.file_id.split("_file_")[0])
            if upload_task:
                upload_task.completed_files += 1

            logger.info(
                "File processing completed successfully",
                file_id=file_task.file_id,
                processing_time=file_task.processing_time_seconds,
            )

        except Exception as e:
            file_task.status = FileStatus.FAILED
            file_task.error = str(e)
            file_task.end_time = datetime.utcnow()
            file_task.progress = 100.0  # Mark as complete even if failed

            # Update upload task counters
            upload_task = self.tasks.get(file_task.file_id.split("_file_")[0])
            if upload_task:
                upload_task.failed_files += 1

            logger.error(
                "File processing failed",
                file_id=file_task.file_id,
                filename=file_data["filename"],
                error=str(e),
            )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an upload task."""
        upload_task = self.tasks.get(task_id)
        if not upload_task:
            return None

        return upload_task.to_dict()

    def cancel_task(self, task_id: str) -> bool:
        """Cancel an upload task (if still in progress)."""
        upload_task = self.tasks.get(task_id)
        if not upload_task:
            return False

        if upload_task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            upload_task.status = TaskStatus.CANCELLED
            upload_task.end_time = datetime.utcnow()
            logger.info("Upload task cancelled", task_id=task_id)
            return True

        return False

    def cleanup_old_tasks(self):
        """Clean up old completed tasks to free memory."""
        cutoff_time = datetime.utcnow() - self.task_cleanup_interval

        tasks_to_remove = []
        for task_id, upload_task in self.tasks.items():
            if (
                upload_task.end_time
                and upload_task.end_time < cutoff_time
                and upload_task.status
                in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.tasks[task_id]

        if tasks_to_remove:
            logger.info("Cleaned up old tasks", removed_count=len(tasks_to_remove))

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        total_tasks = len(self.tasks)
        completed_tasks = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED
        )
        failed_tasks = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.FAILED
        )

        # Calculate average processing times
        completed_upload_tasks = [
            task
            for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED and task.processing_time_seconds
        ]

        avg_processing_time = 0.0
        if completed_upload_tasks:
            avg_processing_time = sum(
                task.processing_time_seconds for task in completed_upload_tasks
            ) / len(completed_upload_tasks)

        return {
            "service_status": "running",
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "average_processing_time_seconds": avg_processing_time,
            "parser_metrics": self.resume_parser.get_performance_metrics(),
        }
