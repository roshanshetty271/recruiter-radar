"""
AI prompts for resume extraction and other LLM tasks.
"""

RESUME_EXTRACTION_PROMPT_V5 = """
Extract ALL information from this resume. Handle multiple jobs, education, and unlimited items.

CRITICAL RULES:
1. Extract ALL work experiences (not just the most recent one)
2. Extract ALL education entries (degrees, bootcamps, courses, certifications)
3. Extract EVERY skill mentioned (no limits - could be 50+ skills)
4. Handle various date formats gracefully
5. If unsure about a field, include it rather than skip it
6. Arrays can have ANY number of items - extract them ALL
7. CALCULATE total_experience_years by adding up ALL job durations

EXPERIENCE CALCULATION EXAMPLES (BE PRECISE WITH DATES):
- "Software Engineer at Google (2019 - 2023)" → 4 years
- "Director at Adobe (2019 - current)" → ~5 years (2025 - 2019)
- "Engineer (Jan 2015 - Dec 2017)" → 3 years
- "Aug 2020 - Present" → ~4.5 years (2025 - 2020.67)
- "June 2017 - June 2020" → 3 years exactly
- "2016 - 2017" (year only) → 1 year (assume full year)
- Multiple jobs: Add them up! 3 years + 2 years + 4 years = 9 years total

CRITICAL: Use current year 2025 for "Present", "Current", "Now" calculations.
CRITICAL: Parse month-year dates precisely (Aug 2020 = 2020.67, June 2017 = 2017.5)
CRITICAL: Account for ALL jobs including internships and part-time work.

JSON STRUCTURE (showing multiple entries):
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1-234-567-8900",
    "location": "City, State/Country or Remote",
    "current_title": "Most Recent Job Title (infer from work_experience[0])",
    "desired_roles": ["Software Engineer", "Full Stack Developer", "Tech Lead"],
    "total_experience_years": 8.5,
    
    "technical_skills": [
        "Python", "JavaScript", "React", "Node.js", "AWS", "Docker", 
        "Kubernetes", "GraphQL", "PostgreSQL", "MongoDB", "Redis",
        "JIRA", "Jenkins", "TensorFlow", "Apache Hadoop", "Spring Boot",
        "Selenium", "Oracle", "ANY OTHER TECHNICAL SKILL MENTIONED - NO LIMIT"
    ],
    
    "soft_skills": [
        "Leadership", "Agile", "Communication", "Problem Solving",
        "ALL SOFT SKILLS FOUND"
    ],
    
    "work_experience": [
        {{
            "company": "Current Company Inc",
            "title": "Senior Software Engineer",
            "duration": "Jan 2021 - Present",
            "description": "Led team of 5 engineers developing microservices...",
            "technologies": ["React", "Node.js", "AWS", "Docker"]
        }},
        {{
            "company": "Previous Corp",
            "title": "Software Engineer",
            "duration": "Jun 2018 - Dec 2020",
            "description": "Developed full-stack applications serving 10k users...",
            "technologies": ["Python", "Django", "PostgreSQL"]
        }},
        {{
            "company": "Startup XYZ",
            "title": "Junior Developer",
            "duration": "Jan 2017 - May 2018",
            "description": "Built features for e-commerce platform...",
            "technologies": ["JavaScript", "MongoDB", "Express"]
        }}
        // EXTRACT ALL JOBS - NO LIMIT (could be 10+ jobs for senior professionals)
    ],
    
    "education": [
        {{
            "degree": "Master of Science",
            "field": "Computer Science",
            "school": "Stanford University",
            "graduation_year": "2017",
            "gpa": "3.9"
        }},
        {{
            "degree": "Bachelor of Science",
            "field": "Mathematics",
            "school": "UC Berkeley",
            "graduation_year": "2015",
            "gpa": "3.7"
        }},
        {{
            "degree": "Full Stack Web Development Bootcamp",
            "field": "Software Engineering",
            "school": "App Academy",
            "graduation_year": "2016",
            "gpa": null
        }}
        // INCLUDE ALL EDUCATION, CERTIFICATIONS, BOOTCAMPS
    ],
    
    "projects": [
        {{
            "name": "Open Source React Contributions",
            "description": "Fixed 15+ bugs in React core library",
            "technologies": ["JavaScript", "React", "Jest"],
            "url": "https://github.com/facebook/react/pulls/username"
        }},
        {{
            "name": "AI-Powered Chatbot",
            "description": "Built chatbot serving 10k daily users",
            "technologies": ["Python", "TensorFlow", "Flask", "Redis"],
            "url": "https://chatbot-demo.com"
        }},
        {{
            "name": "E-commerce Platform",
            "description": "Full-stack marketplace with payment integration",
            "technologies": ["Node.js", "React", "Stripe", "MongoDB"],
            "url": "https://github.com/username/ecommerce"
        }}
        // ALL PROJECTS MENTIONED
    ],
    
    "certifications": [
        "AWS Solutions Architect Professional",
        "Google Cloud Professional Developer",
        "Kubernetes Administrator (CKA)",
        "Scrum Master Certified",
        // ALL CERTIFICATIONS FOUND - could be 10+
    ],
    
    "languages": ["English (Native)", "Spanish (Fluent)", "Mandarin (Conversational)"],
    "clearance_level": "Secret",
    
    "linkedin_url": "https://linkedin.com/in/username",
    "github_url": "https://github.com/username",
    "portfolio_url": "https://portfolio-site.com",
    "other_urls": [
        "https://blog.medium.com/@username",
        "https://personal-website.com",
        "https://stackoverflow.com/users/username"
    ],
    
    "professional_summary": "Generate 2-3 sentence summary if not explicitly stated",
    "key_achievements": [
        "Reduced API response time by 60%",
        "Led migration to microservices architecture", 
        "Promoted twice in 18 months",
        "Mentored 10+ junior developers"
        // ALL ACHIEVEMENTS MENTIONED
    ],
    
    "extraction_confidence": 0.95
}}

CRITICAL REMINDERS:
- Arrays can have ANY number of items - extract them ALL
- If work_experience has 12 jobs, include all 12
- If education has 4 degrees/bootcamps, include all 4  
- If they list 50+ skills, extract all 50+
- CALCULATE experience by adding up job durations (years between start/end dates)
- Look for EVERY technical skill: JIRA, Jenkins, TensorFlow, Hadoop, Spring Boot, etc.
- Missing fields should be null or empty array []
- Don't summarize or limit - be exhaustive and comprehensive
- Set extraction_confidence based on how much info you found (0.9+ if comprehensive)

Resume Text:
---
{resume_text}
---

Extract everything. Calculate experience years properly. Return ONLY valid JSON.
"""


