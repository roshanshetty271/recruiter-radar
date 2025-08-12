#!/usr/bin/env python3
"""
Performance Audit Script for Resume Upload System

This script benchmarks the current performance and identifies bottlenecks
in the resume upload pipeline to guide optimization efforts.
"""

import asyncio
import time
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.ai_extraction_service import AIExtractionService
from app.services.resume_parser import ResumeParser
from app.services.rag_service import RAGService
from app.services.chroma_connector import ChromaConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceAuditor:
    """Comprehensive performance auditing for resume upload system."""

    def __init__(self):
        """Initialize the auditor with required services."""
        self.llm_service = LLMService(settings)
        self.ai_extractor = AIExtractionService(self.llm_service)
        self.resume_parser = ResumeParser(self.llm_service)

        # Initialize RAG service for storage testing
        try:
            self.connector = ChromaConnector(settings)
            self.rag_service = RAGService(settings, self.connector)
        except Exception as e:
            logger.warning(f"RAG service initialization failed: {e}")
            self.rag_service = None

        self.results = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "text_extraction_times": [],
            "ai_extraction_times": [],
            "embedding_generation_times": [],
            "storage_times": [],
            "end_to_end_times": [],
            "error_rates": {},
            "file_size_analysis": {},
            "bottlenecks": [],
            "recommendations": [],
        }

    async def audit_text_extraction_performance(
        self, test_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Audit text extraction performance across different file types and sizes."""
        logger.info("🔍 Auditing text extraction performance...")

        extraction_times = []
        error_count = 0
        file_type_performance = {}

        for test_file in test_files:
            file_path = test_file["path"]
            file_type = test_file["type"]
            file_size = test_file["size_mb"]

            try:
                start_time = time.time()

                # Read file content
                with open(file_path, "rb") as f:
                    file_content = f.read()

                # Extract text based on file type
                text = self.resume_parser.extract_text_from_file(
                    file_content, file_type
                )

                extraction_time = time.time() - start_time
                extraction_times.append(extraction_time)

                # Track per file type
                if file_type not in file_type_performance:
                    file_type_performance[file_type] = []
                file_type_performance[file_type].append(
                    {
                        "time": extraction_time,
                        "size_mb": file_size,
                        "text_length": len(text),
                        "success": True,
                    }
                )

                logger.info(
                    f"✅ Extracted {len(text)} chars from {file_path} in {extraction_time:.2f}s"
                )

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Text extraction failed for {file_path}: {e}")

                if file_type not in file_type_performance:
                    file_type_performance[file_type] = []
                file_type_performance[file_type].append(
                    {
                        "time": None,
                        "size_mb": file_size,
                        "text_length": 0,
                        "success": False,
                        "error": str(e),
                    }
                )

        # Calculate statistics
        success_times = [t for t in extraction_times if t is not None]

        return {
            "total_files": len(test_files),
            "successful_extractions": len(success_times),
            "failed_extractions": error_count,
            "error_rate": error_count / len(test_files) if test_files else 0,
            "avg_extraction_time": (
                statistics.mean(success_times) if success_times else 0
            ),
            "median_extraction_time": (
                statistics.median(success_times) if success_times else 0
            ),
            "max_extraction_time": max(success_times) if success_times else 0,
            "min_extraction_time": min(success_times) if success_times else 0,
            "file_type_performance": file_type_performance,
        }

    async def audit_ai_extraction_performance(
        self, sample_texts: List[str]
    ) -> Dict[str, Any]:
        """Audit AI extraction performance with various text samples."""
        logger.info("🤖 Auditing AI extraction performance...")

        extraction_times = []
        confidence_scores = []
        error_count = 0
        timeout_count = 0
        cache_hits = 0

        for i, text in enumerate(sample_texts):
            try:
                start_time = time.time()

                # Test with different timeout values
                timeout_values = [10, 20, 45]  # Current is 45s
                for timeout in timeout_values:
                    logger.info(
                        f"Testing AI extraction with {timeout}s timeout (sample {i+1}/{len(sample_texts)})..."
                    )

                    try:
                        extracted_data = await self.ai_extractor.extract_resume_data(
                            resume_text=text, timeout_seconds=timeout
                        )

                        extraction_time = time.time() - start_time

                        if extracted_data:
                            extraction_times.append(extraction_time)
                            confidence_scores.append(
                                extracted_data.extraction_confidence
                            )

                            logger.info(
                                f"✅ AI extraction completed in {extraction_time:.2f}s "
                                f"(confidence: {extracted_data.extraction_confidence:.2f}, "
                                f"skills: {len(extracted_data.technical_skills)})"
                            )
                        else:
                            error_count += 1
                            logger.warning(f"⚠️ AI extraction returned None")

                        break  # Success, don't try other timeouts

                    except asyncio.TimeoutError:
                        timeout_count += 1
                        logger.warning(f"⏰ AI extraction timeout at {timeout}s")
                        if timeout == timeout_values[-1]:  # Last timeout
                            error_count += 1
                    except Exception as e:
                        logger.error(f"❌ AI extraction error: {e}")
                        error_count += 1
                        break

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Sample {i+1} failed: {e}")

        # Get analytics from the AI extraction service
        analytics = self.ai_extractor.get_analytics(hours_back=1)

        success_times = [t for t in extraction_times if t is not None]

        return {
            "total_samples": len(sample_texts),
            "successful_extractions": len(success_times),
            "failed_extractions": error_count,
            "timeout_count": timeout_count,
            "error_rate": error_count / len(sample_texts) if sample_texts else 0,
            "timeout_rate": timeout_count / len(sample_texts) if sample_texts else 0,
            "avg_extraction_time": (
                statistics.mean(success_times) if success_times else 0
            ),
            "median_extraction_time": (
                statistics.median(success_times) if success_times else 0
            ),
            "max_extraction_time": max(success_times) if success_times else 0,
            "avg_confidence": (
                statistics.mean(confidence_scores) if confidence_scores else 0
            ),
            "min_confidence": min(confidence_scores) if confidence_scores else 0,
            "analytics": analytics,
        }

    async def audit_embedding_performance(self, texts: List[str]) -> Dict[str, Any]:
        """Audit embedding generation performance."""
        logger.info("🧠 Auditing embedding generation performance...")

        embedding_times = []
        error_count = 0

        for i, text in enumerate(texts):
            try:
                start_time = time.time()

                # Test embedding generation
                embedding = await self.llm_service.get_embedding(text)

                embedding_time = time.time() - start_time
                embedding_times.append(embedding_time)

                logger.info(
                    f"✅ Generated embedding {i+1}/{len(texts)} in {embedding_time:.2f}s "
                    f"(dimension: {len(embedding)}, text length: {len(text)})"
                )

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Embedding generation failed for text {i+1}: {e}")

        success_times = [t for t in embedding_times if t is not None]

        return {
            "total_texts": len(texts),
            "successful_embeddings": len(success_times),
            "failed_embeddings": error_count,
            "error_rate": error_count / len(texts) if texts else 0,
            "avg_embedding_time": (
                statistics.mean(success_times) if success_times else 0
            ),
            "median_embedding_time": (
                statistics.median(success_times) if success_times else 0
            ),
            "max_embedding_time": max(success_times) if success_times else 0,
        }

    async def audit_storage_performance(
        self, candidate_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Audit ChromaDB storage performance."""
        if not self.rag_service:
            return {"error": "RAG service not available"}

        logger.info("💾 Auditing storage performance...")

        storage_times = []
        error_count = 0

        for i, data in enumerate(candidate_data):
            try:
                start_time = time.time()

                # Test storage operation
                await self.rag_service.add_candidate_to_collection(
                    candidate_id=f"audit_test_{i}",
                    embedding=data["embedding"],
                    metadata=data["metadata"],
                    document_text=data["document_text"],
                )

                storage_time = time.time() - start_time
                storage_times.append(storage_time)

                logger.info(
                    f"✅ Stored candidate {i+1}/{len(candidate_data)} in {storage_time:.2f}s"
                )

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Storage failed for candidate {i+1}: {e}")

        success_times = [t for t in storage_times if t is not None]

        return {
            "total_candidates": len(candidate_data),
            "successful_storage": len(success_times),
            "failed_storage": error_count,
            "error_rate": error_count / len(candidate_data) if candidate_data else 0,
            "avg_storage_time": statistics.mean(success_times) if success_times else 0,
            "median_storage_time": (
                statistics.median(success_times) if success_times else 0
            ),
            "max_storage_time": max(success_times) if success_times else 0,
        }

    def generate_test_data(self) -> Dict[str, List[Any]]:
        """Generate test data for performance auditing."""
        # Sample resume texts of varying lengths
        sample_texts = [
            # Short resume
            """
            John Doe
            john.doe@email.com
            Software Engineer
            
            Skills: Python, JavaScript, React
            Experience: 3 years at Tech Company
            Education: BS Computer Science, State University
            """,
            # Medium resume
            """
            Jane Smith
            jane.smith@email.com
            (555) 123-4567
            Senior Full Stack Developer
            
            EXPERIENCE:
            Senior Full Stack Developer | TechCorp Inc. | 2020 - Present
            - Led development of microservices architecture serving 1M+ users
            - Implemented CI/CD pipeline reducing deployment time by 60%
            - Mentored team of 5 junior developers
            
            Full Stack Developer | StartupXYZ | 2018 - 2020
            - Built e-commerce platform from scratch using React and Node.js
            - Integrated payment systems and inventory management
            
            SKILLS:
            Frontend: React, Vue.js, TypeScript, HTML5, CSS3
            Backend: Node.js, Python, Java, Express.js, Django
            Database: PostgreSQL, MongoDB, Redis
            Cloud: AWS, Docker, Kubernetes
            
            EDUCATION:
            Master of Science in Computer Science
            Stanford University | 2018
            
            Bachelor of Science in Software Engineering  
            UC Berkeley | 2016
            """,
            # Long, complex resume
            """
            Dr. Sarah Johnson, Ph.D.
            sarah.johnson@email.com
            (555) 987-6543
            LinkedIn: linkedin.com/in/sarahjohnson
            GitHub: github.com/sarahjohnson
            
            PROFESSIONAL SUMMARY:
            Seasoned Principal Software Architect with 15+ years of experience designing and implementing large-scale distributed systems. Expert in cloud-native architectures, microservices, and DevOps practices. Led multiple digital transformation initiatives resulting in 40% cost reduction and 99.9% uptime. Published researcher with 25+ papers in top-tier conferences.
            
            WORK EXPERIENCE:
            
            Principal Software Architect | Google LLC | 2019 - Present
            - Architected distributed data processing platform handling 100TB+ daily
            - Led cross-functional team of 25 engineers across 3 time zones
            - Designed fault-tolerant systems with 99.99% availability SLA
            - Implemented machine learning pipelines for real-time recommendations
            - Technologies: Go, Python, Kubernetes, Apache Kafka, BigQuery, TensorFlow
            
            Senior Software Engineer | Facebook (Meta) | 2016 - 2019
            - Developed real-time messaging infrastructure serving 2B+ users
            - Optimized database queries reducing latency by 45%
            - Built monitoring and alerting systems for production services
            - Mentored 15+ engineers and conducted technical interviews
            - Technologies: C++, Python, MySQL, Cassandra, React, GraphQL
            
            Software Engineer | Microsoft | 2014 - 2016
            - Contributed to Azure cloud platform development
            - Implemented autoscaling algorithms for virtual machine clusters
            - Built REST APIs consumed by millions of users
            - Technologies: C#, .NET, Azure, SQL Server, PowerShell
            
            Research Assistant | MIT CSAIL | 2012 - 2014
            - Conducted research on distributed consensus algorithms
            - Published 8 papers in top-tier conferences (SOSP, OSDI, NSDI)
            - Implemented Raft consensus protocol in production systems
            - Technologies: Go, C++, Protocol Buffers
            
            TECHNICAL SKILLS:
            Programming Languages: Go, Python, C++, Java, JavaScript, TypeScript, C#, Rust, Scala
            Web Technologies: React, Vue.js, Angular, Node.js, Express.js, Django, Flask
            Databases: PostgreSQL, MySQL, MongoDB, Cassandra, Redis, DynamoDB, BigQuery
            Cloud Platforms: AWS (EC2, S3, Lambda, RDS, EKS), Google Cloud Platform, Azure
            DevOps Tools: Docker, Kubernetes, Jenkins, GitLab CI, Terraform, Ansible
            Message Queues: Apache Kafka, RabbitMQ, Amazon SQS, Google Pub/Sub
            Monitoring: Prometheus, Grafana, DataDog, New Relic, ELK Stack
            ML/AI: TensorFlow, PyTorch, scikit-learn, Apache Spark, MLflow
            
            EDUCATION:
            Ph.D. in Computer Science | Massachusetts Institute of Technology | 2014
            Dissertation: "Efficient Consensus Algorithms for Large-Scale Distributed Systems"
            
            Master of Science in Computer Science | Stanford University | 2010
            Thesis: "Scalable Database Replication Strategies"
            
            Bachelor of Science in Computer Engineering | UC Berkeley | 2008
            Magna Cum Laude, Phi Beta Kappa
            
            CERTIFICATIONS:
            - AWS Solutions Architect Professional (2023)
            - Google Cloud Professional Cloud Architect (2022)
            - Kubernetes Certified Administrator (CKA) (2021)
            - Certified Scrum Master (CSM) (2020)
            
            PUBLICATIONS:
            1. "Distributed Consensus in the Era of Cloud Computing" - SOSP 2023
            2. "Optimizing Microservices Communication Patterns" - OSDI 2022
            3. "Machine Learning for Database Query Optimization" - SIGMOD 2021
            [... 22 more publications]
            
            PROJECTS:
            - Open Source Contributor: Kubernetes, Apache Kafka, TensorFlow
            - Personal Project: "DistributedDB" - A high-performance distributed database (50k+ GitHub stars)
            - Speaking: Keynote speaker at DockerCon, KubeCon, Strata Data Conference
            
            LANGUAGES:
            English (Native), Spanish (Fluent), Mandarin (Conversational), French (Basic)
            
            SECURITY CLEARANCE:
            Top Secret (Active)
            """,
        ]

        # Mock file data (since we don't have actual test files)
        test_files = [
            {"path": "test_small.pdf", "type": "pdf", "size_mb": 0.5},
            {"path": "test_medium.docx", "type": "docx", "size_mb": 2.0},
            {"path": "test_large.pdf", "type": "pdf", "size_mb": 8.0},
            {"path": "test_text.txt", "type": "txt", "size_mb": 0.1},
        ]

        # Mock candidate data for storage testing
        candidate_data = []
        for i, text in enumerate(sample_texts):
            candidate_data.append(
                {
                    "embedding": [0.1] * 1536,  # Mock embedding
                    "metadata": {
                        "candidate_id": f"test_{i}",
                        "name": f"Test Candidate {i}",
                        "skills": "Python,JavaScript,React",
                        "experience_years": 3.0 + i,
                        "source": "performance_audit",
                    },
                    "document_text": text,
                }
            )

        return {
            "sample_texts": sample_texts,
            "test_files": test_files,
            "candidate_data": candidate_data,
        }

    async def run_comprehensive_audit(self) -> Dict[str, Any]:
        """Run comprehensive performance audit."""
        logger.info("🚀 Starting comprehensive performance audit...")

        start_time = time.time()

        # Generate test data
        test_data = self.generate_test_data()

        # Run individual audits
        try:
            # Text extraction audit (using sample texts as mock file content)
            text_extraction_results = await self.audit_text_extraction_performance([])

            # AI extraction audit
            ai_extraction_results = await self.audit_ai_extraction_performance(
                test_data["sample_texts"]
            )

            # Embedding audit
            embedding_results = await self.audit_embedding_performance(
                test_data["sample_texts"][:2]  # Just first 2 to save on API costs
            )

            # Storage audit
            storage_results = await self.audit_storage_performance(
                test_data["candidate_data"][:2]  # Just first 2 for testing
            )

        except Exception as e:
            logger.error(f"❌ Audit failed: {e}")
            return {"error": str(e)}

        total_time = time.time() - start_time

        # Compile results
        results = {
            "audit_summary": {
                "total_audit_time": total_time,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed",
            },
            "text_extraction": text_extraction_results,
            "ai_extraction": ai_extraction_results,
            "embedding_generation": embedding_results,
            "storage": storage_results,
            "bottleneck_analysis": self._analyze_bottlenecks(
                ai_extraction_results, embedding_results, storage_results
            ),
            "recommendations": self._generate_recommendations(
                ai_extraction_results, embedding_results, storage_results
            ),
        }

        return results

    def _analyze_bottlenecks(
        self, ai_results: Dict, embedding_results: Dict, storage_results: Dict
    ) -> List[str]:
        """Analyze results to identify performance bottlenecks."""
        bottlenecks = []

        # AI extraction bottlenecks
        if ai_results.get("avg_extraction_time", 0) > 10:
            bottlenecks.append(
                f"AI extraction too slow: {ai_results.get('avg_extraction_time', 0):.2f}s average"
            )

        if ai_results.get("timeout_rate", 0) > 0.1:
            bottlenecks.append(
                f"High timeout rate: {ai_results.get('timeout_rate', 0)*100:.1f}%"
            )

        if ai_results.get("error_rate", 0) > 0.05:
            bottlenecks.append(
                f"High error rate: {ai_results.get('error_rate', 0)*100:.1f}%"
            )

        # Embedding bottlenecks
        if embedding_results.get("avg_embedding_time", 0) > 3:
            bottlenecks.append(
                f"Embedding generation slow: {embedding_results.get('avg_embedding_time', 0):.2f}s average"
            )

        # Storage bottlenecks
        if storage_results.get("avg_storage_time", 0) > 2:
            bottlenecks.append(
                f"Storage slow: {storage_results.get('avg_storage_time', 0):.2f}s average"
            )

        return bottlenecks

    def _generate_recommendations(
        self, ai_results: Dict, embedding_results: Dict, storage_results: Dict
    ) -> List[str]:
        """Generate optimization recommendations based on audit results."""
        recommendations = []

        # AI extraction recommendations
        if ai_results.get("avg_extraction_time", 0) > 15:
            recommendations.append(
                "Implement async processing to reduce user wait time"
            )
            recommendations.append("Consider faster AI models or optimize prompts")

        if ai_results.get("timeout_rate", 0) > 0.1:
            recommendations.append("Implement progressive timeouts (10s, 20s, 45s)")
            recommendations.append("Add intelligent fallback mechanisms")

        # Embedding recommendations
        if embedding_results.get("avg_embedding_time", 0) > 2:
            recommendations.append("Batch embedding generation for multiple candidates")
            recommendations.append("Consider local embedding models for speed")

        # Storage recommendations
        if storage_results.get("error_rate", 0) > 0.05:
            recommendations.append("Improve error handling and retry logic")
            recommendations.append("Add metadata sanitization")

        # General recommendations
        recommendations.extend(
            [
                "Implement caching for repeated uploads",
                "Add progress indicators for better UX",
                "Use parallel processing for batch uploads",
                "Monitor performance metrics in production",
            ]
        )

        return recommendations

    def save_results(
        self,
        results: Dict[str, Any],
        output_file: str = "performance_audit_results.json",
    ):
        """Save audit results to file."""
        try:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"📊 Audit results saved to {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")


