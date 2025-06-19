import asyncio
import aiohttp
import os
from pathlib import Path


async def upload_resume(session, file_path, session_id):
    """Upload a single resume."""
    url = "http://localhost:8000/api/v1/upload/resume"
    headers = {"X-Session-ID": session_id}

    with open(file_path, "rb") as f:
        data = aiohttp.FormData()
        data.add_field(
            "file",
            f,
            filename=os.path.basename(file_path),
            content_type="application/pdf",
        )

        async with session.post(url, data=data, headers=headers) as resp:
            try:
                result = await resp.json()
                print(
                    f"Uploaded {file_path.name}: {result.get('status')} - {result.get('message')}"
                )
                return result
            except aiohttp.ContentTypeError:
                text = await resp.text()
                print(
                    f"Error uploading {file_path.name}: Server returned non-JSON response (Status: {resp.status})"
                )
                print(f"Response body: {text}")
                return None


async def test_chat(session, query, session_id):
    """Test chat endpoint."""
    url = "http://localhost:8000/api/v1/chat"
    data = {"message": query, "session_id": session_id}

    async with session.post(url, json=data) as resp:
        try:
            result = await resp.json()
            print(f"\nQuery: '{query}'")
            print(f"AI Response: {result.get('ai_message', 'N/A')}")
            candidates = result.get("candidates", [])
            print(f"Found {len(candidates)} candidates")
            for candidate in candidates[:3]:
                print(f"  - {candidate.get('name')} ({candidate.get('title')})")
            return result
        except aiohttp.ContentTypeError:
            text = await resp.text()
            print(
                f"\nError testing chat with query '{query}': Server returned non-JSON response (Status: {resp.status})"
            )
            print(f"Response body: {text}")
            return None


async def main():
    session_id = "test-device-123"

    async with aiohttp.ClientSession() as session:
        # Path to the directory with your test PDFs
        pdf_dir = Path(__file__).parent / "test_resumes"
        if not pdf_dir.exists():
            print(f"Error: Test resume directory not found at {pdf_dir.resolve()}")
            return

        pdf_files = list(pdf_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"Error: No PDF files found in {pdf_dir.resolve()}")
            return

        print(f"Found {len(pdf_files)} PDFs to upload from {pdf_dir.resolve()}\n")

        # Upload all PDFs
        for pdf_file in pdf_files:
            await upload_resume(session, pdf_file, session_id)
            await asyncio.sleep(0.5)  # Small delay

        print("\n" + "=" * 50 + "\n")

        # Test various chat queries
        test_queries = [
            "Show me Python developers",
            "Senior engineers with 5+ years experience",
            "Anyone with React and TypeScript?",
            "Full stack developers in San Francisco",
            "Entry level developers",
            "DevOps engineers with AWS",
            "Show me all candidates",  # A query that should return all
        ]

        for query in test_queries:
            await test_chat(session, query, session_id)
            print("\n" + "-" * 30)
            await asyncio.sleep(1)


if __name__ == "__main__":
    # This allows running the script with `python -m asyncio` on Windows if needed,
    # but asyncio.run() is generally fine.
    asyncio.run(main())