RESUME_EXTRACTION_PROMPT_V6 = """
You are an expert resume parser. Extract ALL information from this resume comprehensively and accurately.

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON (no comments, no additional text)
2. Extract ALL work experiences, education, skills, and achievements
3. Calculate total_experience_years precisely using date math
4. Handle various date formats and overlapping employment
5. Be exhaustive - capture every skill, project, and detail mentioned

EXPERIENCE CALCULATION RULES:
Use current year 2025 for "Present", "Current", "Now" calculations.

Date Examples:
- "2019 - 2023" → 4.0 years
- "Jan 2019 - Dec 2022" → 4.0 years  
- "Mar 2020 - Present" → 4.8 years (2025.0 - 2020.25)
- "Aug 2021 - Jun 2023" → 1.8 years (2023.5 - 2021.67)
- "2018 - 2019" (year only) → 1.0 year

Multiple Jobs: Add all durations together, including internships and part-time work.

CONFIDENCE SCORING:
- 0.9-1.0: Found name, email, 3+ jobs, 10+ skills, clear dates
- 0.7-0.89: Found most key info, some missing fields
- 0.5-0.69: Found basic info but significant gaps
- 0.3-0.49: Limited information extracted
- 0.1-0.29: Very little information found

EXAMPLE INPUT:
"John Smith
Software Engineer
john.smith@email.com
(555) 123-4567

EXPERIENCE
Senior Developer, TechCorp (2020-Present)
- Built scalable APIs using Python and Django
- Managed team of 4 developers

Junior Developer, StartupXYZ (2018-2020)  
- Developed React applications
- Used AWS and Docker for deployment

EDUCATION
BS Computer Science, MIT (2018)

SKILLS
Python, React, AWS, Docker, Leadership"

EXAMPLE OUTPUT:
{{
  "name": "John Smith",
  "email": "john.smith@email.com", 
  "phone": "(555) 123-4567",
  "location": null,
  "current_title": "Senior Developer",
  "desired_roles": [],
  "total_experience_years": 7.0,
  "technical_skills": ["Python", "Django", "React", "AWS", "Docker"],
  "soft_skills": ["Leadership"],
  "work_experience": [
    {{
      "company": "TechCorp",
      "title": "Senior Developer", 
      "duration": "2020-Present",
      "description": "Built scalable APIs using Python and Django. Managed team of 4 developers",
      "technologies": ["Python", "Django"]
    }},
    {{
      "company": "StartupXYZ",
      "title": "Junior Developer",
      "duration": "2018-2020", 
      "description": "Developed React applications. Used AWS and Docker for deployment",
      "technologies": ["React", "AWS", "Docker"]
    }}
  ],
  "education": [
    {{
      "degree": "BS Computer Science",
      "field": "Computer Science", 
      "school": "MIT",
      "graduation_year": "2018",
      "gpa": null
    }}
  ],
  "projects": [],
  "certifications": [],
  "languages": [],
  "clearance_level": null,
  "linkedin_url": null,
  "github_url": null, 
  "portfolio_url": null,
  "other_urls": [],
  "professional_summary": "Software Engineer with 7 years of experience in Python, React, and cloud technologies. Proven track record in API development and team leadership.",
  "key_achievements": ["Built scalable APIs", "Managed team of 4 developers"],
  "extraction_confidence": 0.85
}}

ERROR HANDLING:
- If dates are unclear, estimate reasonably based on context
- If no email found, set to null (don't guess)
- If skills are ambiguous, include them (better to over-extract)
- If unsure about field values, use null rather than empty strings
- Always return valid JSON even if some fields are missing

JSON STRUCTURE TEMPLATE:
{{
  "name": "string or null",
  "email": "string or null", 
  "phone": "string or null",
  "location": "string or null",
  "current_title": "string or null",
  "desired_roles": ["array of strings"],
  "total_experience_years": 0.0,
  "technical_skills": ["array of all technical skills found"],
  "soft_skills": ["array of all soft skills found"], 
  "work_experience": [
    {{
      "company": "string",
      "title": "string",
      "duration": "string", 
      "description": "string",
      "technologies": ["array of strings"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "field": "string",
      "school": "string", 
      "graduation_year": "string or null",
      "gpa": "string or null"
    }}
  ],
  "projects": [
    {{
      "name": "string",
      "description": "string",
      "technologies": ["array of strings"],
      "url": "string or null"
    }}
  ],
  "certifications": ["array of strings"],
  "languages": ["array of strings"],
  "clearance_level": "string or null",
  "linkedin_url": "string or null",
  "github_url": "string or null",
  "portfolio_url": "string or null", 
  "other_urls": ["array of strings"],
  "professional_summary": "string (generate if not explicit)",
  "key_achievements": ["array of strings"],
  "extraction_confidence": 0.0
}}

Resume Text:
---
{resume_text}
---

Extract all information. Return ONLY valid JSON.
"""

