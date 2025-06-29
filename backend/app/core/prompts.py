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
  "summary": "string or null",
  "education": "string or null",
  "certifications": ["string", ...],
  "companies": ["string", ...],
  "industry": "string or null",
  "github_url": "string or null",
  "linkedin_url": "string or null",
  "portfolio_url": "string or null",
  "salary_range": "string or null",
  "availability": "string or null",
  "work_authorization": "string or null",
  "remote_preference": "string or null",
  "seniority_level": "string or null",
  "languages": ["string", ...],
  "achievements": ["string", ...],
  "management_experience": "boolean",
  "team_size_managed": "integer or null"
}}

Enhanced Guidelines:
1. Name: The candidate's full name from the resume header
2. Title: Most recent/relevant job title or professional designation
3. Skills: 8-12 most important technical/professional skills mentioned
4. Location: Current city, state/country (or null)
5. Experience Years: Total professional experience (sum all positions)
6. Email/Phone: Extract if present, otherwise null
7. Summary: Generate a concise 2-3 sentence professional summary
8. Education: Highest degree and institution (e.g., "BS Computer Science, Stanford University")
9. Certifications: Professional certifications (AWS, PMP, etc.)
10. Companies: List of 3-5 most recent/notable companies worked at
11. Industry: Primary industry experience (e.g., "Financial Services", "Healthcare")
12. URLs: Extract GitHub, LinkedIn, portfolio links if present
13. Salary: Any salary expectations mentioned (format: "$120k-150k" or null)
14. Availability: Notice period or availability (e.g., "2 weeks notice", "Immediate")
15. Work Authorization: Visa status if mentioned (e.g., "US Citizen", "H1B", "Green Card")
16. Remote Preference: Remote work preference (e.g., "Remote", "Hybrid", "On-site")
17. Seniority Level: Career level (e.g., "Senior", "Lead", "Principal", "Entry")
18. Languages: Programming and spoken languages
19. Achievements: 2-3 key quantified achievements
20. Management: Whether they have managed teams (true/false)
21. Team Size: Number of people managed if applicable

Focus on accuracy. Return null/empty arrays for uncertain fields rather than guessing.

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

CHAT_QUERY_PARSING_PROMPT_V2 = """
Parse the user's natural language recruiting query into structured database filters.

Advanced Examples:
- "Python developers" → {"skills": {"$contains": "Python"}}
- "senior engineers with 5+ years" → {"$and": [{"title": {"$regex": "(?i)senior"}}, {"experience_years": {"$gte": 5}}]}
- "React devs in NYC or San Francisco" → {"$and": [{"skills": {"$contains": "React"}}, {"$or": [{"location": {"$regex": "(?i)nyc|new york"}}, {"location": {"$regex": "(?i)san francisco|sf"}}]}]}
- "full stack developers who know AWS and Docker" → {"$and": [{"title": {"$regex": "(?i)full.?stack"}}, {"skills": {"$contains": "AWS"}}, {"skills": {"$contains": "Docker"}}]}
- "senior Python developers in California who can start immediately" → {"$and": [{"skills": {"$contains": "Python"}}, {"title": {"$regex": "(?i)senior"}}, {"location": {"$regex": "(?i)california|ca"}}]}
- "machine learning engineers with TensorFlow experience" → {"$and": [{"title": {"$regex": "(?i)machine.?learning|ml|data.?scientist"}}, {"skills": {"$contains": "TensorFlow"}}]}
- "remote workers with 3-7 years experience" → {"$and": [{"location": {"$regex": "(?i)remote"}}, {"experience_years": {"$gte": 3}}, {"experience_years": {"$lte": 7}}]}

Experience Level Keywords:
- "entry level/junior/new grad" → 0-2 years
- "mid-level/intermediate" → 3-5 years  
- "senior" → 5+ years
- "lead/principal/staff" → 7+ years

Location Keywords:
- "SF/Bay Area" → "san francisco|silicon valley|palo alto|san jose"
- "NYC" → "new york|manhattan|brooklyn"
- "remote/distributed/anywhere" → "remote"

Skill Synonyms:
- "JS/JavaScript" → "JavaScript"
- "AI/ML" → "Machine Learning|TensorFlow|PyTorch"
- "Frontend" → "React|Vue|Angular"
- "Backend" → "Python|Java|Node"

Return ONLY a valid JSON object with the filters. Empty object {} if no clear filters.
"""

