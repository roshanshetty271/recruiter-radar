#!/usr/bin/env python3
"""
Simulate Real Resume Uploads

This script simulates real users uploading the PDF resumes from test_files/
through the actual upload API endpoints. This tests the complete real workflow:

1. Uses the actual /api/v1/upload endpoint
2. Goes through the same PDF extraction process as real users
3. Uses the same LLM extraction and ChromaDB storage
4. Creates a realistic demo session with uploaded candidates

This gives us the most realistic testing environment possible!

Usage:
    cd backend
    python scripts/simulate_real_uploads.py
"""

import asyncio
import httpx
import logging
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RealUploadSimulator:
    """Simulates real resume uploads through the actual API endpoints."""

    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.demo_session_id = "demo_real_resumes_session"
        self.test_files_dir = Path("test_files")

    async def upload_resume(
        self, client: httpx.AsyncClient, pdf_path: Path
    ) -> Dict[str, Any]:
        """Upload a single resume through the API."""
        try:
            logger.info(f"📤 Uploading: {pdf_path.name}")

            # Read the PDF file
            with open(pdf_path, "rb") as file:
                files = {"file": (pdf_path.name, file, "application/pdf")}

                # Upload through the actual API endpoint
                response = await client.post(
                    f"{self.api_base}/api/v1/upload/resume",
                    files=files,
                    headers={"X-Session-ID": self.demo_session_id},
                    timeout=60.0,  # Give it time for LLM processing
                )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Success: {result.get('message', 'Upload completed')}")
                return {"success": True, "data": result, "filename": pdf_path.name}
            else:
                logger.error(f"❌ Failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": response.text,
                    "filename": pdf_path.name,
                }

        except Exception as e:
            logger.error(f"💥 Error uploading {pdf_path.name}: {e}")
            return {"success": False, "error": str(e), "filename": pdf_path.name}

    async def check_session_status(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Check the session status to see uploaded candidates."""
        try:
            response = await client.get(
                f"{self.api_base}/api/v1/session",
                headers={"X-Session-ID": self.demo_session_id},
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not get session status: {response.status_code}")
                return {}

        except Exception as e:
            logger.warning(f"Error checking session status: {e}")
            return {}

    async def test_search_functionality(self, client: httpx.AsyncClient):
        """Test search functionality with the uploaded resumes."""
        test_queries = [
            "senior software engineers",
            "Python developers",
            "machine learning engineers",
            "frontend developers",
            "engineering managers",
            "security engineers",
        ]

        logger.info("🔍 Testing search functionality...")

        for query in test_queries:
            try:
                response = await client.post(
                    f"{self.api_base}/api/v1/chat/bulletproof",
                    json={"message": f"find {query}"},
                    headers={"X-Session-ID": self.demo_session_id},
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    candidates_count = len(data.get("candidates", []))
                    source = data.get("source", "unknown")
                    logger.info(
                        f"  🎯 '{query}': {candidates_count} matches (via {source})"
                    )
                else:
                    logger.warning(f"  ❌ '{query}': Failed ({response.status_code})")

            except Exception as e:
                logger.warning(f"  💥 '{query}': Error - {e}")

    async def run(self):
        """Main execution method."""
        logger.info("🚀 Starting Real Resume Upload Simulation")
        logger.info(f"📁 Looking for resumes in: {self.test_files_dir.absolute()}")

        # Check if test_files directory exists
        if not self.test_files_dir.exists():
            logger.error(f"Directory {self.test_files_dir} does not exist!")
            return

        # Get all resume PDF files (filter out non-resume files)
        pdf_files = list(self.test_files_dir.glob("*.pdf"))
        resume_files = [
            f
            for f in pdf_files
            if any(
                keyword in f.name.lower()
                for keyword in ["resume", "engineer", "developer"]
            )
            and "questions" not in f.name.lower()  # Filter out Amazon OA Questions
        ]

        if not resume_files:
            logger.error(f"No resume PDF files found in {self.test_files_dir}")
            return

        logger.info(f"📊 Found {len(resume_files)} resume files to upload")

        # Create HTTP client for API calls
        async with httpx.AsyncClient() as client:

            # Test if backend is running
            try:
                health_response = await client.get(f"{self.api_base}/docs")
                if health_response.status_code != 200:
                    logger.error(
                        "❌ Backend is not running! Start it with: python -m uvicorn app.main:app --reload"
                    )
                    return
                logger.info("✅ Backend is running")
            except Exception as e:
                logger.error(f"❌ Cannot connect to backend: {e}")
                logger.error(
                    "Make sure backend is running with: python -m uvicorn app.main:app --reload"
                )
                return

            # Upload all resumes
            upload_results = []
            successful_uploads = 0

            for pdf_file in resume_files:
                result = await self.upload_resume(client, pdf_file)
                upload_results.append(result)
                if result["success"]:
                    successful_uploads += 1

                # Small delay between uploads
                await asyncio.sleep(1)

            # Check session status
            logger.info("\n📊 Checking session status...")
            session_status = await self.check_session_status(client)
            upload_count = session_status.get("upload_count", 0)
            logger.info(f"📈 Session upload count: {upload_count}")

            # Test search functionality
            if successful_uploads > 0:
                await self.test_search_functionality(client)

            # Print summary
            logger.info("=" * 60)
            logger.info("🎉 REAL RESUME UPLOAD SIMULATION COMPLETE!")
            logger.info(f"📊 Total files processed: {len(resume_files)}")
            logger.info(f"✅ Successful uploads: {successful_uploads}")
            logger.info(f"❌ Failed uploads: {len(resume_files) - successful_uploads}")
            logger.info(f"🆔 Demo session ID: {self.demo_session_id}")
            logger.info("=" * 60)

            # Show results summary
            if upload_results:
                logger.info("\n📋 UPLOAD RESULTS:")
                for result in upload_results:
                    status = "✅" if result["success"] else "❌"
                    filename = result["filename"]
                    logger.info(f"  {status} {filename}")
                    if not result["success"]:
                        logger.info(
                            f"     Error: {result.get('error', 'Unknown error')}"
                        )

            # Instructions for using the demo data
            if successful_uploads > 0:
                logger.info("\n🎯 HOW TO USE THIS DEMO DATA:")
                logger.info(
                    f"1. Set your frontend session ID to: {self.demo_session_id}"
                )
                logger.info(
                    "2. Try searching for: 'senior engineers', 'Python developers', etc."
                )
                logger.info("3. All uploaded candidates will appear in search results!")
                logger.info(
                    "4. This gives you the most realistic demo experience possible!"
                )


async def main():
    """Main entry point."""
    simulator = RealUploadSimulator()
    await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())