# ==============================================================================
# QUERY INTELLIGENCE PROMPTS
# ==============================================================================

QUERY_INTENT_PARSING_PROMPT = """
You are an expert recruiter search assistant. Parse the following natural language query into structured search intent.

QUERY: "{query}"

ROLE IDENTIFICATION GUIDELINES:
- "web developer", "frontend", "UI" → frontend_developer
- "backend", "server", "API" → backend_developer  
- "fullstack", "full-stack", "full stack" → fullstack_developer
- "mobile", "iOS", "Android", "React Native" → mobile_developer
- "DevOps", "infrastructure", "deployment" → devops_engineer
- "cloud", "AWS", "Azure", "GCP" → cloud_engineer
- "data scientist", "ML", "machine learning" → data_scientist
- "data engineer", "ETL", "pipeline" → data_engineer
- "QA", "test", "automation" → qa_engineer
- "product manager", "PM" → product_manager
- "designer", "UX", "UI designer" → designer
- "security", "cybersecurity" → security_engineer

EXPERIENCE LEVEL DETECTION:
- "junior", "entry", "entry-level", "new grad" → junior
- "mid", "mid-level", "intermediate", "2-5 years" → mid
- "senior", "sr", "experienced", "5+ years" → senior
- "lead", "team lead", "tech lead" → lead
- "principal", "staff", "architect" → principal

SKILL EXPANSION RULES:
- Include obvious related skills (React → JavaScript, HTML, CSS)
- Separate required vs preferred skills
- Categorize skills appropriately
- Include common synonyms

EXPERIENCE PARSING:
- "5+ years" → min: 5, max: null
- "2-5 years" → min: 2, max: 5
- "senior" implies 5+ years typically
- "junior" implies 0-3 years typically

LOCATION NORMALIZATION:
- Handle various formats: "San Francisco", "SF", "Bay Area"
- Extract city, state, country if clear
- Mark confidence based on specificity

Return ONLY valid JSON matching this schema:
{{
  "role_type": "frontend_developer|backend_developer|fullstack_developer|mobile_developer|devops_engineer|cloud_engineer|data_scientist|data_engineer|ml_engineer|qa_engineer|product_manager|designer|security_engineer|generic|null",
  "role_keywords": ["keyword1", "keyword2"],
  "experience_level": "junior|mid|senior|lead|principal|null",
  "experience_years_min": number_or_null,
  "experience_years_max": number_or_null,
  "required_skills": [
    {{
      "skill": "skill_name",
      "category": "programming_language|framework|database|cloud_platform|tool|methodology|domain_knowledge|null",
      "confidence_score": 0.0_to_1.0,
      "is_exact_match": true_or_false,
      "synonyms": ["alt1", "alt2"]
    }}
  ],
  "preferred_skills": [
    {{
      "skill": "skill_name", 
      "category": "programming_language|framework|database|cloud_platform|tool|methodology|domain_knowledge|null",
      "confidence_score": 0.0_to_1.0,
      "is_exact_match": true_or_false,
      "synonyms": ["alt1", "alt2"]
    }}
  ],
  "excluded_skills": ["skill1", "skill2"],
  "location_match": {{
    "original_query": "location_from_query",
    "normalized_location": "cleaned_location",
    "city": "city_name",
    "state": "state_name", 
    "country": "country_name",
    "confidence_score": 0.0_to_1.0,
    "is_valid": true_or_false,
    "suggested_radius_km": number_or_null
  }},
  "confidence_score": 0.0_to_1.0,
  "is_empty_query": true_or_false,
  "parsing_errors": ["error1", "error2"],
  "additional_filters": {{}}
}}

EXAMPLES:

Query: "React developers in Boston"
Output: {{
  "role_type": "frontend_developer",
  "role_keywords": ["react", "developers"],
  "experience_level": null,
  "experience_years_min": null,
  "experience_years_max": null,
  "required_skills": [
    {{
      "skill": "react",
      "category": "framework",
      "confidence_score": 1.0,
      "is_exact_match": true,
      "synonyms": ["reactjs", "react.js"]
    }},
    {{
      "skill": "javascript",
      "category": "programming_language", 
      "confidence_score": 0.9,
      "is_exact_match": false,
      "synonyms": ["js", "ecmascript"]
    }}
  ],
  "preferred_skills": [
    {{
      "skill": "typescript",
      "category": "programming_language",
      "confidence_score": 0.7,
      "is_exact_match": false,
      "synonyms": ["ts"]
    }}
  ],
  "excluded_skills": [],
  "location_match": {{
    "original_query": "Boston",
    "normalized_location": "Boston, MA, USA",
    "city": "Boston",
    "state": "Massachusetts",
    "country": "USA",
    "confidence_score": 0.95,
    "is_valid": true,
    "suggested_radius_km": 50
  }},
  "confidence_score": 0.92,
  "is_empty_query": false,
  "parsing_errors": [],
  "additional_filters": {{}}
}}

Query: "senior python engineers with 5+ years"
Output: {{
  "role_type": "backend_developer",
  "role_keywords": ["senior", "python", "engineers"],
  "experience_level": "senior",
  "experience_years_min": 5,
  "experience_years_max": null,
  "required_skills": [
    {{
      "skill": "python",
      "category": "programming_language",
      "confidence_score": 1.0,
      "is_exact_match": true,
      "synonyms": ["py"]
    }}
  ],
  "preferred_skills": [
    {{
      "skill": "django",
      "category": "framework",
      "confidence_score": 0.6,
      "is_exact_match": false,
      "synonyms": []
    }},
    {{
      "skill": "fastapi",
      "category": "framework", 
      "confidence_score": 0.6,
      "is_exact_match": false,
      "synonyms": []
    }}
  ],
  "excluded_skills": [],
  "location_match": null,
  "confidence_score": 0.88,
  "is_empty_query": false,
  "parsing_errors": [],
  "additional_filters": {{}}
}}

Be precise and conservative with confidence scores. Return ONLY the JSON object.
"""