async def main():
    """Main function to run performance audit."""
    auditor = PerformanceAuditor()

    try:
        results = await auditor.run_comprehensive_audit()

        # Print summary
        print("\n" + "=" * 80)
        print("🔍 PERFORMANCE AUDIT SUMMARY")
        print("=" * 80)

        if "error" in results:
            print(f"❌ Audit failed: {results['error']}")
            return

        # Print key metrics
        ai_results = results.get("ai_extraction", {})
        embedding_results = results.get("embedding_generation", {})
        storage_results = results.get("storage", {})

        print(
            f"⏱️  AI Extraction Average: {ai_results.get('avg_extraction_time', 0):.2f}s"
        )
        print(
            f"🧠 Embedding Average: {embedding_results.get('avg_embedding_time', 0):.2f}s"
        )
        print(f"💾 Storage Average: {storage_results.get('avg_storage_time', 0):.2f}s")
        print(f"❌ AI Error Rate: {ai_results.get('error_rate', 0)*100:.1f}%")
        print(f"⏰ Timeout Rate: {ai_results.get('timeout_rate', 0)*100:.1f}%")

        # Print bottlenecks
        bottlenecks = results.get("bottleneck_analysis", [])
        if bottlenecks:
            print(f"\n🚨 BOTTLENECKS IDENTIFIED:")
            for bottleneck in bottlenecks:
                print(f"   • {bottleneck}")

        # Print recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations[:5]:  # Top 5
                print(f"   • {rec}")

        print("=" * 80)

        # Save detailed results
        auditor.save_results(results)

    except Exception as e:
        logger.error(f"❌ Audit failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
