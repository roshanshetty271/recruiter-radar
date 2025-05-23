#!/bin/bash
# Frontend JavaScript/React Formatting & Linting Script
# Run this when you want to polish the frontend code

echo "🎨 Formatting JavaScript/React code with Prettier..."
npx prettier --write .

echo "🔍 Running ESLint with auto-fix..."
npx eslint . --fix --ext .js,.jsx,.ts,.tsx

echo "✅ Frontend formatting complete!" 