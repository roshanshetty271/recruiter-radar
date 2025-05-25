"""
API usage examples for documentation
"""

SEARCH_EXAMPLES = {
    "basic_search": {
        "summary": "Basic AI search",
        "description": "Search for Python developers",
        "value": {"q": "Python developers with 5 years experience", "limit": 10},
    },
    "filtered_search": {
        "summary": "Search with filters",
        "description": "Search with all filters applied",
        "value": {
            "q": "senior engineers who love startups",
            "limit": 20,
            "visa_status": "US Citizen",
            "location": "San Francisco",
            "min_experience": 5,
            "skills": "Python,Docker,Kubernetes",
        },
    },
    "skill_focused": {
        "summary": "Skill-specific search",
        "description": "Find AI/ML specialists",
        "value": {
            "q": "machine learning engineers with NLP experience",
            "skills": "PyTorch,TensorFlow,Transformers",
        },
    },
}

OUTREACH_EXAMPLES = {
    "professional": {
        "summary": "Professional tone",
        "description": "Standard professional outreach",
        "value": {
            "job_role_title": "Senior Python Developer",
            "job_role_description": "Lead our backend team in building scalable APIs",
            "tone": "professional and friendly",
            "company_context": "Series B SaaS startup with great culture",
            "additional_instructions": "Mention their open source contributions",
        },
    },
    "startup_casual": {
        "summary": "Startup casual",
        "description": "More casual tone for startup culture",
        "value": {
            "job_role_title": "Founding Engineer",
            "tone": "enthusiastic and casual",
            "company_context": "Early stage AI startup, small team, huge impact",
        },
    },
    "executive": {
        "summary": "Executive role",
        "description": "For senior/executive positions",
        "value": {
            "job_role_title": "VP of Engineering",
            "job_role_description": "Build and lead our entire engineering organization",
            "tone": "professional and executive",
            "company_context": "Unicorn fintech company preparing for IPO",
        },
    },
}