SKILL_EXPANSION_PROMPT = """
You are a technical recruiter expert. Given a role type, expand the skills that would typically be required or preferred for that role.

ROLE TYPE: {role_type}
MENTIONED SKILLS: {mentioned_skills}

Rules:
1. Include core technical skills for the role
2. Add complementary skills that typically go together
3. Include both required (must-have) and preferred (nice-to-have) skills
4. Consider current industry standards (2024-2025)
5. Don't duplicate skills already mentioned
6. Categorize skills appropriately

Return ONLY valid JSON:
{{
  "additional_required_skills": [
    {{
      "skill": "skill_name",
      "category": "programming_language|framework|database|cloud_platform|tool|methodology|domain_knowledge",
      "confidence_score": 0.0_to_1.0,
      "is_exact_match": false,
      "synonyms": ["alt1", "alt2"]
    }}
  ],
  "additional_preferred_skills": [
    {{
      "skill": "skill_name",
      "category": "programming_language|framework|database|cloud_platform|tool|methodology|domain_knowledge", 
      "confidence_score": 0.0_to_1.0,
      "is_exact_match": false,
      "synonyms": ["alt1", "alt2"]
    }}
  ]
}}

Example for frontend_developer with mentioned React:
{{
  "additional_required_skills": [
    {{
      "skill": "javascript",
      "category": "programming_language",
      "confidence_score": 0.95,
      "is_exact_match": false,
      "synonyms": ["js", "ecmascript"]
    }},
    {{
      "skill": "html",
      "category": "programming_language",
      "confidence_score": 0.9,
      "is_exact_match": false,
      "synonyms": ["html5"]
    }},
    {{
      "skill": "css",
      "category": "programming_language", 
      "confidence_score": 0.9,
      "is_exact_match": false,
      "synonyms": ["css3", "stylesheets"]
    }}
  ],
  "additional_preferred_skills": [
    {{
      "skill": "typescript",
      "category": "programming_language",
      "confidence_score": 0.8,
      "is_exact_match": false,
      "synonyms": ["ts"]
    }},
    {{
      "skill": "webpack",
      "category": "tool",
      "confidence_score": 0.6,
      "is_exact_match": false,
      "synonyms": ["bundler"]
    }}
  ]
}}
"""

