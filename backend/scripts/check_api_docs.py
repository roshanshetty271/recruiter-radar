"""
Script to verify API documentation completeness
"""

import requests
import json
from typing import (
    Dict,
    List,
)  # Ensure List is imported if used, though not in current snippet


def check_api_docs(base_url: str = "http://localhost:8000"):
    """Check OpenAPI docs for completeness"""

    openapi_url = f"{base_url}/openapi.json"
    print(f"Attempting to fetch OpenAPI schema from: {openapi_url}")

    try:
        response = requests.get(openapi_url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        schema = response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching OpenAPI schema: {e}")
        print(
            "Please ensure the FastAPI server is running and accessible at the specified base_url."
        )
        return
    except json.JSONDecodeError as e:
        print(f"\n❌ Error decoding OpenAPI JSON: {e}")
        print("The server might not be returning valid JSON for the OpenAPI schema.")
        return

    print(
        f"\n🚀 API: {schema.get('info', {}).get('title', 'N/A')} v{schema.get('info', {}).get('version', 'N/A')}"
    )
    description = schema.get("info", {}).get("description", "")
    print(
        f"📝 Description: {description[:100]}{ '...' if len(description) > 100 else ''}"
    )

    # Check endpoints
    print("\n📍 Endpoints:")
    paths = schema.get("paths", {})
    if not paths:
        print("  No paths found in the OpenAPI schema.")

    for path, methods in paths.items():
        for method, details in methods.items():
            summary = details.get("summary", "No summary")
            print(f"  {method.upper()} {path} - {summary}")

            issues = []
            if not details.get("description"):
                issues.append("Missing endpoint description")
            if not details.get("responses"):
                issues.append("Missing endpoint response docs")
            # Summary is checked above, but good to have a consistent check pattern
            if not details.get("summary"):
                issues.append("Missing endpoint summary")
            if not details.get("operationId"):
                issues.append("Missing endpoint operationId")

            if issues:
                print(f"    ⚠️  Issues: {', '.join(issues)}")
            else:
                print(f"    ✅ Fully documented")

    # Check models (components/schemas)
    print("\n📋 Models (Schemas):")
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    if not schemas:
        print("  No schemas (models) found in components.")

    for model_name, model_schema in schemas.items():
        props_count = len(model_schema.get("properties", {}))
        print(f"  {model_name} ({props_count} fields)")

        model_issues = []
        # Pydantic models often have descriptions in the class docstring,
        # which FastAPI includes in the model schema's description.
        if not model_schema.get("description"):
            # This might be too strict if class docstrings are the primary source.
            # Consider checking if model_schema.get('title') has content if description is missing.
            pass  # Commenting out for now as Pydantic models might not always have a separate schema description
            # if the class docstring is used by FastAPI.
            # model_issues.append("Missing model description in schema")

        # Checking for examples directly in the schema (FastAPI uses schema_extra for this often)
        if (
            "example" not in model_schema
            and "examples" not in model_schema
            and not model_schema.get("json_schema_extra", {}).get("example")
        ):
            # Check if Pydantic V1 style schema_extra has example
            config_example = model_schema.get("example", None)  # Pydantic V2
            if not config_example:
                # FastAPI might put this under schema_extra in Pydantic V1
                # For Pydantic models, examples are often in Config.json_schema_extra
                # This check might need adjustment depending on how examples are consistently defined.
                model_issues.append("Missing model examples (or schema_extra example)")

        # Check field descriptions within properties
        properties = model_schema.get("properties", {})
        for prop_name, prop_details in properties.items():
            if not prop_details.get("description"):
                # model_issues.append(f"Field '{prop_name}' missing description")
                pass  # Field descriptions are good but might make output too verbose for a quick check

        if model_issues:
            print(f"    ⚠️  Model Issues: {', '.join(model_issues)}")
        # else:
        # print(f"    ✅ Model appears well-structured") # Avoid too much noise


if __name__ == "__main__":
    print("Starting API Documentation Check...")
    # You might want to add a CLI argument for base_url if needed
    # import argparse
    # parser = argparse.ArgumentParser(description='Check API docs.')
    # parser.add_argument('--base_url', type=str, default='http://localhost:8000', help='Base URL of the API')
    # args = parser.parse_args()
    # check_api_docs(base_url=args.base_url)
    check_api_docs()
    print("\nDocumentation Check Finished.")
