import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.query_enhancement_service import QueryEnhancementService


async def test_query():
    try:
        print("🧪 Testing query enhancement for 'show me web developers'...")
        service = QueryEnhancementService()
        result = await service.enhance_query("show me web developers")

        print(f"📋 Role: {result.query_intent.role}")
        print(
            f"🎯 Required Skills: {[s.skill for s in result.query_intent.required_skills]}"
        )
        print(
            f"⭐ Preferred Skills: {[s.skill for s in result.query_intent.preferred_skills]}"
        )
        print(f"🔍 Has Skills Filter: {result.query_intent.has_skills_filter()}")
        print(f"📊 Confidence: {result.query_intent.confidence_score}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_query())
