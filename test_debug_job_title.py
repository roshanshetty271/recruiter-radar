import sys
import re


def debug_job_title_detection():
    print("🔍 Debugging Job Title Detection for Spaced Names")
    print("=" * 60)

    test_line = "R E NATA VO S S"

    job_title_keywords = [
        "director",
        "manager",
        "engineer",
        "developer",
        "analyst",
        "architect",
        "consultant",
        "specialist",
        "coordinator",
        "supervisor",
        "lead",
        "senior",
        "junior",
        "intern",
        "associate",
        "principal",
        "staff",
        "software",
        "data",
        "systems",
        "network",
        "security",
        "product",
        "project",
        "program",
        "technical",
        "chief",
        "head",
        "vice",
        "president",
        "ceo",
        "cto",
        "cfo",
        "vp",
        "officer",
        "experience",
        "summary",
        "profile",
        "objective",
        "skills",
        "education",
        "resume",
        "cv",
        "curriculum",
        "vitae",
    ]

    print(f"📝 Test line: '{test_line}'")
    print(f"📝 Test line (lower): '{test_line.lower()}'")

    line_lower = test_line.lower()
    found_keywords = [
        keyword for keyword in job_title_keywords if keyword in line_lower
    ]
    is_job_title = any(keyword in line_lower for keyword in job_title_keywords)

    print(f"🔍 Found job title keywords: {found_keywords}")
    print(f"🎯 Is job title: {is_job_title}")

    # Test spaced name conditions
    print(f"\n🧪 Spaced Name Conditions:")
    print(f"   Has space: {' ' in test_line}")
    print(f"   Is upper: {test_line.isupper()}")
    print(f"   Split count >= 2: {len(test_line.split()) >= 2}")
    print(f"   All words <= 5 chars: {all(len(w) <= 5 for w in test_line.split())}")
    print(f"   Not job title: {not is_job_title}")

    all_conditions = (
        " " in test_line
        and test_line.isupper()
        and len(test_line.split()) >= 2
        and all(len(w) <= 5 for w in test_line.split())
        and not is_job_title
    )

    print(f"   ALL CONDITIONS MET: {all_conditions}")

    if not all_conditions:
        print(f"\n❌ Conditions failed. Let's check individual words:")
        words = test_line.split()
        for i, word in enumerate(words):
            print(f"   Word {i+1}: '{word}' (length: {len(word)})")
            word_keywords = [kw for kw in job_title_keywords if kw in word.lower()]
            if word_keywords:
                print(f"      ⚠️ Contains job keywords: {word_keywords}")


if __name__ == "__main__":
    debug_job_title_detection()
