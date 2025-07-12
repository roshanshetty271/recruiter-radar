import json
import re
import os

# Build the full path to the data file relative to the script's location
# The script is in backend/scripts, the data is in backend/app/data
script_dir = os.path.dirname(__file__)
project_root = os.path.dirname(script_dir)  # this is backend/
file_path = os.path.join(project_root, "app", "data", "candidate_profiles.json")

# Load data
try:
    with open(file_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
except FileNotFoundError:
    print(f"Error: Could not find the file at {file_path}")
    exit()

# Define the email regex pattern
email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
updated_count = 0

# Process each candidate
for candidate in candidates:
    # Only process if email field is missing or null
    if candidate.get("email") is None:
        match = re.search(
            email_pattern, candidate.get("raw_resume_text", ""), re.IGNORECASE
        )
        if match:
            candidate["email"] = match.group()
            updated_count += 1
        else:
            candidate["email"] = None  # Ensure consistent structure

# Define canonical order of keys for consistency
canonical_order = [
    "id",
    "name",
    "email",
    "raw_resume_text",
    "skills",
    "experience_years",
    "visa_status",
    "location",
    "github_url",
    "linkedin_url",
]

reordered_candidates = []
for candidate in candidates:
    reordered_candidate = {}
    for key in canonical_order:
        if key in candidate:
            reordered_candidate[key] = candidate[key]

    # Add any other keys that might not be in the canonical order, just in case
    for key, value in candidate.items():
        if key not in reordered_candidate:
            reordered_candidate[key] = value

    reordered_candidates.append(reordered_candidate)

# Save the updated data back to the file
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(reordered_candidates, f, indent=4)

print(f"Processing complete.")
print(f"Successfully processed {len(reordered_candidates)} candidates.")
print(f"Found and added emails for {updated_count} candidates.")
print(f"The file '{file_path}' has been updated with a consistent structure.")
