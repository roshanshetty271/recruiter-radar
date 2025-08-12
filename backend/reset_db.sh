#!/bin/bash
# Quick database reset script for RecruiterRadar testing

echo "🔄 RecruiterRadar Database Reset"
echo "================================="

# Check if we're in the backend directory
if [ ! -f "cleanup_database.py" ]; then
    echo "❌ Error: Run this script from the backend/ directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "🔧 Activating virtual environment..."
    
    if [ -f ".venv/Scripts/activate" ]; then
        # Windows
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        # Unix/Linux/Mac
        source .venv/bin/activate
    else
        echo "❌ Virtual environment not found. Please activate it manually:"
        echo "   Windows: .venv\\Scripts\\activate"
        echo "   Unix/Mac: source .venv/bin/activate"
        exit 1
    fi
fi

echo "🎯 Performing full database reset (recommended for testing)..."
echo "   - Clearing all ChromaDB data"
echo "   - Reloading demo candidates"
echo ""

python cleanup_database.py --full-reset

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database reset complete! Ready for testing uploads."
else
    echo ""
    echo "❌ Database reset failed. Check the error messages above."
    exit 1
fi 