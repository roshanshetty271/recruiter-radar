# Resume Test Collection

This directory contains test resumes organized by complexity for validating the LLM extraction pipeline.

## Categories:

### [STANDARD] standard/
Clean, well-formatted resumes that should parse easily. Target: 95%+ success rate.

### [CHALLENGING] challenging/
Complex layouts with multiple columns, graphics, tables. Target: 70-85% success rate.

### [EDGE CASES] edge_cases/
Unusual formats, scanned images, non-English text. Target: 40-70% success rate.

### [REAL WORLD] real_world/
Actual resumes from job sites and platforms. Target: 75-90% success rate.

## Adding Test Files:

1. Ensure you have permission to use the resumes (use synthetic/anonymous data)
2. Name files descriptively (e.g., `role_format_issue.pdf`)
3. Aim for 3-5 files per category minimum
4. Include diverse roles, experience levels, and formats

## Privacy Note:
[WARNING] Never commit real resumes with personal information to version control!
Use synthetic data or thoroughly anonymized resumes only.