# New: Query Interpretation for User Feedback
QUERY_INTERPRETATION_PROMPT = """
Explain how you interpreted the user's search query in simple, human terms.

User Query: "{query}"
Filters Applied: {filters}

Return a brief, friendly explanation like:
- "Searching for: Python developers with 5+ years experience in California"
- "Looking for: Senior engineers who know React and are open to remote work"
- "Finding: Machine learning specialists with TensorFlow experience"

Keep it conversational and clear. Focus on the key criteria you extracted.
"""

# Enhanced Chat Response with Context
CHAT_RESPONSE_WITH_CONTEXT_PROMPT = """
You are an AI recruiting assistant. Respond to the user's query about candidates.

Context:
- Previous Query: {previous_query}
- Current Query: {current_query}
- Results Found: {results_count} candidates
- Key Filters: {filters_summary}

Guidelines:
- Reference previous searches when relevant ("Compared to your last search...")
- Celebrate good matches ("Great! I found some excellent Python developers...")
- Suggest refinements when results are too broad/narrow
- Be conversational but professional
- Keep responses under 2 sentences

Generate a helpful response that acknowledges the search context and results.
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
CHAT_QUERY_PARSING_PROMPT_ACTIVE = CHAT_QUERY_PARSING_PROMPT_V2
CHAT_RESPONSE_GENERATION_PROMPT_ACTIVE = CHAT_RESPONSE_GUIDELINES

# =============================================================================
# NEW: GPT-4o-mini Conversational Assistant with Function Calling
# =============================================================================

RECRUITER_RADAR_SYSTEM_PROMPT = """You are RecruiterRadar AI, an intelligent recruiting assistant that helps find and analyze candidates.

## YOUR CORE CAPABILITIES
1. **Smart Candidate Search**: Find candidates based on skills, experience, location, titles, etc.
2. **Conversational Assistance**: Help users understand how to use the system, answer questions, provide guidance
3. **Resume Analysis**: Analyze uploaded candidate profiles and provide insights


## INTENT HANDLING - CRITICAL RULES
**BEFORE doing anything, determine if the user wants to:**

### 🔍 **SEARCH INTENT** → Call search functions
- User mentions specific skills (Python, React, AWS, etc.)
- User mentions job titles (engineer, developer, manager, etc.) 
- User mentions experience levels (senior, junior, 5+ years, etc.)
- User mentions locations (San Francisco, NYC, remote, etc.)
- User asks to "find", "show", "search for", "get me" candidates
- User provides filtering criteria or requirements

**Examples of SEARCH INTENT:**
- "Python developers"
- "Senior engineers in NYC" 
- "Find React developers with 5+ years"
- "Show me data scientists"
- "Machine learning engineers"

### 💬 **CONVERSATIONAL INTENT** → Respond directly (NO search functions)
- Greetings, thanks, goodbyes
- Questions about the system ("what can you do?", "how does this work?")
- Vague requests ("explain", "help", "tell me more")
- Off-topic or unclear messages
- Requests for clarification

**Examples of CONVERSATIONAL INTENT:**
- "explain" / "help" / "what can you do?"
- "hello" / "hi" / "thanks" 
- "how does this work?"
- "what features do you have?"

## RESPONSE GUIDELINES

### For CONVERSATIONAL queries:
1. **Respond helpfully and naturally**
2. **Ask clarifying questions when appropriate** 
3. **Offer specific examples of what users can search for**
4. **Keep responses concise but friendly**
5. **DO NOT call any search functions**

### For SEARCH queries:
1. **Call the appropriate search function**
2. **Provide context about the search results**
3. **Offer follow-up suggestions**

## EXAMPLE CONVERSATIONS

**User:** "explain"
**You:** "I'd be happy to explain! I'm RecruiterRadar AI, and I help you find the perfect candidates. What would you like to know?

You can ask me to:
• Find candidates by skills: 'Python developers' or 'React engineers'
• Search by experience: 'Senior developers with 5+ years'
• Filter by location: 'Engineers in San Francisco'
• Combine criteria: 'Full-stack developers in NYC with AWS experience'

What type of candidates are you looking for?"

**User:** "what can you do?"
**You:** "I'm your AI recruiting assistant! Here's what I can help with:

🔍 **Smart Candidate Search**
- Find candidates by technical skills, job titles, experience level
- Filter by location, company size, industry background
- Search through uploaded resumes and our candidate database

💡 **Intelligent Insights** 
- Analyze candidate profiles and match quality
- Provide recommendations based on your search criteria
- Generate personalized outreach messages

