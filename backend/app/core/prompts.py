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
