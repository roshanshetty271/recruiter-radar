#!/usr/bin/env python3
"""
🚨 NUCLEAR AI EXTRACTION TEST
Quick test script to debug AI extraction issues.
"""

import asyncio
import sys
import os
import logging

# Setup logging to see everything
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add backend to path
sys.path.append("backend")

from app.services.llm_service import LLMService
from app.services.ai_extraction_service import AIExtractionService
from app.core.config import settings

# Sample resume text for testing - REAL RENATA VOSS RESUME
SAMPLE_RESUME = """
RENATA VOSS
DIRECTOR OF SOFTWARE ENGINEERING

CONTACT
r.voss@email.com
(123) 456-7890
San Jose, CA
LinkedIn
Github

EDUCATION
Bachelor of Science
Software Engineering
California Institute of Technology
2006 - 2010
Pasadena, CA

SKILLS
JIRA 
Amazon Web Services (AWS)
Jenkins
TensorFlow
Spring Boot
Apache Hadoop
IDPS
React Native
Selenium
Oracle

WORK EXPERIENCE

Director of Software Engineering
Adobe
2019 - current / San Jose, CA
• Managed cross-functional team on Jira, increasing production velocity by 23%
• Integrated IDPS into systems, which decreased instances of successful socially engineered attacks to less than 1%
• Boosted processes through Jenkins-backed workflows that improved the quality of outcomes by a 54% margin
• Achieved a 97% Net Promoter Score and a 4.7 out of 5 rating from end users for error-free end products

Senior Engineering Manager
PayPal
2014 - 2019 / San Jose, CA
• Resolved app incompatibility issues with some mobile devices using AWS, reducing user-reporting incidences by 92%
• Incorporated agile best practices into core processes, which reduced average production cycle time by 17% across projects
• Decreased mobile app density defects by 31% by integrating React Native UI elements
• Worked within budget and timelines to deliver user-centric solutions and maintained a user satisfaction rating of 94% through customer feedback surveys

Principal Software Engineer
Intel
2010 - 2014 / Santa Clara, CA
• Optimized storage and dataset processing through Apache Hadoop, resulting in a 47% increase in concurrent user capacity
• Automated web applications testing across browsers with Selenium that shrank user-reported defects by 68%
• Led a team of 4 software engineers to create and upgrade databases on Oracle with a consistent 98% on-time delivery rate
• Implemented cloud infrastructure optimizations, which decreased monthly hosting costs by 28% and boosted system reliability
"""


async def test_nuclear_extraction():
    """Test AI extraction with nuclear debugging."""
    print("🚨 STARTING NUCLEAR EXTRACTION TEST")
    print("=" * 80)

    try:
        # Initialize services
        llm_service = LLMService(settings)
        ai_extractor = AIExtractionService(llm_service)

        print(f"✅ Services initialized")
        print(f"📏 Sample resume length: {len(SAMPLE_RESUME)} characters")

        # Run extraction
        result = await ai_extractor.extract_resume_data(SAMPLE_RESUME)

        if result:
            print("\n" + "=" * 80)
            print("🎉 EXTRACTION RESULTS SUMMARY:")
            print("=" * 80)
            print(f"Name: {result.name}")
            print(f"Email: {result.email}")
            print(
                f"Technical Skills ({len(result.technical_skills)}): {result.technical_skills}"
            )
            print(f"Work Experience: {len(result.work_experience)} jobs")
            print(f"Total Experience: {result.total_experience_years} years")
            print(f"🎯 CONFIDENCE: {result.extraction_confidence:.2f}")

            # Detailed work experience
            print("\nWork Experience Details:")
            for i, job in enumerate(result.work_experience):
                print(f"  {i+1}. {job.title} at {job.company} ({job.duration})")

            if result.extraction_confidence < 0.7:
                print(f"\n🚨 LOW CONFIDENCE DETECTED!")
                print(f"   This will help us understand why...")

        else:
            print("❌ EXTRACTION FAILED - NO RESULT")

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_nuclear_extraction())