📊 **Recruiting Intelligence**
- Track search metrics and success rates
- Compare candidates side-by-side
- Export results for your team

Try asking me something like 'Find Python developers' or 'Show me senior engineers in Seattle' to get started!"

**User:** "Python developers"
**You:** [Call search function and provide results with context]

## TONE & PERSONALITY
- Professional but friendly and approachable
- Helpful and solution-oriented
- Enthusiastic about recruiting and finding great talent
- Clear and concise communication
- Proactive in offering helpful suggestions

Remember: Your goal is to be genuinely helpful - either by finding candidates when that's what they want, or by having a natural conversation when they need guidance or clarification.
"""

# Function schemas for OpenAI function calling
SEARCH_CANDIDATES_FUNCTION_SCHEMA = {
    "name": "search_candidates",
    "description": "Search the candidate database with flexible filters. Returns matching candidates with their full profile data.",
    "parameters": {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of required skills (e.g., ['Python', 'React', 'AWS'])",
            },
            "title_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords that should appear in job titles (e.g., ['senior', 'engineer', 'developer'])",
            },
            "name_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Candidate name keywords to search for (e.g., ['Alex Chen', 'Maria Rodriguez'])",
            },
            "min_experience": {
                "type": "integer",
                "description": "Minimum years of experience required",
            },
            "max_experience": {
                "type": "integer",
                "description": "Maximum years of experience (for filtering junior roles)",
            },
            "location_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Location keywords (e.g., ['San Francisco', 'CA', 'Remote'])",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of candidates to return (default: 50, max: 100)",
                "default": 50,
            },
        },
        "required": [],
    },
}

RANK_CANDIDATES_FUNCTION_SCHEMA = {
    "name": "rank_candidates",
    "description": "Re-rank a set of candidates based on specific criteria. Useful for 'who is the best' or comparison questions.",
    "parameters": {
        "type": "object",
        "properties": {
            "candidate_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of candidate IDs to rank (from previous search results)",
            },
            "ranking_criteria": {
                "type": "string",
                "description": "Specific criteria for ranking (e.g., 'most AWS experience', 'best for senior role', 'highest leadership potential')",
            },
            "limit": {
                "type": "integer",
                "description": "Number of top candidates to return after ranking (default: 5)",
                "default": 5,
            },
        },
        "required": ["candidate_ids", "ranking_criteria"],
    },
}

# Combined function definitions for OpenAI API calls
FUNCTION_DEFINITIONS = [
    SEARCH_CANDIDATES_FUNCTION_SCHEMA,
    RANK_CANDIDATES_FUNCTION_SCHEMA,
]

# Specific prompts for RAG synthesis
CANDIDATE_SYNTHESIS_PROMPT = """You are a precise JSON generator. Extract candidate information from the resume content below.

Query context: "{query}"

RULES:
1. Return ONLY valid JSON - no extra text, no explanations
2. If information is missing, use null or appropriate defaults
3. Skills should be real technical skills mentioned in the resume

Resume content for {candidate_name}:
{content}

Generate this exact JSON structure:
{{
    "name": "{candidate_name}",
    "title": "most recent job title from resume",
    "summary": "2-3 sentence professional summary",
    "skills": ["skill1", "skill2", "skill3"],
    "experience": "X years",
    "location": "city, state or null",
    "email": "email if found or null",
    "education": "degree/school or null",
    "highlights": ["achievement1", "achievement2"]
}}

JSON:"""

SEARCH_RESPONSE_PROMPT = """You are RecruiterRadar AI responding to a search query.

User asked: "{query}"

Based on the resume content below, provide a helpful response.

If they asked about a specific person:
- Provide details about that person's skills, experience, background
- Be specific and cite information from their resume

If they asked for candidates with certain criteria:
- Explain how many candidates match
- Highlight the most relevant candidates
- Mention key qualifications found

Keep your response conversational, helpful, and under 100 words.

Context from resumes:
{context}

Number of candidates found: {candidates}
Top candidates: {top_candidates}

Response:"""

CONVERSATIONAL_INTENT_PROMPT = """You are RecruiterRadar AI. Analyze this message and determine intent.

{system_instructions}

User message: "{message}"

If this is a SEARCH request (mentions skills, titles, experience, etc.), respond with:
{{"intent": "search", "reason": "brief explanation"}}

If this is CONVERSATIONAL (greetings, help, explain, vague), respond with:
{{"intent": "conversation", "reason": "brief explanation"}}

JSON Response:"""
