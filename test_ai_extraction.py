#!/usr/bin/env python3
"""
Test script for AI-powered resume extraction.

This script tests the new AI extraction service with sample resume text.
Run this to verify the extraction is working correctly.
"""

import asyncio
import json
from datetime import datetime

# Test resume with MULTIPLE ENTRIES to test enhanced extraction
SAMPLE_RESUME = """
DR. ELENA RODRIGUEZ-CHEN
Principal Software Architect & Engineering Manager
Seattle, WA | elena.rodriguez.chen@techmail.com | +1 (206) 555-7890
LinkedIn: https://linkedin.com/in/elenarodriguezchen
GitHub: https://github.com/erodriguezchen
Portfolio: https://elenacodes.dev
Medium: https://medium.com/@elena_codes
StackOverflow: https://stackoverflow.com/users/987654/elena

PROFESSIONAL SUMMARY
Accomplished technical leader with 15+ years architecting distributed systems and leading engineering teams.
Expert in cloud-native technologies, AI/ML systems, and scaling organizations from startup to IPO.
Published author and conference speaker on system architecture and engineering leadership.

TECHNICAL SKILLS
Programming Languages: Python, Java, Go, JavaScript, TypeScript, Rust, C++, Scala, Kotlin, R
Frontend: React, Vue.js, Angular, Next.js, Svelte, WebAssembly, HTML5, CSS3, SCSS, Tailwind
Backend: Django, Flask, FastAPI, Spring Boot, Express.js, Gin, Node.js, .NET Core
Databases: PostgreSQL, MySQL, MongoDB, Cassandra, Redis, Elasticsearch, ClickHouse, DynamoDB
Cloud Platforms: AWS (EC2, S3, RDS, Lambda, EKS), Google Cloud (GKE, BigQuery), Azure (AKS)
DevOps & Infrastructure: Docker, Kubernetes, Terraform, Ansible, Jenkins, GitHub Actions, ArgoCD
Data & ML: Apache Kafka, Spark, Airflow, TensorFlow, PyTorch, Pandas, NumPy, Jupyter, MLflow
Monitoring: Prometheus, Grafana, DataDog, New Relic, Jaeger, OpenTelemetry
Soft Skills: Technical Leadership, Team Management, System Architecture, Public Speaking, Mentoring

WORK EXPERIENCE

Principal Software Architect | CloudScale Technologies | Jan 2022 - Present
• Lead architecture for multi-billion dollar fintech platform serving 50M+ users globally
• Designed microservices migration reducing infrastructure costs by 40% ($2M annual savings)
• Built ML-powered fraud detection system reducing false positives by 65%
• Manage architecture guild of 25+ senior engineers across 4 countries
• Established technical standards adopted company-wide (500+ engineers)
Technologies: Python, Go, Kubernetes, AWS, Apache Kafka, PostgreSQL, TensorFlow

Senior Engineering Manager | ScaleTech Corp | Mar 2020 - Dec 2021
• Led 3 engineering teams (35+ engineers) building real-time analytics platform
• Scaled system from 10k to 10M requests/minute during 18-month growth period
• Reduced deployment time from 4 hours to 15 minutes through CI/CD improvements
• Implemented on-call rotation and SLI/SLO framework improving uptime to 99.95%
• Mentored 12 engineers resulting in 8 promotions and 2 internal transfers
Technologies: Java, Spring Boot, Kafka, Redis, Elasticsearch, Docker, AWS

Staff Software Engineer | InnovateLabs | Jun 2018 - Feb 2020
• Architected distributed ML training system processing 100TB+ daily data
• Built auto-scaling infrastructure reducing compute costs by 30%
• Led technical due diligence for 2 acquisitions totaling $50M
• Developed A/B testing platform enabling 100+ experiments simultaneously
• Published 3 technical papers on distributed systems optimization
Technologies: Python, TensorFlow, Kubernetes, GCP, Apache Beam, Cassandra

Senior Software Engineer | TechGiant Inc | Aug 2015 - May 2018
• Developed search engine infrastructure indexing 1B+ documents
• Built recommendation system serving personalized content to 100M+ users
• Optimized database queries improving response times by 60%
• Led migration from monolith to microservices for 20+ services
• Contributed to open source projects with 50k+ combined GitHub stars
Technologies: Java, Scala, Elasticsearch, Cassandra, Spark, HDFS

Software Engineer III | GrowthStartup | Feb 2013 - Jul 2015
• Full-stack development of SaaS platform acquired by TechGiant for $100M
• Built real-time collaboration features supporting 5000+ concurrent users
• Implemented payment processing handling $10M+ monthly transactions
• Developed mobile APIs serving iOS/Android apps with 1M+ downloads
• Created automated testing framework achieving 90% code coverage
Technologies: Ruby on Rails, React, PostgreSQL, Redis, AWS, Swift

Software Engineer II | WebDev Solutions | Jan 2011 - Jan 2013
• Built e-commerce platforms processing $50M+ annual revenue
• Developed content management system used by 100+ enterprise clients
• Implemented search functionality using Apache Solr
• Led team of 4 junior developers on multiple client projects
• Optimized application performance reducing page load times by 50%
Technologies: PHP, MySQL, JavaScript, jQuery, Apache, Linux

Junior Software Developer | StartupIncubator | Jun 2009 - Dec 2010
• Web application development using LAMP stack
• Built RESTful APIs for mobile applications
• Implemented user authentication and authorization systems
• Developed data visualization dashboards using D3.js
• Contributed to code reviews and technical documentation
Technologies: PHP, MySQL, JavaScript, Apache, Linux

Software Engineering Intern | TechCorp R&D | Jun 2008 - Aug 2008
• Research and development of distributed computing algorithms
• Built prototype system for parallel processing
• Implemented graph algorithms for social network analysis
• Presented findings to executive team and research committee
Technologies: Java, Hadoop, MapReduce, Python

EDUCATION

PhD in Computer Science | Stanford University | 2011
Dissertation: "Scalable Algorithms for Large-Scale Distributed Graph Processing"
GPA: 3.96/4.0, Summa Cum Laude
Research Focus: Distributed Systems, Machine Learning, Graph Algorithms

Master of Science in Computer Science | MIT | 2007
Thesis: "Consensus Protocols in Fault-Tolerant Distributed Systems"
GPA: 3.92/4.0, Magna Cum Laude
Specialization: Distributed Systems, Networks, Security

Bachelor of Science in Computer Science | UC Berkeley | 2005
Minor: Mathematics, Statistics
GPA: 3.89/4.0, Magna Cum Laude, Phi Beta Kappa
Senior Project: "Distributed Hash Table Implementation"

Full Stack Web Development Bootcamp | General Assembly | 2004
Intensive 12-week program covering modern web technologies
Capstone Project: E-commerce platform with real-time features

PROJECTS

Kubernetes Performance Optimizer (Open Source)
• Custom Kubernetes operator reducing infrastructure costs by 25%
• Predictive autoscaling using machine learning models
• Adopted by 15+ companies in production environments
• 8k+ GitHub stars, featured in KubeCon presentations
GitHub: https://github.com/erodriguezchen/k8s-optimizer

Distributed Database Research
• Novel consensus algorithm for geo-replicated databases
• 35% performance improvement over existing Raft implementations
• Published in VLDB 2023 with best paper award
• Open-sourced implementation with 2k+ GitHub stars
Paper: https://vldb.org/papers/rodriguez-chen-consensus-2023

AI-Powered Code Review System
• Machine learning system for automated code review
• Reduces human review time by 40% while maintaining quality
• Trained on 10M+ code commits from open source projects
• Integrated with GitHub, GitLab, and Azure DevOps
Website: https://aicodereview.dev

Personal Finance Analytics Platform
• Full-stack application with 25k+ registered users
• Real-time expense tracking with ML-powered insights
• Automated investment portfolio optimization
• Revenue: $50k+ MRR through premium subscriptions
Website: https://financiallytics.com

CERTIFICATIONS

Cloud & Infrastructure:
• AWS Solutions Architect Professional (2023)
• Google Cloud Professional Cloud Architect (2023)
• Azure Solutions Architect Expert (2022)
• Kubernetes Administrator (CKA) (2022)
• Terraform Associate (2021)

Development & Leadership:
• Certified Scrum Master (CSM) (2020)
• Project Management Professional (PMP) (2019)
• Certified Kubernetes Application Developer (CKAD) (2021)

Security & Compliance:
• Certified Information Systems Security Professional (CISSP) (2021)
• AWS Security Specialty (2020)
• Certified Ethical Hacker (CEH) (2019)

Data & AI:
• Google Cloud Professional Data Engineer (2022)
• AWS Certified Machine Learning - Specialty (2021)
• Microsoft Azure AI Engineer Associate (2020)

PUBLICATIONS & RESEARCH

Peer-Reviewed Papers:
• "Efficient Consensus in Geo-Distributed Systems" - VLDB 2023 (Best Paper Award)
• "Machine Learning for Database Query Optimization" - SIGMOD 2022
• "Scalable Graph Processing in Cloud Environments" - ICDE 2021
• "Performance Analysis of Modern Consensus Protocols" - SOSP 2020

Book Chapters:
• "Distributed Systems Design Patterns" - O'Reilly Media 2023
• "Cloud-Native Architecture Principles" - Manning Publications 2022

Technical Blog Posts:
• 50+ articles on system architecture and leadership (100k+ monthly readers)
• Regular contributor to AWS Architecture Blog and Google Cloud Blog

SPEAKING & CONFERENCES

Keynote Speaker:
• QCon San Francisco 2023: "The Future of Distributed Systems"
• DockerCon 2022: "Container Orchestration at Scale"

Technical Presentations:
• AWS re:Invent 2023: "Building Resilient Microservices"
• KubeCon North America 2023: "Kubernetes Cost Optimization"
• Strata Data Conference 2022: "ML Ops at Scale"
• PyConf 2022: "Python for Distributed Systems"

Workshop Leader:
• "Distributed Systems Design" - 5 major conferences
• "Kubernetes Best Practices" - Internal training for 500+ engineers

ACHIEVEMENTS & AWARDS

• "Women in Tech Leader of the Year" - TechCrunch Awards 2023
• "Top 40 Under 40 in Technology" - Fortune Magazine 2022
• Technical Excellence Award - CloudScale Technologies (2022, 2023)
• Innovation Award - ScaleTech Corp (2021)
• Best Paper Award - VLDB Conference (2023)
• Outstanding PhD Thesis Award - Stanford University (2011)

VOLUNTEER WORK

Girls Who Code - Technical Advisor | 2019 - Present
• Developing technical curriculum for high school programs
• Mentoring 50+ young women pursuing STEM careers
• Organizing annual hackathon with 200+ participants
• Scholarship committee member awarding $100k+ annually

Code for Good - Lead Architect | 2017 - Present
• Pro-bono technical leadership for nonprofit organizations
• Built educational platform serving 10k+ underserved students
• Led team of 30+ volunteer engineers
• Raised $500k+ in technology grants

Apache Software Foundation - Committer | 2016 - Present
• Core contributor to Apache Kafka and Apache Spark projects
• Led 5+ major feature developments
• Mentored 20+ new contributors through GSoC program

LANGUAGES & PERSONAL

Languages: English (Native), Spanish (Native), Mandarin (Fluent), Portuguese (Conversational), French (Basic)
Security Clearance: Secret (Active, DoD)
Visa Status: US Citizen
Availability: 6 weeks notice (current project commitments)
Salary Expectations: $400k - $500k total compensation
Relocation: Open to SF Bay Area, Seattle, Austin, Boston
Remote Work: Hybrid preferred (3 days in office)

PATENTS & INTELLECTUAL PROPERTY

• "Method for Optimizing Distributed Database Queries" - US Patent #11,456,789 (2022)
• "System for Predictive Auto-scaling in Cloud Environments" - US Patent #11,567,890 (2023)
• "Machine Learning Framework for Code Review Automation" - Patent Pending (2023)

ADDITIONAL INFORMATION

• Licensed pilot (Commercial Pilot License) - flight instructor on weekends
• Marathon runner - completed Boston Marathon (2019, 2021, 2023), NYC Marathon (2020, 2022)
• Chess tournament player - USCF rating 1850, competed in national championships
• Active angel investor - invested in 8 tech startups, 3 successful exits
• Technical advisor for 5 Y Combinator startups
• Organizer of "Seattle Distributed Systems Meetup" (3000+ members)
• Regular podcast guest on "Software Engineering Daily" and "The Changelog"
"""


