#!/usr/bin/env python3
"""
LLM Extraction Test Harness for RecruiterRadar MVP.
Tests PDF text extraction and LLM structured data extraction across diverse resume formats.

Usage:
    python llm_extraction_harness.py [--prompt-version V1|V2|V3] [--test-category all|standard|challenging|edge_cases|real_world]
"""

import os
import sys
import json
import time
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import statistics

# Add parent directory to path to import from app
sys.path.append(str(Path(__file__).parent.parent))

# Third-party imports
import pypdf
from openai import AsyncOpenAI
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from dotenv import load_dotenv

# Local imports
from app.core.prompts import (
    EXTRACTION_PROMPT_V1,
    EXTRACTION_PROMPT_V2,
    EXTRACTION_PROMPT_V3,
    EXTRACTION_CONFIDENCE_PROMPT,
)
from app.core.feature_flags import USE_CONFIDENCE_SCORES, SHOW_PROCESSING_TIMES

# Load environment variables
load_dotenv()

# Initialize Rich console for beautiful output
console = Console()

# Test categories with expected file patterns
TEST_CATEGORIES = {
    "standard": {
        "description": "Clean, well-formatted single-column resumes",
        "expected_files": ["software_engineer_clean.pdf", "data_scientist_simple.pdf"],
    },
    "challenging": {
        "description": "Complex layouts, multiple columns, heavy formatting",
        "expected_files": ["two_column_designer.pdf", "academic_cv_long.pdf"],
    },
    "edge_cases": {
        "description": "Unusual formats, potential parsing issues",
        "expected_files": ["scanned_image_resume.pdf", "non_english_resume.pdf"],
    },
    "real_world": {
        "description": "Actual resume formats from job sites",
        "expected_files": ["linkedin_export.pdf", "indeed_formatted.pdf"],
    },
}


@dataclass
class ExtractionResult:
    """Result of a single extraction attempt."""

    filename: str
    category: str
    success: bool = False  # Default to False, will be updated during processing
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    pdf_text_length: int = 0
    extraction_time_ms: float = 0
    tokens_used: int = 0


@dataclass
class ExtractionMetrics:
    """Aggregated metrics across all extractions."""

    total_attempts: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    partial_extractions: int = 0  # Some fields extracted but not all
    avg_extraction_time_ms: float = 0
    extraction_times: List[float] = field(default_factory=list)
    success_by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    common_missing_fields: Dict[str, int] = field(default_factory=dict)
    common_error_patterns: Dict[str, int] = field(default_factory=dict)
    field_confidence_scores: Dict[str, List[float]] = field(default_factory=dict)


