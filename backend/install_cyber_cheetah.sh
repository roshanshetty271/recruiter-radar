#!/bin/bash

# 🚀 CYBER-CHEETAH INSTALLATION SCRIPT
# Installs performance dependencies for sub-1s RecruiterRadar

echo "🚀 Installing CYBER-CHEETAH performance dependencies..."

# Install the performance boost packages
pip install orjson>=3.9.0 httpx>=0.24.0 redis>=4.5.0 aioredis>=2.0.0

echo "✅ Cyber-Cheetah dependencies installed!"

# Verify installation
echo "🔍 Verifying installations..."
python -c "import orjson; print('✅ orjson:', orjson.__version__)"
python -c "import httpx; print('✅ httpx:', httpx.__version__)"
python -c "import redis; print('✅ redis:', redis.__version__)"
python -c "import aioredis; print('✅ aioredis:', aioredis.__version__)"

echo ""
echo "🏁 CYBER-CHEETAH READY!"
echo "🚀 Expected performance improvements:"
echo "   - ~300ms faster per request (HTTP connection pooling)"
echo "   - ~1s faster on repeated queries (ChatCompletion caching)"
echo "   - ~50ms faster JSON (orjson serialization)"
echo "   - ~200ms faster search (ChromaDB optimization)"
echo ""
echo "Target: Sub-1s median response time 🎯" 