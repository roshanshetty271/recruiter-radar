import sys
import re
from pathlib import Path

sys.path.append("backend")
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.llm_service import LLMService
from backend.app.core.config import settings


def debug_renata_name():
    print("🔍 Debugging Renata's Name Extraction")
    print("=" * 50)

    # Load Renata's resume
    resume_path = Path("backend/tests/test_data/resumes/renata_voss.txt")
    resume_text = resume_path.read_text(encoding="utf-8")

    lines = resume_text.strip().split("\n")
    print(f"📄 First 10 lines of resume:")
    for i, line in enumerate(lines[:10]):
        print(f"   {i+1:2d}: '{line.strip()}'")

    print("\n🧪 Testing name extraction patterns:")

    # Test the spaced name pattern
    spaced_name_pattern = r"^[A-Z]\s+[A-Z]\s.*[A-Z]\s+[A-Z]\s.*[A-Z]\s+[A-Z]"
    first_line = lines[0].strip()

    print(f"📝 First line: '{first_line}'")
    print(f"🔍 Spaced pattern: {spaced_name_pattern}")
    print(f"🎯 Pattern match: {bool(re.match(spaced_name_pattern, first_line))}")

    if re.match(spaced_name_pattern, first_line):
        print("✅ Pattern matches! Processing...")
        name = re.sub(r"\s+", " ", first_line.replace(" ", "")).strip()
        print(f"   Step 1 - Remove spaces: '{name}'")
        name = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", name)
        print(f"   Step 2 - Add logical spaces: '{name}'")
    else:
        print("❌ Pattern doesn't match, trying alternatives...")

        # Try a more flexible pattern
        alt_pattern = r"^[A-Z]\s+[A-Z].*[A-Z]\s+[A-Z]"
        print(f"🔍 Alternative pattern: {alt_pattern}")
        print(f"🎯 Alt pattern match: {bool(re.match(alt_pattern, first_line))}")

        # Manual processing
        if " " in first_line and first_line.isupper():
            print("🛠️ Manual processing for spaced uppercase name...")
            words = first_line.split()
            print(f"   Words: {words}")
            print(f"   All words <= 5 chars: {all(len(w) <= 5 for w in words)}")
            if len(words) >= 2 and all(len(w) <= 5 for w in words):
                # Likely spaced characters, join them
                name = "".join(words)
                print(f"   Joined: '{name}' (length: {len(name)})")
                # Insert spaces logically
                if len(name) >= 4:  # At least 4 chars for first + last
                    # Use smarter logic for finding split point
                    mid = len(name) // 2
                    if len(name) >= 6:
                        # For "RENATAVOSS", try different split points
                        for split_point in range(
                            max(2, len(name) * 2 // 5),
                            min(len(name) - 2, len(name) * 3 // 5 + 1),
                        ):
                            mid = split_point
                            break
                    name = name[:mid] + " " + name[mid:]
                    print(f"   Final result: '{name}' (split at position {mid})")
                else:
                    print(f"   Too short, keeping as: '{name}'")


if __name__ == "__main__":
    debug_renata_name()
