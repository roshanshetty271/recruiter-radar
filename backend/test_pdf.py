# backend/test_pdf.py
import asyncio
import logging
from app.services.pdf_service import PDFService

# Basic logging setup to see output from the service
logging.basicConfig(level=logging.INFO)


async def test_extraction():
    """
    Test the PDF extraction service on a local file.
    """
    # --- IMPORTANT ---
    # Change this to the actual path of your test resume PDF
    pdf_file_path = (
        "../documentation/resumes/experienced-software-engineer-resume-example.pdf"
    )
    # For example: "documentation/resumes/experienced-software-engineer-resume-example.pdf"
    # --- IMPORTANT ---

    try:
        with open(pdf_file_path, "rb") as f:
            pdf_bytes = f.read()
            print(f"--- Testing PDF: {pdf_file_path} ---")
            result = await PDFService.extract_text_from_pdf(pdf_bytes)

        print(f"\n--- RESULTS ---")
        print(f"Success: {result.success}")
        print(f"Pages:   {result.page_count}")
        print(f"Chars:   {result.char_count}")

        if result.success:
            print(f"First 500 chars: {result.text[:500]}")

            # Save the full extracted text for easy inspection
            output_filename = "extracted_text_from_test.txt"
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(result.text)
            print(f"\nFull extracted text saved to: '{output_filename}'")
        else:
            print(f"Error: {result.error}")

    except FileNotFoundError:
        print(
            f"ERROR: File not found at '{pdf_file_path}'. Please update the path in the script."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    print("Running PDF extraction test script...")
    asyncio.run(test_extraction())
