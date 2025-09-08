#!/usr/bin/env python3
"""Debug regex patterns for resume parsing"""
import re

_MONTHS = r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"

# Current patterns from extraction_utils.py
patterns = [
    # Pattern 1: "Company, City, State/Country Dates"
    re.compile(
        r"^(.+?),\s*([^,]+,\s*[A-Za-z\s]+?)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE
    ),
    # Pattern 2: "Company, Location Dates" (more flexible location)
    re.compile(r"^(.+?),\s*([^,]+)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE),
    # Pattern 3: "Company Location Dates" (no commas)
    re.compile(
        r"^(.+?)\s+([A-Z][a-z]+(?:,\s*[A-Z]{2})?)\s+(" + _MONTHS + r".*?)$",
        re.IGNORECASE,
    ),
    # Pattern 4: Just "Company Dates" (no location)
    re.compile(r"^(.+?)\s+(" + _MONTHS + r".*?)$", re.IGNORECASE),
]

# Test lines from Roshan's resume
test_lines = [
    "Aosenuma, Texas, USA Jan 2025 - May 2025",
    "Capgemini, Navi Mumbai, India Nov 2020 - Jun 2023",
]

print("🔍 DEBUGGING REGEX PATTERNS\n")

for i, test_line in enumerate(test_lines, 1):
    print(f"📄 Test Line {i}: '{test_line}'")

    for j, pattern in enumerate(patterns, 1):
        match = pattern.match(test_line)
        if match:
            print(f"  ✅ Pattern {j} SUCCESS:")
            groups = match.groups()
            if len(groups) == 3:
                print(f"    Company: '{groups[0]}'")
                print(f"    Location: '{groups[1]}'")
                print(f"    Duration: '{groups[2]}'")
            elif len(groups) == 2:
                print(f"    Company: '{groups[0]}'")
                print(f"    Duration: '{groups[1]}'")
            break
        else:
            print(f"  ❌ Pattern {j} failed")
    else:
        print(f"  🚨 ALL PATTERNS FAILED for '{test_line}'")

    print()

# Test job title matching
print("🎯 TESTING JOB TITLE PATTERNS\n")

job_title_patterns = [
    r"\b(?:senior|lead|principal|chief|head of|director of)?\s*(?:software|web|mobile|backend|frontend|full.?stack|data|machine learning|ai|ml)?\s*(?:engineer|developer|scientist|analyst|architect|manager|consultant|specialist|intern|associate)\b",
]

job_title_regex = re.compile("|".join(job_title_patterns), re.IGNORECASE)

test_titles = ["AI Software Developer", "Software Developer"]

for title in test_titles:
    match = job_title_regex.search(title)
    print(f"📝 '{title}': {'✅ MATCH' if match else '❌ NO MATCH'}")