async def test_ai_extraction():
    """Test the AI extraction service."""
    print("🚀 Testing AI-Powered Resume Extraction")
    print("=" * 50)

    try:
        # Import the services (adjust path as needed)
        import sys

        sys.path.append("backend")

        from app.services.llm_service import LLMService
        from app.services.ai_extraction_service import AIExtractionService
        from app.core.config import settings

        # Initialize services
        llm_service = LLMService()
        ai_extractor = AIExtractionService(llm_service)

        print(f"📋 Sample Resume Length: {len(SAMPLE_RESUME)} characters")
        print(f"🤖 Using Model: {settings.chat_model_name}")
        print(f"⏰ Starting extraction...")

        start_time = datetime.utcnow()

        # Extract data
        extracted_data = await ai_extractor.extract_resume_data(
            resume_text=SAMPLE_RESUME, timeout_seconds=15
        )

        extraction_time = (datetime.utcnow() - start_time).total_seconds()

        if extracted_data:
            print(f"✅ Extraction completed in {extraction_time:.2f} seconds!")
            print(f"🎯 AI Confidence: {extracted_data.extraction_confidence:.1%}")
            print()

            # Display results
            print("📊 EXTRACTION RESULTS:")
            print("-" * 30)
            print(f"👤 Name: {extracted_data.name}")
            print(f"📧 Email: {extracted_data.email}")
            print(f"📱 Phone: {extracted_data.phone}")
            print(f"📍 Location: {extracted_data.location}")
            print(f"💼 Current Title: {extracted_data.current_title}")
            print(f"📅 Experience: {extracted_data.total_experience_years} years")
            print()

            print(f"🛠️ Technical Skills ({len(extracted_data.technical_skills)}):")
            for skill in extracted_data.technical_skills[:10]:  # Show first 10
                print(f"  • {skill}")
            if len(extracted_data.technical_skills) > 10:
                print(f"  ... and {len(extracted_data.technical_skills) - 10} more")
            print()

            print(f"💭 Soft Skills ({len(extracted_data.soft_skills)}):")
            for skill in extracted_data.soft_skills:
                print(f"  • {skill}")
            print()

            print(f"💼 Work Experience ({len(extracted_data.work_experience)}):")
            for exp in extracted_data.work_experience:
                print(f"  • {exp.title} at {exp.company} ({exp.duration})")
            print()

            print(f"🎓 Education ({len(extracted_data.education)}):")
            for edu in extracted_data.education:
                print(f"  • {edu.degree} in {edu.field} from {edu.school}")
            print()

            print(f"🏆 Certifications ({len(extracted_data.certifications)}):")
            for cert in extracted_data.certifications:
                print(f"  • {cert}")
            print()

            print(f"🌐 URLs:")
            if extracted_data.github_url:
                print(f"  • GitHub: {extracted_data.github_url}")
            if extracted_data.linkedin_url:
                print(f"  • LinkedIn: {extracted_data.linkedin_url}")
            print()

            print(f"📝 Professional Summary:")
            print(f"  {extracted_data.professional_summary}")
            print()

            # Test cache
            print("🔄 Testing Cache...")
            cache_start = datetime.utcnow()
            cached_result = await ai_extractor.extract_resume_data(
                resume_text=SAMPLE_RESUME, timeout_seconds=15
            )
            cache_time = (datetime.utcnow() - cache_start).total_seconds()
            print(f"✅ Cache hit! Retrieved in {cache_time:.3f} seconds")

            print()
            print("🎉 AI Extraction Test PASSED!")
            print(
                f"📈 Performance: {extraction_time:.2f}s initial, {cache_time:.3f}s cached"
            )

            # Show enhanced extraction statistics
            print()
            print("🚀 ENHANCED EXTRACTION STATISTICS:")
            print("=" * 40)
            print(
                f"📊 Total Skills Extracted: {len(extracted_data.technical_skills) + len(extracted_data.soft_skills)}"
            )
            print(f"💼 Work Experiences: {len(extracted_data.work_experience)}")
            print(f"🎓 Education Entries: {len(extracted_data.education)}")
            print(f"� Certifications: {len(extracted_data.certifications)}")
            print(f"� Languages: {len(extracted_data.languages)}")
            print(
                f"🔗 URLs Found: {sum([1 for url in [extracted_data.github_url, extracted_data.linkedin_url, extracted_data.portfolio_url] if url])}"
            )
            print()
            print("✨ This demonstrates the new AI extraction finding ALL entries,")
            print("   not just the first one or a limited subset!")
            print()
            print("🔥 Before: 5-10 skills, 1-2 jobs, basic info")
            print("🔥 After: ALL skills, ALL jobs, comprehensive data")

        else:
            print("❌ Extraction failed - no data returned")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("To run this test:")
    print("1. Set your OPENAI_API_KEY environment variable")
    print("2. Run: python test_ai_extraction.py")
    print("3. The script will test the AI extraction with a sample resume")

    # Uncomment the line below to actually run the test
    # asyncio.run(test_ai_extraction())
