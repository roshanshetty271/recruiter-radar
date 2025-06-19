"""
Centralized LLM prompts for RecruiterRadar MVP.
All prompts are versioned for A/B testing and iterative improvement.
"""

# Resume extraction prompts - iterate through versions as we test
EXTRACTION_PROMPT_V1 = """
Analyze the resume text provided below. Extract the following information and return it as a VALID JSON object.

Keys in JSON must be EXACTLY: "name", "title", "skills", "location", "experience_years", "email", "phone", "summary"

Instructions:
- For "name": Extract the full name of the candidate
- For "title": Extract the most recent or prominent job title
- For "skills": List 5-7 key technical skills or competencies as an array of strings
- For "location": Extract city and state/country (e.g., "San Francisco, CA"). If multiple, use the most recent
- For "experience_years": Calculate total years of professional experience as an integer
- For "email": Extract email address or null if not found
- For "phone": Extract phone number or null if not found  
- For "summary": Create a 1-2 sentence overview of the candidate's profile

Important:
- If a field cannot be determined with confidence, use null
- For experience_years, if unclear, estimate based on job history or use 0
- Ensure the output is valid JSON that can be parsed

Resume text:
---
{text}
---

JSON Output:
"""

EXTRACTION_PROMPT_V2 = """
You are an expert resume parser. Analyze the following resume text and extract structured information.

Return a JSON object with these exact keys:
{{
  "name": "string",
  "title": "string", 
  "skills": ["string", ...],
  "location": "string or null",
  "experience_years": "integer",
  "email": "string or null",
  "phone": "string or null",
  "summary": "string or null"
}}

Guidelines:
1. Name: The candidate's full name from the resume header
2. Title: Most recent/relevant job title or professional designation
3. Skills: 5-7 most important technical/professional skills mentioned
4. Location: Current city, state/country (or null)
5. Experience Years: Total professional experience (sum all positions)
6. Email/Phone: Extract if present, otherwise null
7. Summary: Generate a concise 1-2 sentence professional summary

Focus on accuracy. Return null for uncertain fields rather than guessing.

Resume Text:
{text}

JSON:
"""

EXTRACTION_PROMPT_V3 = """
Extract structured data from this resume. You must return valid JSON.

Required fields (use null if not found):
- name: Full name
- title: Current/latest job title
- skills: Array of 5-7 key skills
- location: City, State format
- experience_years: Total years (integer)
- email: Email address
- phone: Phone number
- summary: 1-2 sentence overview you generate

Resume:
{text}

Return only the JSON object:
"""

# Confidence scoring prompt (optional enhancement)
EXTRACTION_CONFIDENCE_PROMPT = """
Based on the resume text provided, extract the required information AND provide confidence scores.

Return JSON in this format:
{{
  "data": {{
    "name": "...",
    "title": "...",
    "skills": [...],
    "location": "...",
    "experience_years": 0,
    "email": "...",
    "phone": "...",
    "summary": "..."
  }},
  "confidence": {{
    "name": 0.95,
    "title": 0.87,
    "skills": 0.92,
    "location": 0.78,
    "experience_years": 0.65,
    "email": 1.0,
    "phone": 1.0,
    "summary": 0.90
  }}
}}

Confidence scores should be 0.0-1.0 based on how clearly the information was stated in the resume.

Resume:
{text}
"""

# For generating personalized outreach messages to candidates.
OUTREACH_DRAFT_PROMPT = """You are an expert technical recruiter. Your task is to write a personalized, engaging, and concise outreach message to a potential candidate for a specific job role.

Use the provided candidate details and job role to draft the message.

**Candidate Details:**
- Name: {candidate_name}
- Key Skills: {candidate_skills}
- Experience Highlights: {candidate_summary}

**Job Role:**
- Title: {job_role}

**Instructions:**
- Start with a personalized greeting to the candidate.
- Briefly introduce the compelling opportunity ({job_role}).
- Mention 1-2 specific skills or experiences from the candidate's profile that make them a great fit.
- Keep the tone professional, yet friendly and enthusiastic.
- The entire message should be concise (around 100-150 words).
- End with a clear call to action, like asking for their availability for a brief chat.
"""

# Chat Query Parsing Prompts
CHAT_QUERY_PARSING_PROMPT_V1 = """
Parse the user's natural language query into structured database filters.

Examples:
- "Python developers" → {"skills": {"$contains": "Python"}}
- "senior engineers with 5+ years" → {"$and": [{"title": {"$regex": "(?i)senior"}}, {"experience_years": {"$gte": 5}}]}
- "React devs in NYC or Boston" → {"$and": [{"skills": {"$contains": "React"}}, {"$or": [{"location": {"$regex": "NYC"}}, {"location": {"$regex": "Boston"}}]}]}
- "full stack developers who know AWS" → {"$and": [{"title": {"$regex": "(?i)full.?stack"}}, {"skills": {"$contains": "AWS"}}]}
- "entry level Python" → {"$and": [{"skills": {"$contains": "Python"}}, {"experience_years": {"$lte": 2}}]}

Key patterns:
- Use $contains for skills (since skills is an array)
- Use $regex with (?i) for case-insensitive text matching
- Use $gte/$lte for numeric comparisons
- Use $and/$or for combining conditions
- "senior" typically means 5+ years, "entry level" means 0-2 years
- "junior" means 1-3 years, "mid-level" means 3-5 years

Return ONLY a valid JSON object with the filters. Empty object {} if no clear filters.
"""

# Chat Response Generation Guidelines
CHAT_RESPONSE_GUIDELINES = """
You are an AI recruiting assistant helping users find candidates from their uploaded resumes.

Tone:
- Friendly and conversational
- Professional but not stiff
- Enthusiastic about good matches
- Helpful when no results found

Keep responses concise and actionable.
"""

# Current active versions (update these as you test)
EXTRACTION_PROMPT_ACTIVE = EXTRACTION_PROMPT_V2
CHAT_QUERY_PARSING_PROMPT_ACTIVE = CHAT_QUERY_PARSING_PROMPT_V1
CHAT_RESPONSE_GENERATION_PROMPT_ACTIVE = CHAT_RESPONSE_GUIDELINES
