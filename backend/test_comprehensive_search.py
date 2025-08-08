"""
Comprehensive Search Test Suite - 200+ Test Cases
Tests SmartPatternMatcher system with varied queries, edge cases, and complex scenarios
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.smart_pattern_matcher import SmartPatternMatcher, MatchResult


class SearchTestSuite:
    """Comprehensive test suite for search functionality"""

    def __init__(self):
        self.matcher = SmartPatternMatcher()
        self.test_results = []
        self.stats = {
            "total_tests": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "avg_confidence": 0.0,
            "avg_response_time": 0.0,
            "skill_coverage": set(),
            "location_coverage": set(),
        }

    def get_test_queries(self) -> List[Dict[str, Any]]:
        """Generate 200+ comprehensive test queries"""

        test_queries = []

        # ===== CATEGORY 1: PROGRAMMING LANGUAGES (40 tests) =====
        programming_tests = [
            # Basic patterns
            {
                "query": "Java developers",
                "category": "programming",
                "expected_skill": "Java",
                "complexity": "simple",
            },
            {
                "query": "Python engineer",
                "category": "programming",
                "expected_skill": "Python",
                "complexity": "simple",
            },
            {
                "query": "JavaScript programmer",
                "category": "programming",
                "expected_skill": "JavaScript",
                "complexity": "simple",
            },
            {
                "query": "TypeScript developer",
                "category": "programming",
                "expected_skill": "TypeScript",
                "complexity": "simple",
            },
            {
                "query": "C++ engineers",
                "category": "programming",
                "expected_skill": "C++",
                "complexity": "simple",
            },
            {
                "query": "C# developer",
                "category": "programming",
                "expected_skill": "C#",
                "complexity": "simple",
            },
            {
                "query": "Go developers",
                "category": "programming",
                "expected_skill": "Go",
                "complexity": "simple",
            },
            {
                "query": "Rust programmer",
                "category": "programming",
                "expected_skill": "Rust",
                "complexity": "simple",
            },
            {
                "query": "Swift developer",
                "category": "programming",
                "expected_skill": "Swift",
                "complexity": "simple",
            },
            {
                "query": "Kotlin engineer",
                "category": "programming",
                "expected_skill": "Kotlin",
                "complexity": "simple",
            },
            # With experience
            {
                "query": "Senior Java developer",
                "category": "programming",
                "expected_skill": "Java",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "5+ years Python experience",
                "category": "programming",
                "expected_skill": "Python",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "Junior JavaScript developer",
                "category": "programming",
                "expected_skill": "JavaScript",
                "expected_experience": 1,
                "complexity": "medium",
            },
            {
                "query": "Python developer with 3 years",
                "category": "programming",
                "expected_skill": "Python",
                "expected_experience": 3,
                "complexity": "medium",
            },
            {
                "query": "Java skills over 7 years",
                "category": "programming",
                "expected_skill": "Java",
                "expected_experience": 7,
                "complexity": "medium",
            },
            # Natural language variations
            {
                "query": "Looking for Java expertise",
                "category": "programming",
                "expected_skill": "Java",
                "complexity": "medium",
            },
            {
                "query": "Need someone with Python skills",
                "category": "programming",
                "expected_skill": "Python",
                "complexity": "medium",
            },
            {
                "query": "Show me JavaScript talent",
                "category": "programming",
                "expected_skill": "JavaScript",
                "complexity": "medium",
            },
            {
                "query": "Find me a C++ expert",
                "category": "programming",
                "expected_skill": "C++",
                "complexity": "medium",
            },
            {
                "query": "Looking for Go programming skills",
                "category": "programming",
                "expected_skill": "Go",
                "complexity": "medium",
            },
            # Edge cases - variations and typos
            {
                "query": "java",
                "category": "programming",
                "expected_skill": "Java",
                "complexity": "simple",
            },
            {
                "query": "python",
                "category": "programming",
                "expected_skill": "Python",
                "complexity": "simple",
            },
            {
                "query": "javascript",
                "category": "programming",
                "expected_skill": "JavaScript",
                "complexity": "simple",
            },
            {
                "query": "Java dev",
                "category": "programming",
                "expected_skill": "Java",
                "complexity": "simple",
            },
            {
                "query": "Python dev",
                "category": "programming",
                "expected_skill": "Python",
                "complexity": "simple",
            },
            {
                "query": "JS developer",
                "category": "programming",
                "expected_skill": "JavaScript",
                "complexity": "simple",
            },
            {
                "query": "TypeScript dev",
                "category": "programming",
                "expected_skill": "TypeScript",
                "complexity": "simple",
            },
            {
                "query": "C# programmer",
                "category": "programming",
                "expected_skill": "C#",
                "complexity": "simple",
            },
            {
                "query": "golang developer",
                "category": "programming",
                "expected_skill": "Go",
                "complexity": "simple",
            },
            {
                "query": "rust engineer",
                "category": "programming",
                "expected_skill": "Rust",
                "complexity": "simple",
            },
            # Case insensitive
            {
                "query": "JAVA DEVELOPER",
                "category": "programming",
                "expected_skill": "Java",
                "complexity": "simple",
            },
            {
                "query": "python ENGINEER",
                "category": "programming",
                "expected_skill": "Python",
                "complexity": "simple",
            },
            {
                "query": "Javascript Developer",
                "category": "programming",
                "expected_skill": "JavaScript",
                "complexity": "simple",
            },
            # Alternative names
            {
                "query": "Golang developer",
                "category": "programming",
                "expected_skill": "Go",
                "complexity": "simple",
            },
            {
                "query": "Node.js developer",
                "category": "programming",
                "expected_skill": "Node.js",
                "complexity": "simple",
            },
            {
                "query": "NodeJS engineer",
                "category": "programming",
                "expected_skill": "Node.js",
                "complexity": "simple",
            },
            {
                "query": "PHP developer",
                "category": "programming",
                "expected_skill": "PHP",
                "complexity": "simple",
            },
            {
                "query": "Ruby developer",
                "category": "programming",
                "expected_skill": "Ruby",
                "complexity": "simple",
            },
            {
                "query": "Scala engineer",
                "category": "programming",
                "expected_skill": "Scala",
                "complexity": "simple",
            },
            {
                "query": "R developer",
                "category": "programming",
                "expected_skill": "R",
                "complexity": "simple",
            },
        ]
        test_queries.extend(programming_tests)

        # ===== CATEGORY 2: FRONTEND TECHNOLOGIES (35 tests) =====
        frontend_tests = [
            # React ecosystem
            {
                "query": "React developer",
                "category": "frontend",
                "expected_skill": "React",
                "complexity": "simple",
            },
            {
                "query": "React.js engineer",
                "category": "frontend",
                "expected_skill": "React",
                "complexity": "simple",
            },
            {
                "query": "ReactJS developer",
                "category": "frontend",
                "expected_skill": "React",
                "complexity": "simple",
            },
            {
                "query": "Senior React developer",
                "category": "frontend",
                "expected_skill": "React",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "React developer with 4 years",
                "category": "frontend",
                "expected_skill": "React",
                "expected_experience": 4,
                "complexity": "medium",
            },
            # Angular ecosystem
            {
                "query": "Angular developer",
                "category": "frontend",
                "expected_skill": "Angular",
                "complexity": "simple",
            },
            {
                "query": "Angular engineer",
                "category": "frontend",
                "expected_skill": "Angular",
                "complexity": "simple",
            },
            {
                "query": "AngularJS developer",
                "category": "frontend",
                "expected_skill": "Angular",
                "complexity": "simple",
            },
            {
                "query": "Angular 2+ developer",
                "category": "frontend",
                "expected_skill": "Angular",
                "complexity": "simple",
            },
            # Vue ecosystem
            {
                "query": "Vue developer",
                "category": "frontend",
                "expected_skill": "Vue.js",
                "complexity": "simple",
            },
            {
                "query": "Vue.js engineer",
                "category": "frontend",
                "expected_skill": "Vue.js",
                "complexity": "simple",
            },
            {
                "query": "VueJS developer",
                "category": "frontend",
                "expected_skill": "Vue.js",
                "complexity": "simple",
            },
            # Other frameworks
            {
                "query": "Svelte developer",
                "category": "frontend",
                "expected_skill": "Svelte",
                "complexity": "simple",
            },
            {
                "query": "Next.js developer",
                "category": "frontend",
                "expected_skill": "Next.js",
                "complexity": "simple",
            },
            {
                "query": "Gatsby developer",
                "category": "frontend",
                "expected_skill": "Gatsby",
                "complexity": "simple",
            },
            {
                "query": "Nuxt.js engineer",
                "category": "frontend",
                "expected_skill": "Nuxt.js",
                "complexity": "simple",
            },
            # Core web technologies
            {
                "query": "HTML5 developer",
                "category": "frontend",
                "expected_skill": "HTML5",
                "complexity": "simple",
            },
            {
                "query": "CSS3 developer",
                "category": "frontend",
                "expected_skill": "CSS3",
                "complexity": "simple",
            },
            {
                "query": "HTML developer",
                "category": "frontend",
                "expected_skill": "HTML5",
                "complexity": "simple",
            },
            {
                "query": "CSS developer",
                "category": "frontend",
                "expected_skill": "CSS3",
                "complexity": "simple",
            },
            # CSS frameworks
            {
                "query": "Bootstrap developer",
                "category": "frontend",
                "expected_skill": "Bootstrap",
                "complexity": "simple",
            },
            {
                "query": "Tailwind CSS developer",
                "category": "frontend",
                "expected_skill": "Tailwind CSS",
                "complexity": "simple",
            },
            {
                "query": "Sass developer",
                "category": "frontend",
                "expected_skill": "Sass",
                "complexity": "simple",
            },
            {
                "query": "LESS developer",
                "category": "frontend",
                "expected_skill": "LESS",
                "complexity": "simple",
            },
            # UI Libraries
            {
                "query": "Material-UI developer",
                "category": "frontend",
                "expected_skill": "Material-UI",
                "complexity": "simple",
            },
            {
                "query": "Ant Design developer",
                "category": "frontend",
                "expected_skill": "Ant Design",
                "complexity": "simple",
            },
            {
                "query": "Chakra UI developer",
                "category": "frontend",
                "expected_skill": "Chakra UI",
                "complexity": "simple",
            },
            # State management
            {
                "query": "Redux developer",
                "category": "frontend",
                "expected_skill": "Redux",
                "complexity": "simple",
            },
            {
                "query": "MobX developer",
                "category": "frontend",
                "expected_skill": "MobX",
                "complexity": "simple",
            },
            {
                "query": "Vuex developer",
                "category": "frontend",
                "expected_skill": "Vuex",
                "complexity": "simple",
            },
            # Role-based
            {
                "query": "Frontend developer",
                "category": "frontend",
                "expected_skill": "Frontend Development",
                "complexity": "medium",
            },
            {
                "query": "Front-end engineer",
                "category": "frontend",
                "expected_skill": "Frontend Development",
                "complexity": "medium",
            },
            {
                "query": "UI developer",
                "category": "frontend",
                "expected_skill": "UI Design",
                "complexity": "medium",
            },
            {
                "query": "Web developer",
                "category": "frontend",
                "expected_skill": "Frontend Development",
                "complexity": "medium",
            },
            {
                "query": "JavaScript frontend developer",
                "category": "frontend",
                "expected_skill": "JavaScript",
                "complexity": "medium",
            },
        ]
        test_queries.extend(frontend_tests)

        # ===== CATEGORY 3: BACKEND TECHNOLOGIES (30 tests) =====
        backend_tests = [
            # Node.js ecosystem
            {
                "query": "Node.js developer",
                "category": "backend",
                "expected_skill": "Node.js",
                "complexity": "simple",
            },
            {
                "query": "Express.js developer",
                "category": "backend",
                "expected_skill": "Express.js",
                "complexity": "simple",
            },
            {
                "query": "Fastify developer",
                "category": "backend",
                "expected_skill": "Fastify",
                "complexity": "simple",
            },
            {
                "query": "NestJS developer",
                "category": "backend",
                "expected_skill": "NestJS",
                "complexity": "simple",
            },
            # Python frameworks
            {
                "query": "Django developer",
                "category": "backend",
                "expected_skill": "Django",
                "complexity": "simple",
            },
            {
                "query": "Flask developer",
                "category": "backend",
                "expected_skill": "Flask",
                "complexity": "simple",
            },
            {
                "query": "FastAPI developer",
                "category": "backend",
                "expected_skill": "FastAPI",
                "complexity": "simple",
            },
            # Java frameworks
            {
                "query": "Spring Boot developer",
                "category": "backend",
                "expected_skill": "Spring Boot",
                "complexity": "simple",
            },
            {
                "query": "Spring Framework developer",
                "category": "backend",
                "expected_skill": "Spring Framework",
                "complexity": "simple",
            },
            # .NET ecosystem
            {
                "query": ".NET developer",
                "category": "backend",
                "expected_skill": ".NET Core",
                "complexity": "simple",
            },
            {
                "query": "ASP.NET developer",
                "category": "backend",
                "expected_skill": "ASP.NET",
                "complexity": "simple",
            },
            {
                "query": "dotnet developer",
                "category": "backend",
                "expected_skill": ".NET Core",
                "complexity": "simple",
            },
            # PHP frameworks
            {
                "query": "Laravel developer",
                "category": "backend",
                "expected_skill": "Laravel",
                "complexity": "simple",
            },
            {
                "query": "Symfony developer",
                "category": "backend",
                "expected_skill": "Symfony",
                "complexity": "simple",
            },
            {
                "query": "CodeIgniter developer",
                "category": "backend",
                "expected_skill": "CodeIgniter",
                "complexity": "simple",
            },
            # Ruby frameworks
            {
                "query": "Ruby on Rails developer",
                "category": "backend",
                "expected_skill": "Ruby on Rails",
                "complexity": "simple",
            },
            {
                "query": "Rails developer",
                "category": "backend",
                "expected_skill": "Ruby on Rails",
                "complexity": "simple",
            },
            {
                "query": "Sinatra developer",
                "category": "backend",
                "expected_skill": "Sinatra",
                "complexity": "simple",
            },
            # Go frameworks
            {
                "query": "Gin developer",
                "category": "backend",
                "expected_skill": "Gin",
                "complexity": "simple",
            },
            {
                "query": "Echo developer",
                "category": "backend",
                "expected_skill": "Echo",
                "complexity": "simple",
            },
            {
                "query": "Fiber developer",
                "category": "backend",
                "expected_skill": "Fiber",
                "complexity": "simple",
            },
            # API technologies
            {
                "query": "REST API developer",
                "category": "backend",
                "expected_skill": "REST API",
                "complexity": "simple",
            },
            {
                "query": "GraphQL developer",
                "category": "backend",
                "expected_skill": "GraphQL",
                "complexity": "simple",
            },
            {
                "query": "gRPC developer",
                "category": "backend",
                "expected_skill": "gRPC",
                "complexity": "simple",
            },
            # Role-based
            {
                "query": "Backend developer",
                "category": "backend",
                "expected_skill": "Backend Development",
                "complexity": "medium",
            },
            {
                "query": "Back-end engineer",
                "category": "backend",
                "expected_skill": "Backend Development",
                "complexity": "medium",
            },
            {
                "query": "Server developer",
                "category": "backend",
                "expected_skill": "Backend Development",
                "complexity": "medium",
            },
            {
                "query": "API developer",
                "category": "backend",
                "expected_skill": "REST API",
                "complexity": "medium",
            },
            # With experience
            {
                "query": "Senior Node.js developer",
                "category": "backend",
                "expected_skill": "Node.js",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "Django developer with 3+ years",
                "category": "backend",
                "expected_skill": "Django",
                "expected_experience": 3,
                "complexity": "medium",
            },
            {
                "query": "Spring Boot developer over 4 years",
                "category": "backend",
                "expected_skill": "Spring Boot",
                "expected_experience": 4,
                "complexity": "medium",
            },
        ]
        test_queries.extend(backend_tests)

        # ===== CATEGORY 4: DATABASES (25 tests) =====
        database_tests = [
            # SQL databases
            {
                "query": "PostgreSQL developer",
                "category": "database",
                "expected_skill": "PostgreSQL",
                "complexity": "simple",
            },
            {
                "query": "MySQL developer",
                "category": "database",
                "expected_skill": "MySQL",
                "complexity": "simple",
            },
            {
                "query": "SQL Server developer",
                "category": "database",
                "expected_skill": "SQL Server",
                "complexity": "simple",
            },
            {
                "query": "Oracle developer",
                "category": "database",
                "expected_skill": "Oracle",
                "complexity": "simple",
            },
            {
                "query": "SQLite developer",
                "category": "database",
                "expected_skill": "SQLite",
                "complexity": "simple",
            },
            # NoSQL databases
            {
                "query": "MongoDB developer",
                "category": "database",
                "expected_skill": "MongoDB",
                "complexity": "simple",
            },
            {
                "query": "Cassandra developer",
                "category": "database",
                "expected_skill": "Cassandra",
                "complexity": "simple",
            },
            {
                "query": "DynamoDB developer",
                "category": "database",
                "expected_skill": "DynamoDB",
                "complexity": "simple",
            },
            {
                "query": "Redis developer",
                "category": "database",
                "expected_skill": "Redis",
                "complexity": "simple",
            },
            {
                "query": "Elasticsearch developer",
                "category": "database",
                "expected_skill": "Elasticsearch",
                "complexity": "simple",
            },
            # Graph databases
            {
                "query": "Neo4j developer",
                "category": "database",
                "expected_skill": "Neo4j",
                "complexity": "simple",
            },
            {
                "query": "ArangoDB developer",
                "category": "database",
                "expected_skill": "ArangoDB",
                "complexity": "simple",
            },
            # Time series databases
            {
                "query": "InfluxDB developer",
                "category": "database",
                "expected_skill": "InfluxDB",
                "complexity": "simple",
            },
            {
                "query": "TimescaleDB developer",
                "category": "database",
                "expected_skill": "TimescaleDB",
                "complexity": "simple",
            },
            # Cloud databases
            {
                "query": "Snowflake developer",
                "category": "database",
                "expected_skill": "Snowflake",
                "complexity": "simple",
            },
            {
                "query": "BigQuery developer",
                "category": "database",
                "expected_skill": "BigQuery",
                "complexity": "simple",
            },
            {
                "query": "Redshift developer",
                "category": "database",
                "expected_skill": "Redshift",
                "complexity": "simple",
            },
            # Variations
            {
                "query": "Postgres developer",
                "category": "database",
                "expected_skill": "PostgreSQL",
                "complexity": "simple",
            },
            {
                "query": "Mongo developer",
                "category": "database",
                "expected_skill": "MongoDB",
                "complexity": "simple",
            },
            {
                "query": "SQL developer",
                "category": "database",
                "expected_skill": "SQL",
                "complexity": "simple",
            },
            # With experience
            {
                "query": "PostgreSQL DBA with 5+ years",
                "category": "database",
                "expected_skill": "PostgreSQL",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "Senior MongoDB developer",
                "category": "database",
                "expected_skill": "MongoDB",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "Redis developer over 3 years",
                "category": "database",
                "expected_skill": "Redis",
                "expected_experience": 3,
                "complexity": "medium",
            },
            # Role-based
            {
                "query": "Database administrator",
                "category": "database",
                "expected_skill": "SQL",
                "complexity": "medium",
            },
            {
                "query": "DBA",
                "category": "database",
                "expected_skill": "SQL",
                "complexity": "medium",
            },
        ]
        test_queries.extend(database_tests)

        # ===== CATEGORY 5: CLOUD & DEVOPS (30 tests) =====
        cloud_devops_tests = [
            # Cloud platforms
            {
                "query": "AWS developer",
                "category": "cloud",
                "expected_skill": "AWS",
                "complexity": "simple",
            },
            {
                "query": "Azure developer",
                "category": "cloud",
                "expected_skill": "Azure",
                "complexity": "simple",
            },
            {
                "query": "Google Cloud developer",
                "category": "cloud",
                "expected_skill": "Google Cloud Platform",
                "complexity": "simple",
            },
            {
                "query": "GCP developer",
                "category": "cloud",
                "expected_skill": "Google Cloud Platform",
                "complexity": "simple",
            },
            # Containerization
            {
                "query": "Docker developer",
                "category": "devops",
                "expected_skill": "Docker",
                "complexity": "simple",
            },
            {
                "query": "Kubernetes developer",
                "category": "devops",
                "expected_skill": "Kubernetes",
                "complexity": "simple",
            },
            {
                "query": "K8s engineer",
                "category": "devops",
                "expected_skill": "Kubernetes",
                "complexity": "simple",
            },
            {
                "query": "OpenShift developer",
                "category": "devops",
                "expected_skill": "OpenShift",
                "complexity": "simple",
            },
            # Infrastructure as Code
            {
                "query": "Terraform developer",
                "category": "devops",
                "expected_skill": "Terraform",
                "complexity": "simple",
            },
            {
                "query": "Ansible developer",
                "category": "devops",
                "expected_skill": "Ansible",
                "complexity": "simple",
            },
            {
                "query": "Puppet developer",
                "category": "devops",
                "expected_skill": "Puppet",
                "complexity": "simple",
            },
            {
                "query": "Chef developer",
                "category": "devops",
                "expected_skill": "Chef",
                "complexity": "simple",
            },
            # CI/CD
            {
                "query": "Jenkins developer",
                "category": "devops",
                "expected_skill": "Jenkins",
                "complexity": "simple",
            },
            {
                "query": "GitLab CI/CD developer",
                "category": "devops",
                "expected_skill": "GitLab CI/CD",
                "complexity": "simple",
            },
            {
                "query": "GitHub Actions developer",
                "category": "devops",
                "expected_skill": "GitHub Actions",
                "complexity": "simple",
            },
            {
                "query": "CircleCI developer",
                "category": "devops",
                "expected_skill": "CircleCI",
                "complexity": "simple",
            },
            # Monitoring
            {
                "query": "Prometheus developer",
                "category": "devops",
                "expected_skill": "Prometheus",
                "complexity": "simple",
            },
            {
                "query": "Grafana developer",
                "category": "devops",
                "expected_skill": "Grafana",
                "complexity": "simple",
            },
            {
                "query": "Datadog developer",
                "category": "devops",
                "expected_skill": "Datadog",
                "complexity": "simple",
            },
            {
                "query": "New Relic developer",
                "category": "devops",
                "expected_skill": "New Relic",
                "complexity": "simple",
            },
            # Role-based
            {
                "query": "DevOps engineer",
                "category": "devops",
                "expected_skill": "DevOps Engineering",
                "complexity": "medium",
            },
            {
                "query": "Site Reliability Engineer",
                "category": "devops",
                "expected_skill": "Site Reliability Engineering",
                "complexity": "medium",
            },
            {
                "query": "SRE",
                "category": "devops",
                "expected_skill": "Site Reliability Engineering",
                "complexity": "medium",
            },
            {
                "query": "Cloud architect",
                "category": "cloud",
                "expected_skill": "Cloud Architecture",
                "complexity": "medium",
            },
            {
                "query": "Infrastructure engineer",
                "category": "devops",
                "expected_skill": "Infrastructure",
                "complexity": "medium",
            },
            # With experience
            {
                "query": "Senior AWS engineer",
                "category": "cloud",
                "expected_skill": "AWS",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "Kubernetes engineer with 4+ years",
                "category": "devops",
                "expected_skill": "Kubernetes",
                "expected_experience": 4,
                "complexity": "medium",
            },
            {
                "query": "Docker developer over 2 years",
                "category": "devops",
                "expected_skill": "Docker",
                "expected_experience": 2,
                "complexity": "medium",
            },
            # Alternative names
            {
                "query": "Amazon Web Services developer",
                "category": "cloud",
                "expected_skill": "AWS",
                "complexity": "simple",
            },
            {
                "query": "Microsoft Azure developer",
                "category": "cloud",
                "expected_skill": "Azure",
                "complexity": "simple",
            },
        ]
        test_queries.extend(cloud_devops_tests)

        # ===== CATEGORY 6: AI & MACHINE LEARNING (20 tests) =====
        ai_ml_tests = [
            # ML frameworks
            {
                "query": "TensorFlow developer",
                "category": "ai_ml",
                "expected_skill": "TensorFlow",
                "complexity": "simple",
            },
            {
                "query": "PyTorch developer",
                "category": "ai_ml",
                "expected_skill": "PyTorch",
                "complexity": "simple",
            },
            {
                "query": "Keras developer",
                "category": "ai_ml",
                "expected_skill": "Keras",
                "complexity": "simple",
            },
            {
                "query": "Scikit-learn developer",
                "category": "ai_ml",
                "expected_skill": "Scikit-learn",
                "complexity": "simple",
            },
            # Data science libraries
            {
                "query": "Pandas developer",
                "category": "ai_ml",
                "expected_skill": "Pandas",
                "complexity": "simple",
            },
            {
                "query": "NumPy developer",
                "category": "ai_ml",
                "expected_skill": "NumPy",
                "complexity": "simple",
            },
            {
                "query": "Matplotlib developer",
                "category": "ai_ml",
                "expected_skill": "Matplotlib",
                "complexity": "simple",
            },
            {
                "query": "Seaborn developer",
                "category": "ai_ml",
                "expected_skill": "Seaborn",
                "complexity": "simple",
            },
            # Modern AI
            {
                "query": "OpenAI developer",
                "category": "ai_ml",
                "expected_skill": "OpenAI",
                "complexity": "simple",
            },
            {
                "query": "GPT-4 developer",
                "category": "ai_ml",
                "expected_skill": "GPT-4",
                "complexity": "simple",
            },
            {
                "query": "LangChain developer",
                "category": "ai_ml",
                "expected_skill": "LangChain",
                "complexity": "simple",
            },
            {
                "query": "Hugging Face developer",
                "category": "ai_ml",
                "expected_skill": "Hugging Face",
                "complexity": "simple",
            },
            # Role-based
            {
                "query": "Machine Learning engineer",
                "category": "ai_ml",
                "expected_skill": "Machine Learning Engineering",
                "complexity": "medium",
            },
            {
                "query": "Data scientist",
                "category": "ai_ml",
                "expected_skill": "Data Science",
                "complexity": "medium",
            },
            {
                "query": "AI engineer",
                "category": "ai_ml",
                "expected_skill": "AI Engineering",
                "complexity": "medium",
            },
            {
                "query": "MLOps engineer",
                "category": "ai_ml",
                "expected_skill": "MLOps",
                "complexity": "medium",
            },
            # Variations
            {
                "query": "ML engineer",
                "category": "ai_ml",
                "expected_skill": "Machine Learning Engineering",
                "complexity": "medium",
            },
            {
                "query": "Deep Learning engineer",
                "category": "ai_ml",
                "expected_skill": "Deep Learning",
                "complexity": "medium",
            },
            # With experience
            {
                "query": "Senior Data Scientist",
                "category": "ai_ml",
                "expected_skill": "Data Science",
                "expected_experience": 5,
                "complexity": "medium",
            },
            {
                "query": "TensorFlow developer with 3+ years",
                "category": "ai_ml",
                "expected_skill": "TensorFlow",
                "expected_experience": 3,
                "complexity": "medium",
            },
        ]
        test_queries.extend(ai_ml_tests)

        # ===== CATEGORY 7: LOCATION-BASED SEARCHES (25 tests) =====
        location_tests = [
            # State variations
            {
                "query": "Java developer in California",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "California",
                "complexity": "medium",
            },
            {
                "query": "Python engineer in CA",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "CA",
                "complexity": "medium",
            },
            {
                "query": "React developer in New York",
                "category": "location",
                "expected_skill": "React",
                "expected_location": "New York",
                "complexity": "medium",
            },
            {
                "query": "Angular developer in NY",
                "category": "location",
                "expected_skill": "Angular",
                "expected_location": "NY",
                "complexity": "medium",
            },
            {
                "query": "Node.js developer in Texas",
                "category": "location",
                "expected_skill": "Node.js",
                "expected_location": "Texas",
                "complexity": "medium",
            },
            {
                "query": "Java developer in TX",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "TX",
                "complexity": "medium",
            },
            # City variations
            {
                "query": "Python developer in San Francisco",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "San Francisco",
                "complexity": "medium",
            },
            {
                "query": "React engineer in Los Angeles",
                "category": "location",
                "expected_skill": "React",
                "expected_location": "Los Angeles",
                "complexity": "medium",
            },
            {
                "query": "Java developer in Seattle",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "Seattle",
                "complexity": "medium",
            },
            {
                "query": "Angular developer in Austin",
                "category": "location",
                "expected_skill": "Angular",
                "expected_location": "Austin",
                "complexity": "medium",
            },
            {
                "query": "Node.js engineer in Denver",
                "category": "location",
                "expected_skill": "Node.js",
                "expected_location": "Denver",
                "complexity": "medium",
            },
            # Remote variations
            {
                "query": "Remote Java developer",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "Remote",
                "complexity": "medium",
            },
            {
                "query": "Python developer remote",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "Remote",
                "complexity": "medium",
            },
            {
                "query": "Remote work React developer",
                "category": "location",
                "expected_skill": "React",
                "expected_location": "Remote",
                "complexity": "medium",
            },
            {
                "query": "Work from home Python engineer",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "Remote",
                "complexity": "medium",
            },
            # Alternative patterns
            {
                "query": "Java developer based in Boston",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "Boston",
                "complexity": "medium",
            },
            {
                "query": "Python engineer located in Chicago",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "Chicago",
                "complexity": "medium",
            },
            {
                "query": "React developer from Miami",
                "category": "location",
                "expected_skill": "React",
                "expected_location": "Miami",
                "complexity": "medium",
            },
            # Multi-city
            {
                "query": "Java developer in Bay Area",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "Bay Area",
                "complexity": "medium",
            },
            {
                "query": "Python engineer in Silicon Valley",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "Silicon Valley",
                "complexity": "medium",
            },
            # With experience and location
            {
                "query": "Senior Java developer in California",
                "category": "location",
                "expected_skill": "Java",
                "expected_location": "California",
                "expected_experience": 5,
                "complexity": "complex",
            },
            {
                "query": "5+ years Python engineer in New York",
                "category": "location",
                "expected_skill": "Python",
                "expected_location": "New York",
                "expected_experience": 5,
                "complexity": "complex",
            },
            {
                "query": "React developer with 3 years in San Francisco",
                "category": "location",
                "expected_skill": "React",
                "expected_location": "San Francisco",
                "expected_experience": 3,
                "complexity": "complex",
            },
            {
                "query": "Junior Angular developer in Seattle",
                "category": "location",
                "expected_skill": "Angular",
                "expected_location": "Seattle",
                "expected_experience": 1,
                "complexity": "complex",
            },
            {
                "query": "Node.js developer over 4 years in Austin",
                "category": "location",
                "expected_skill": "Node.js",
                "expected_location": "Austin",
                "expected_experience": 4,
                "complexity": "complex",
            },
        ]
        test_queries.extend(location_tests)

        # ===== CATEGORY 8: EDGE CASES & TYPOS (15 tests) =====
        edge_case_tests = [
            # Typos
            {
                "query": "Javva developer",
                "category": "edge_case",
                "expected_skill": "Java",
                "complexity": "edge_case",
            },
            {
                "query": "Pyhton engineer",
                "category": "edge_case",
                "expected_skill": "Python",
                "complexity": "edge_case",
            },
            {
                "query": "Javascirpt developer",
                "category": "edge_case",
                "expected_skill": "JavaScript",
                "complexity": "edge_case",
            },
            {
                "query": "Reactt developer",
                "category": "edge_case",
                "expected_skill": "React",
                "complexity": "edge_case",
            },
            # Partial matches
            {
                "query": "Java",
                "category": "edge_case",
                "expected_skill": "Java",
                "complexity": "simple",
            },
            {
                "query": "Python",
                "category": "edge_case",
                "expected_skill": "Python",
                "complexity": "simple",
            },
            {
                "query": "React",
                "category": "edge_case",
                "expected_skill": "React",
                "complexity": "simple",
            },
            # Alternative spellings
            {
                "query": "Node js developer",
                "category": "edge_case",
                "expected_skill": "Node.js",
                "complexity": "simple",
            },
            {
                "query": "Vue js developer",
                "category": "edge_case",
                "expected_skill": "Vue.js",
                "complexity": "simple",
            },
            {
                "query": "Express js developer",
                "category": "edge_case",
                "expected_skill": "Express.js",
                "complexity": "simple",
            },
            # Abbreviations
            {
                "query": "JS developer",
                "category": "edge_case",
                "expected_skill": "JavaScript",
                "complexity": "simple",
            },
            {
                "query": "TS developer",
                "category": "edge_case",
                "expected_skill": "TypeScript",
                "complexity": "simple",
            },
            {
                "query": "DB developer",
                "category": "edge_case",
                "expected_skill": "Database",
                "complexity": "simple",
            },
            # Empty/minimal queries
            {
                "query": "developer",
                "category": "edge_case",
                "expected_skill": None,
                "complexity": "edge_case",
            },
            {
                "query": "engineer",
                "category": "edge_case",
                "expected_skill": None,
                "complexity": "edge_case",
            },
        ]
        test_queries.extend(edge_case_tests)

        # ===== CATEGORY 9: COMPLEX MULTI-SKILL QUERIES (10 tests) =====
        complex_tests = [
            # Multiple skills
            {
                "query": "Full stack JavaScript developer",
                "category": "complex",
                "expected_skill": "JavaScript",
                "complexity": "complex",
            },
            {
                "query": "React and Node.js developer",
                "category": "complex",
                "expected_skill": "React",
                "complexity": "complex",
            },
            {
                "query": "Python Django developer",
                "category": "complex",
                "expected_skill": "Python",
                "complexity": "complex",
            },
            {
                "query": "Java Spring Boot developer",
                "category": "complex",
                "expected_skill": "Java",
                "complexity": "complex",
            },
            {
                "query": "React TypeScript developer",
                "category": "complex",
                "expected_skill": "React",
                "complexity": "complex",
            },
            # Role + skills + experience
            {
                "query": "Senior Full Stack Developer with React and Node.js",
                "category": "complex",
                "expected_skill": "React",
                "expected_experience": 5,
                "complexity": "complex",
            },
            {
                "query": "Lead Python Django engineer with 8+ years",
                "category": "complex",
                "expected_skill": "Python",
                "expected_experience": 8,
                "complexity": "complex",
            },
            {
                "query": "Principal Java Spring developer over 10 years",
                "category": "complex",
                "expected_skill": "Java",
                "expected_experience": 10,
                "complexity": "complex",
            },
            # Everything combined
            {
                "query": "Senior React TypeScript developer with 5+ years in San Francisco",
                "category": "complex",
                "expected_skill": "React",
                "expected_experience": 5,
                "expected_location": "San Francisco",
                "complexity": "complex",
            },
            {
                "query": "Lead Python Django engineer over 7 years remote work",
                "category": "complex",
                "expected_skill": "Python",
                "expected_experience": 7,
                "expected_location": "Remote",
                "complexity": "complex",
            },
        ]
        test_queries.extend(complex_tests)

        return test_queries

    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case and collect results"""

        query = test_case["query"]
        start_time = time.time()

        try:
            # Test skill extraction
            skill_matches = await self.matcher.extract_skills_from_query(query)

            # Test location extraction
            location = self.matcher.extract_location(query)

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Analyze results
            result = {
                "query": query,
                "category": test_case["category"],
                "complexity": test_case["complexity"],
                "response_time_ms": round(response_time, 2),
                "skill_matches_found": len(skill_matches),
                "skills_detected": [match.matched_skill for match in skill_matches],
                "location_detected": location,
                "success": len(skill_matches) > 0,
                "expected_skill": test_case.get("expected_skill"),
                "expected_experience": test_case.get("expected_experience"),
                "expected_location": test_case.get("expected_location"),
            }

            # Add detailed match information
            if skill_matches:
                primary_match = skill_matches[0]
                result.update(
                    {
                        "primary_skill": primary_match.matched_skill,
                        "primary_confidence": round(primary_match.confidence, 3),
                        "match_type": primary_match.match_type,
                        "experience_detected": primary_match.experience_years,
                        "original_skill_text": primary_match.original_skill,
                    }
                )

                # Check if primary skill matches expected
                expected = test_case.get("expected_skill")
                if expected:
                    skill_match_correct = (
                        primary_match.matched_skill.lower() == expected.lower()
                        or expected.lower() in primary_match.matched_skill.lower()
                        or primary_match.matched_skill.lower() in expected.lower()
                    )
                    result["skill_match_correct"] = skill_match_correct

                # Check experience extraction
                expected_exp = test_case.get("expected_experience")
                if expected_exp:
                    exp_match_correct = primary_match.experience_years == expected_exp
                    result["experience_match_correct"] = exp_match_correct

            # Check location extraction
            expected_loc = test_case.get("expected_location")
            if expected_loc:
                loc_match_correct = location and (
                    location.lower() == expected_loc.lower()
                    or expected_loc.lower() in location.lower()
                    or location.lower() in expected_loc.lower()
                )
                result["location_match_correct"] = loc_match_correct

            return result

        except Exception as e:
            return {
                "query": query,
                "category": test_case["category"],
                "complexity": test_case["complexity"],
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "success": False,
                "error": str(e),
                "expected_skill": test_case.get("expected_skill"),
                "expected_experience": test_case.get("expected_experience"),
                "expected_location": test_case.get("expected_location"),
            }

    async def run_all_tests(self):
        """Run all test cases and collect comprehensive results"""

        print("🧪 Starting Comprehensive Search Test Suite...")
        print("=" * 80)

        test_queries = self.get_test_queries()
        total_tests = len(test_queries)

        print(f"📊 Total test cases: {total_tests}")
        print(
            f"🎯 Categories: Programming, Frontend, Backend, Database, Cloud/DevOps, AI/ML, Location, Edge Cases, Complex"
        )
        print()

        # Run tests in batches for better performance
        batch_size = 20
        successful_matches = 0
        total_response_time = 0

        for i in range(0, total_tests, batch_size):
            batch = test_queries[i : i + batch_size]
            batch_results = []

            print(
                f"🔄 Running batch {i//batch_size + 1}/{(total_tests + batch_size - 1)//batch_size} ({len(batch)} tests)..."
            )

            # Run batch tests concurrently for speed
            tasks = [self.run_single_test(test_case) for test_case in batch]
            batch_results = await asyncio.gather(*tasks)

            # Collect statistics
            for result in batch_results:
                self.test_results.append(result)
                if result["success"]:
                    successful_matches += 1
                total_response_time += result["response_time_ms"]

                # Track skill and location coverage
                if "primary_skill" in result:
                    self.stats["skill_coverage"].add(result["primary_skill"])
                if result.get("location_detected"):
                    self.stats["location_coverage"].add(result["location_detected"])

            # Show progress
            batch_success_rate = (
                sum(1 for r in batch_results if r["success"]) / len(batch_results) * 100
            )
            print(f"✅ Batch completed: {batch_success_rate:.1f}% success rate")

        # Calculate final statistics
        self.stats.update(
            {
                "total_tests": total_tests,
                "successful_matches": successful_matches,
                "failed_matches": total_tests - successful_matches,
                "success_rate": (successful_matches / total_tests) * 100,
                "avg_response_time": total_response_time / total_tests,
                "unique_skills_detected": len(self.stats["skill_coverage"]),
                "unique_locations_detected": len(self.stats["location_coverage"]),
            }
        )

        print()
        print("🎉 All tests completed!")
        print("=" * 80)

    def save_results_to_file(self, filename: str = None):
        """Save comprehensive test results to JSON file"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_test_results_{timestamp}.json"

        # Prepare comprehensive results
        output_data = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_test_cases": len(self.test_results),
                "test_categories": list(set(r["category"] for r in self.test_results)),
                "complexity_levels": list(
                    set(r["complexity"] for r in self.test_results)
                ),
            },
            "summary_statistics": {
                "total_tests": self.stats["total_tests"],
                "successful_matches": self.stats["successful_matches"],
                "failed_matches": self.stats["failed_matches"],
                "success_rate_percent": round(self.stats["success_rate"], 2),
                "average_response_time_ms": round(self.stats["avg_response_time"], 2),
                "unique_skills_detected": self.stats["unique_skills_detected"],
                "unique_locations_detected": self.stats["unique_locations_detected"],
                "skills_coverage": sorted(list(self.stats["skill_coverage"])),
                "locations_coverage": sorted(list(self.stats["location_coverage"])),
            },
            "category_breakdown": self._generate_category_breakdown(),
            "complexity_breakdown": self._generate_complexity_breakdown(),
            "performance_analysis": self._generate_performance_analysis(),
            "detailed_results": self.test_results,
            "failed_tests": [r for r in self.test_results if not r["success"]],
            "top_performing_tests": sorted(
                [r for r in self.test_results if r["success"]],
                key=lambda x: x["response_time_ms"],
            )[:10],
            "slowest_tests": sorted(
                self.test_results, key=lambda x: x["response_time_ms"], reverse=True
            )[:10],
        }

        # Save to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"📄 Results saved to: {filename}")
        return filename

    def _generate_category_breakdown(self) -> Dict[str, Any]:
        """Generate breakdown by test category"""
        categories = {}

        for result in self.test_results:
            category = result["category"]
            if category not in categories:
                categories[category] = {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "avg_response_time": 0,
                    "success_rate": 0,
                }

            categories[category]["total_tests"] += 1
            if result["success"]:
                categories[category]["successful_tests"] += 1

        # Calculate percentages and averages
        for category, stats in categories.items():
            category_results = [
                r for r in self.test_results if r["category"] == category
            ]
            stats["success_rate"] = (
                stats["successful_tests"] / stats["total_tests"]
            ) * 100
            stats["avg_response_time"] = sum(
                r["response_time_ms"] for r in category_results
            ) / len(category_results)

        return categories

    def _generate_complexity_breakdown(self) -> Dict[str, Any]:
        """Generate breakdown by complexity level"""
        complexity_levels = {}

        for result in self.test_results:
            complexity = result["complexity"]
            if complexity not in complexity_levels:
                complexity_levels[complexity] = {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "avg_response_time": 0,
                    "success_rate": 0,
                }

            complexity_levels[complexity]["total_tests"] += 1
            if result["success"]:
                complexity_levels[complexity]["successful_tests"] += 1

        # Calculate percentages and averages
        for complexity, stats in complexity_levels.items():
            complexity_results = [
                r for r in self.test_results if r["complexity"] == complexity
            ]
            stats["success_rate"] = (
                stats["successful_tests"] / stats["total_tests"]
            ) * 100
            stats["avg_response_time"] = sum(
                r["response_time_ms"] for r in complexity_results
            ) / len(complexity_results)

        return complexity_levels

    def _generate_performance_analysis(self) -> Dict[str, Any]:
        """Generate performance analysis"""
        response_times = [r["response_time_ms"] for r in self.test_results]
        successful_times = [
            r["response_time_ms"] for r in self.test_results if r["success"]
        ]

        return {
            "response_time_stats": {
                "min_ms": min(response_times),
                "max_ms": max(response_times),
                "avg_ms": sum(response_times) / len(response_times),
                "median_ms": sorted(response_times)[len(response_times) // 2],
            },
            "successful_tests_performance": {
                "avg_ms": (
                    sum(successful_times) / len(successful_times)
                    if successful_times
                    else 0
                ),
                "under_100ms": sum(1 for t in successful_times if t < 100),
                "under_500ms": sum(1 for t in successful_times if t < 500),
                "under_1000ms": sum(1 for t in successful_times if t < 1000),
                "over_1000ms": sum(1 for t in successful_times if t >= 1000),
            },
            "performance_targets": {
                "target_response_time_ms": 100,
                "tests_meeting_target": sum(1 for t in response_times if t < 100),
                "percentage_meeting_target": (
                    sum(1 for t in response_times if t < 100) / len(response_times)
                )
                * 100,
            },
        }

    def print_summary(self):
        """Print a comprehensive summary of test results"""

        print("\n🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)

        # Overall statistics
        print(f"📊 Total Tests: {self.stats['total_tests']}")
        print(
            f"✅ Successful: {self.stats['successful_matches']} ({self.stats['success_rate']:.1f}%)"
        )
        print(f"❌ Failed: {self.stats['failed_matches']}")
        print(f"⏱️  Average Response Time: {self.stats['avg_response_time']:.1f}ms")
        print(f"🎯 Unique Skills Detected: {self.stats['unique_skills_detected']}")
        print(f"🗺️ Unique Locations Detected: {self.stats['unique_locations_detected']}")

        # Category breakdown
        print(f"\n📋 CATEGORY PERFORMANCE:")
        category_stats = self._generate_category_breakdown()
        for category, stats in category_stats.items():
            print(
                f"  {category.upper():15} | {stats['success_rate']:5.1f}% | {stats['avg_response_time']:6.1f}ms | {stats['total_tests']:3d} tests"
            )

        # Complexity breakdown
        print(f"\n🔧 COMPLEXITY PERFORMANCE:")
        complexity_stats = self._generate_complexity_breakdown()
        for complexity, stats in complexity_stats.items():
            print(
                f"  {complexity.upper():15} | {stats['success_rate']:5.1f}% | {stats['avg_response_time']:6.1f}ms | {stats['total_tests']:3d} tests"
            )

        # Performance analysis
        perf_stats = self._generate_performance_analysis()
        print(f"\n⚡ PERFORMANCE ANALYSIS:")
        print(
            f"  Fastest Response: {perf_stats['response_time_stats']['min_ms']:.1f}ms"
        )
        print(
            f"  Slowest Response: {perf_stats['response_time_stats']['max_ms']:.1f}ms"
        )
        print(
            f"  Median Response: {perf_stats['response_time_stats']['median_ms']:.1f}ms"
        )
        print(
            f"  Under 100ms: {perf_stats['successful_tests_performance']['under_100ms']} tests"
        )
        print(
            f"  Under 500ms: {perf_stats['successful_tests_performance']['under_500ms']} tests"
        )
        print(
            f"  Over 1000ms: {perf_stats['successful_tests_performance']['over_1000ms']} tests"
        )

        # Show some examples
        print(f"\n🌟 TOP PERFORMING QUERIES (Fastest):")
        top_tests = sorted(
            [r for r in self.test_results if r["success"]],
            key=lambda x: x["response_time_ms"],
        )[:5]
        for i, test in enumerate(top_tests, 1):
            print(
                f"  {i}. '{test['query']}' → {test['primary_skill']} ({test['response_time_ms']:.1f}ms)"
            )

        print(f"\n🐌 SLOWEST QUERIES:")
        slow_tests = sorted(
            self.test_results, key=lambda x: x["response_time_ms"], reverse=True
        )[:5]
        for i, test in enumerate(slow_tests, 1):
            status = test["primary_skill"] if test["success"] else "FAILED"
            print(
                f"  {i}. '{test['query']}' → {status} ({test['response_time_ms']:.1f}ms)"
            )

        if self.stats["failed_matches"] > 0:
            print(f"\n❌ FAILED QUERIES:")
            failed_tests = [r for r in self.test_results if not r["success"]][:5]
            for i, test in enumerate(failed_tests, 1):
                error = test.get("error", "No skill detected")
                print(f"  {i}. '{test['query']}' → {error}")

        print("\n" + "=" * 80)


async def main():
    """Main function to run the comprehensive test suite"""

    # Initialize test suite
    test_suite = SearchTestSuite()

    # Run all tests
    await test_suite.run_all_tests()

    # Print summary
    test_suite.print_summary()

    # Save detailed results to file
    results_file = test_suite.save_results_to_file()

    print(f"\n🎉 Test Suite Complete!")
    print(f"📊 Summary: {test_suite.stats['success_rate']:.1f}% success rate")
    print(f"⏱️  Performance: {test_suite.stats['avg_response_time']:.1f}ms average")
    print(f"📄 Detailed results: {results_file}")


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(main())
