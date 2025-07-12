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

EXPERIENCE CALCULATION EXAMPLES:
- "Software Engineer at Google (2019 - 2023)" → 4 years
- "Director at Adobe (2019 - current)" → ~5 years (2024 - 2019)
- "Engineer (Jan 2015 - Dec 2017)" → 3 years  
- Multiple jobs: Add them up! 3 years + 2 years + 4 years = 9 years total

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