LOCATION_NORMALIZATION_PROMPT = """
You are a geographic location expert. Normalize the following location query for recruiting searches.

LOCATION QUERY: "{location}"

Rules:
1. Handle common abbreviations (SF → San Francisco, NYC → New York City)
2. Extract city, state/province, country when possible
3. Suggest reasonable search radius based on location type
4. Handle metropolitan areas appropriately
5. Mark confidence based on specificity and clarity
6. Handle ambiguous locations (e.g., "Portland" could be OR or ME)

Return ONLY valid JSON:
{{
  "original_query": "location_input",
  "normalized_location": "Full Location Name",
  "city": "City Name",
  "state": "State/Province Name",
  "country": "Country Name",
  "confidence_score": 0.0_to_1.0,
  "is_valid": true_or_false,
  "suggested_radius_km": number_or_null,
  "ambiguity_notes": "explanation_if_ambiguous"
}}

Examples:

Input: "SF"
Output: {{
  "original_query": "SF",
  "normalized_location": "San Francisco, CA, USA",
  "city": "San Francisco",
  "state": "California", 
  "country": "USA",
  "confidence_score": 0.95,
  "is_valid": true,
  "suggested_radius_km": 50,
  "ambiguity_notes": null
}}

Input: "Bay Area"
Output: {{
  "original_query": "Bay Area",
  "normalized_location": "San Francisco Bay Area, CA, USA",
  "city": null,
  "state": "California",
  "country": "USA", 
  "confidence_score": 0.9,
  "is_valid": true,
  "suggested_radius_km": 100,
  "ambiguity_notes": "Metropolitan area covering multiple cities"
}}

Input: "Portland"
Output: {{
  "original_query": "Portland",
  "normalized_location": "Portland, OR, USA",
  "city": "Portland",
  "state": "Oregon",
  "country": "USA",
  "confidence_score": 0.7,
  "is_valid": true,
  "suggested_radius_km": 50,
  "ambiguity_notes": "Could be Portland, OR or Portland, ME - defaulting to OR (larger tech hub)"
}}
"""
