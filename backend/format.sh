#!/bin/bash
# Backend Python Formatting & Linting Script
# Run this when you want to polish the Python code

echo "🔧 Formatting Python code with Black..."
black .

echo "🔍 Running Flake8 linting (relaxed rules)..."
flake8 . --max-line-length=100 --ignore=E203,W503 --statistics

echo "✅ Backend formatting complete!" 