class ResumeExtractor:
    """Handles PDF text extraction and LLM-based structured data extraction."""

    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.prompt_templates = {
            "V1": EXTRACTION_PROMPT_V1,
            "V2": EXTRACTION_PROMPT_V2,
            "V3": EXTRACTION_PROMPT_V3,
            "CONFIDENCE": EXTRACTION_CONFIDENCE_PROMPT,
        }

    def extract_text_from_pdf(
        self, pdf_path: Path
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract text from PDF using pypdf."""
        try:
            with open(pdf_path, "rb") as file:
                reader = pypdf.PdfReader(file)
                text_parts = []

                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            text_parts.append(text)
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Failed to extract page {page_num + 1}: {e}[/yellow]"
                        )

                full_text = "\n".join(text_parts)

                # Basic text cleaning
                full_text = self._clean_text(full_text)

                if len(full_text) < 100:
                    return None, "Extracted text too short (< 100 chars)"

                return full_text, None

        except Exception as e:
            return None, f"PDF extraction failed: {str(e)}"

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning to improve extraction."""
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        text = "\n".join(cleaned_lines)

        # Remove common PDF artifacts
        text = text.replace("\x00", "")  # Null bytes
        text = " ".join(text.split())  # Normalize whitespace

        # Truncate if too long (to fit in context window)
        if len(text) > 15000:
            text = text[:15000] + "... [truncated]"

        return text

    async def extract_structured_data(
        self, text: str, prompt_version: str = "V2", use_confidence: bool = False
    ) -> Tuple[
        Optional[Dict[str, Any]], Optional[Dict[str, float]], Optional[str], int
    ]:
        """Extract structured data using LLM."""
        try:
            prompt_template = self.prompt_templates.get(
                "CONFIDENCE" if use_confidence else prompt_version,
                self.prompt_templates["V2"],
            )

            prompt = prompt_template.format(text=text)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume parser. Always return valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=1000,
                response_format={"type": "json_object"},  # Force JSON response
            )

            tokens_used = response.usage.total_tokens if response.usage else 0
            result_text = response.choices[0].message.content

            # Parse JSON response
            try:
                result = json.loads(result_text)

                if use_confidence and "data" in result:
                    return result["data"], result.get("confidence"), None, tokens_used
                else:
                    return result, None, None, tokens_used

            except json.JSONDecodeError as e:
                return None, None, f"Invalid JSON response: {e}", tokens_used

        except Exception as e:
            error_msg = f"LLM extraction failed: {str(e)}"
            # Print detailed error for debugging
            console.print(f"[red]Debug - API Error: {type(e).__name__}: {str(e)}[/red]")
            return None, None, error_msg, 0

    def validate_extraction(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate extracted data for required fields and quality."""
        required_fields = [
            "name",
            "title",
            "skills",
            "location",
            "experience_years",
            "email",
            "phone",
            "summary",
        ]
        missing_fields = []
        quality_issues = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif data[field] is None:
                missing_fields.append(f"{field} (null)")
            elif field == "skills" and (
                not isinstance(data[field], list) or len(data[field]) == 0
            ):
                quality_issues.append(f"{field}: empty or not a list")
            elif field == "experience_years" and not isinstance(data[field], int):
                quality_issues.append(f"{field}: not an integer")

        # Additional quality checks
        if "name" in data and data["name"] and len(data["name"]) < 3:
            quality_issues.append("name: too short (< 3 chars)")

        if (
            "skills" in data
            and isinstance(data["skills"], list)
            and len(data["skills"]) > 15
        ):
            quality_issues.append("skills: too many (> 15)")

        is_valid = len(missing_fields) == 0 and len(quality_issues) == 0
        return is_valid, missing_fields, quality_issues


class TestHarness:
    """Main test harness for running extraction tests."""

    def __init__(self, extractor: ResumeExtractor):
        self.extractor = extractor
        self.results: List[ExtractionResult] = []
        self.metrics = ExtractionMetrics()

    async def run_single_test(
        self, pdf_path: Path, category: str, prompt_version: str, use_confidence: bool
    ) -> ExtractionResult:
        """Run extraction test on a single PDF."""
        result = ExtractionResult(filename=pdf_path.name, category=category)

        # Extract PDF text
        start_time = time.time()
        pdf_text, pdf_error = self.extractor.extract_text_from_pdf(pdf_path)

        if pdf_error:
            result.success = False
            result.error_message = pdf_error
            console.print(
                f"[red]PDF extraction failed for {pdf_path.name}: {pdf_error}[/red]"
            )
            return result

        result.pdf_text_length = len(pdf_text)
        console.print(
            f"[dim]Extracted {len(pdf_text)} chars from {pdf_path.name}[/dim]"
        )

        # Extract structured data
        extracted_data, confidence, llm_error, tokens = (
            await self.extractor.extract_structured_data(
                pdf_text, prompt_version, use_confidence
            )
        )

        end_time = time.time()
        result.extraction_time_ms = (end_time - start_time) * 1000
        result.tokens_used = tokens

        if llm_error:
            result.success = False
            result.error_message = llm_error
            return result

        # Validate extraction
        is_valid, missing_fields, quality_issues = self.extractor.validate_extraction(
            extracted_data
        )

        result.extracted_data = extracted_data
        result.confidence_scores = confidence
        result.success = is_valid

        if not is_valid:
            issues = []
            if missing_fields:
                issues.append(f"Missing fields: {', '.join(missing_fields)}")
            if quality_issues:
                issues.append(f"Quality issues: {', '.join(quality_issues)}")
            result.error_message = "; ".join(issues)

        return result

    async def run_category_tests(
        self, category: str, test_dir: Path, prompt_version: str, use_confidence: bool
    ) -> List[ExtractionResult]:
        """Run tests for all PDFs in a category."""
        category_dir = test_dir / category
        if not category_dir.exists():
            console.print(
                f"[yellow]Warning: Category directory {category_dir} not found[/yellow]"
            )
            return []

        pdf_files = list(category_dir.glob("*.pdf"))
        if not pdf_files:
            console.print(
                f"[yellow]Warning: No PDF files found in {category_dir}[/yellow]"
            )
            return []

        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Testing {category} resumes...", total=len(pdf_files)
            )

            for pdf_file in pdf_files:
                progress.update(task, description=f"Testing {pdf_file.name}...")
                result = await self.run_single_test(
                    pdf_file, category, prompt_version, use_confidence
                )
                results.append(result)
                progress.advance(task)

        return results

    def update_metrics(self):
        """Update metrics based on all results."""
        self.metrics.total_attempts = len(self.results)
        self.metrics.successful_extractions = sum(1 for r in self.results if r.success)
        self.metrics.failed_extractions = sum(1 for r in self.results if not r.success)

        # Calculate average extraction time
        self.metrics.extraction_times = [r.extraction_time_ms for r in self.results]
        if self.metrics.extraction_times:
            self.metrics.avg_extraction_time_ms = statistics.mean(
                self.metrics.extraction_times
            )

        # Success by category
        for result in self.results:
            if result.category not in self.metrics.success_by_category:
                self.metrics.success_by_category[result.category] = {
                    "success": 0,
                    "total": 0,
                }

            self.metrics.success_by_category[result.category]["total"] += 1
            if result.success:
                self.metrics.success_by_category[result.category]["success"] += 1

        # Track missing fields and error patterns
        for result in self.results:
            if not result.success and result.error_message:
                if "Missing fields:" in result.error_message:
                    fields = (
                        result.error_message.split("Missing fields:")[1]
                        .split(";")[0]
                        .strip()
                    )
                    for field in fields.split(", "):
                        field = field.strip()
                        self.metrics.common_missing_fields[field] = (
                            self.metrics.common_missing_fields.get(field, 0) + 1
                        )

                # Track error patterns
                if "PDF extraction failed" in result.error_message:
                    pattern = "PDF extraction failed"
                elif "Invalid JSON" in result.error_message:
                    pattern = "Invalid JSON response"
                elif "LLM extraction failed" in result.error_message:
                    pattern = "LLM extraction failed"
                else:
                    pattern = "Other validation errors"

                self.metrics.common_error_patterns[pattern] = (
                    self.metrics.common_error_patterns.get(pattern, 0) + 1
                )

        # Track confidence scores if available
        if USE_CONFIDENCE_SCORES:
            for result in self.results:
                if result.confidence_scores:
                    for field, score in result.confidence_scores.items():
                        if field not in self.metrics.field_confidence_scores:
                            self.metrics.field_confidence_scores[field] = []
                        self.metrics.field_confidence_scores[field].append(score)

    def print_results(self):
        """Print detailed results and metrics."""
        console.rule("[bold blue]Extraction Test Results[/bold blue]")

        # Overall metrics
        success_rate = (
            (self.metrics.successful_extractions / self.metrics.total_attempts * 100)
            if self.metrics.total_attempts > 0
            else 0
        )

        console.print(
            f"\n[bold]Overall Success Rate:[/bold] {success_rate:.1f}% "
            f"({self.metrics.successful_extractions}/{self.metrics.total_attempts})"
        )

        if SHOW_PROCESSING_TIMES:
            console.print(
                f"[bold]Average Extraction Time:[/bold] {self.metrics.avg_extraction_time_ms:.0f}ms"
            )
            console.print(
                f"[bold]Min/Max Times:[/bold] "
                f"{min(self.metrics.extraction_times):.0f}ms / "
                f"{max(self.metrics.extraction_times):.0f}ms"
            )

        # Success by category
        console.print("\n[bold]Success by Category:[/bold]")
        cat_table = Table(show_header=True, header_style="bold magenta")
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Success Rate", justify="right")
        cat_table.add_column("Successful", justify="right")
        cat_table.add_column("Total", justify="right")

        for category, stats in self.metrics.success_by_category.items():
            rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            cat_table.add_row(
                category, f"{rate:.1f}%", str(stats["success"]), str(stats["total"])
            )

        console.print(cat_table)

        # Common issues
        if self.metrics.common_missing_fields:
            console.print("\n[bold]Common Missing Fields:[/bold]")
            field_table = Table(show_header=True, header_style="bold magenta")
            field_table.add_column("Field", style="cyan")
            field_table.add_column("Occurrences", justify="right")

            for field, count in sorted(
                self.metrics.common_missing_fields.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                field_table.add_row(field, str(count))

            console.print(field_table)

        # Error patterns
        if self.metrics.common_error_patterns:
            console.print("\n[bold]Error Patterns:[/bold]")
            error_table = Table(show_header=True, header_style="bold magenta")
            error_table.add_column("Pattern", style="cyan")
            error_table.add_column("Occurrences", justify="right")

            for pattern, count in sorted(
                self.metrics.common_error_patterns.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                error_table.add_row(pattern, str(count))

            console.print(error_table)

        # Confidence scores
        if self.metrics.field_confidence_scores:
            console.print("\n[bold]Average Confidence Scores by Field:[/bold]")
            conf_table = Table(show_header=True, header_style="bold magenta")
            conf_table.add_column("Field", style="cyan")
            conf_table.add_column("Avg Confidence", justify="right")
            conf_table.add_column("Min", justify="right")
            conf_table.add_column("Max", justify="right")

            for field, scores in self.metrics.field_confidence_scores.items():
                if scores:
                    conf_table.add_row(
                        field,
                        f"{statistics.mean(scores):.2f}",
                        f"{min(scores):.2f}",
                        f"{max(scores):.2f}",
                    )

            console.print(conf_table)

        # Detailed failures
        failures = [r for r in self.results if not r.success]
        if failures and len(failures) <= 10:
            console.print("\n[bold]Detailed Failures:[/bold]")
            for result in failures[:5]:
                console.print(
                    f"\n[red]Failed:[/red] {result.filename} ({result.category})"
                )
                console.print(f"  Error: {result.error_message}")
                if result.extracted_data:
                    console.print(
                        f"  Partial data: {list(result.extracted_data.keys())}"
                    )

    def save_results(self, output_path: Path):
        """Save detailed results to JSON file."""
        output_data = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "total_files_tested": self.metrics.total_attempts,
                "success_rate": (
                    (
                        self.metrics.successful_extractions
                        / self.metrics.total_attempts
                        * 100
                    )
                    if self.metrics.total_attempts > 0
                    else 0
                ),
            },
            "metrics": asdict(self.metrics),
            "detailed_results": [asdict(r) for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        console.print(f"\n[green]Results saved to {output_path}[/green]")


async def test_openai_connection(api_key: str, model: str = "gpt-4o-mini"):
    """Test OpenAI API connection before running full tests."""
    console.print("\n[yellow]Testing OpenAI API connection...[/yellow]")

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'API connection successful' in JSON format",
                }
            ],
            temperature=0,
            max_tokens=50,
            response_format={"type": "json_object"},
        )

        result = response.choices[0].message.content
        console.print(f"[green]✓ OpenAI API connection successful![/green]")
        console.print(f"[dim]Model: {model}[/dim]")
        console.print(f"[dim]Response: {result}[/dim]\n")
        return True

    except Exception as e:
        console.print(f"[red]✗ OpenAI API connection failed![/red]")
        console.print(f"[red]Error: {type(e).__name__}: {str(e)}[/red]")

        if "api_key" in str(e).lower():
            console.print("\n[yellow]Check your API key:[/yellow]")
            console.print("1. Ensure OPENAI_API_KEY is set in .env file")
            console.print("2. API key should start with 'sk-'")
            console.print("3. Check if the key has credits/is active")
        elif "model" in str(e).lower():
            console.print(f"\n[yellow]Model '{model}' may not be available.[/yellow]")
            console.print("Try using 'gpt-3.5-turbo' instead")

        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test LLM extraction on resume PDFs")
    parser.add_argument(
        "--prompt-version",
        choices=["V1", "V2", "V3"],
        default="V2",
        help="Which prompt version to use",
    )
    parser.add_argument(
        "--test-category",
        choices=["all"] + list(TEST_CATEGORIES.keys()),
        default="all",
        help="Which category of resumes to test",
    )
    parser.add_argument(
        "--use-confidence", action="store_true", help="Use confidence scoring prompt"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("extraction_results.json"),
        help="Output file for detailed results",
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment[/red]")
        console.print("Please set it in .env file or export it")
        console.print("\nExample .env file content:")
        console.print("OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx")
        return

    # Mask API key for display
    masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
    console.print(f"[dim]Using API key: {masked_key}[/dim]")

    # Test OpenAI connection first
    model = "gpt-4o-mini"  # Using the most cost-effective model
    if not await test_openai_connection(api_key, model):
        console.print("\n[red]Fix the API connection issue before proceeding.[/red]")
        console.print("\nAlternative models to try:")
        console.print("- gpt-3.5-turbo")
        console.print("- gpt-4-turbo-preview")
        return

    # Initialize components
    extractor = ResumeExtractor(api_key)
    harness = TestHarness(extractor)

    # Determine test directory
    test_dir = Path(__file__).parent / "test_resumes"
    if not test_dir.exists():
        console.print(f"[red]Error: Test directory {test_dir} not found[/red]")
        console.print("Please create it and add test PDFs in category subdirectories")
        return

    # Run tests
    console.print(
        f"[bold green]RecruiterRadar LLM Extraction Test Harness[/bold green]"
    )
    console.print(f"Prompt Version: {args.prompt_version}")
    console.print(
        f"Confidence Scoring: {'Enabled' if args.use_confidence else 'Disabled'}"
    )
    console.print(f"Test Category: {args.test_category}\n")

    categories_to_test = (
        list(TEST_CATEGORIES.keys())
        if args.test_category == "all"
        else [args.test_category]
    )

    for category in categories_to_test:
        console.rule(f"[bold cyan]Testing {category} resumes[/bold cyan]")
        if category in TEST_CATEGORIES:
            console.print(f"Description: {TEST_CATEGORIES[category]['description']}\n")

        results = await harness.run_category_tests(
            category,
            test_dir,
            args.prompt_version,
            args.use_confidence or USE_CONFIDENCE_SCORES,
        )
        harness.results.extend(results)

    # Update metrics and print results
    harness.update_metrics()
    harness.print_results()

    # Save results
    harness.save_results(args.output)

    # Print recommendations
    console.rule("[bold yellow]Recommendations[/bold yellow]")

    success_rate = (
        (harness.metrics.successful_extractions / harness.metrics.total_attempts * 100)
        if harness.metrics.total_attempts > 0
        else 0
    )

    if success_rate >= 90:
        console.print(
            "[green]✅ Excellent extraction rate! This prompt version is production-ready.[/green]"
        )
    elif success_rate >= 80:
        console.print(
            "[yellow]⚠️  Good extraction rate, but consider iterating on the prompt for edge cases.[/yellow]"
        )
    else:
        console.print(
            "[red]❌ Extraction rate below target. Significant prompt improvements needed.[/red]"
        )

    if harness.metrics.common_missing_fields:
        top_missing = list(harness.metrics.common_missing_fields.keys())[0]
        console.print(f"\n💡 Focus on improving extraction for '{top_missing}' field")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Review failed extractions in the output JSON")
    console.print("2. Adjust prompt based on common failure patterns")
    console.print("3. Re-run tests with updated prompt version")
    console.print("4. Once >80% success rate achieved, proceed to Phase 1")


if __name__ == "__main__":
    asyncio.run(main())
