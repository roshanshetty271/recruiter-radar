"""
Feature flags for RecruiterRadar MVP.
Demonstrates production thinking even in MVP stage.
"""

# Upload features
ENABLE_BATCH_UPLOAD = False  # V2: Allow multiple file uploads at once
ENABLE_DRAG_DROP_FOLDER = False  # V2: Drag entire folders
ENABLE_RESUME_PREVIEW = False  # V2: Show PDF preview before processing
MAX_FILE_SIZE_MB = 10  # Current limit

# Processing features
ENABLE_PARALLEL_EXTRACTION = False  # V2: Process multiple PDFs simultaneously
ENABLE_OCR_FALLBACK = False  # V2: Use OCR for scanned PDFs
ENABLE_MULTILINGUAL_EXTRACTION = False  # V2: Support non-English resumes
USE_CONFIDENCE_SCORES = True  # MVP: Track extraction confidence

# Chat features
ENABLE_CONVERSATION_MEMORY = False  # V2: Remember full conversation context
ENABLE_VOICE_INPUT = False  # V2: Voice-to-text queries
ENABLE_SUGGESTED_QUESTIONS = True  # MVP: Show query suggestions
MAX_CHAT_CONTEXT_LENGTH = 3  # Number of previous messages to consider

# Storage features
ENABLE_PERSISTENT_SESSIONS = False  # V2: Save sessions to database
ENABLE_RESUME_VERSIONING = False  # V2: Track multiple versions of same resume
SESSION_DURATION_HOURS = 48  # How long to keep session data

# Export features
ENABLE_PDF_EXPORT = False  # V2: Export results as PDF
ENABLE_INTEGRATION_EXPORT = False  # V2: Direct export to ATS/CRM
ENABLE_BULK_ACTIONS = False  # V2: Select multiple candidates for actions

# Analytics features
ENABLE_DETAILED_ANALYTICS = False  # V2: Track detailed usage patterns
ENABLE_AB_TESTING = False  # V2: A/B test different prompts
TRACK_EXTRACTION_METRICS = True  # MVP: Basic success/failure tracking

# Performance features
ENABLE_REDIS_CACHE = False  # V2: Cache LLM responses
ENABLE_WEBSOCKET_UPDATES = False  # V2: Real-time progress updates
ENABLE_CDN_ASSETS = False  # V2: Use CDN for static assets

# Security features
ENABLE_RATE_LIMITING = True  # MVP: Basic rate limiting
ENABLE_API_KEY_AUTH = False  # V2: Require API keys
ENABLE_ENCRYPTION_AT_REST = False  # V2: Encrypt stored resumes

# Development features
ENABLE_DEBUG_MODE = True  # MVP: Verbose logging
ENABLE_MOCK_LLM = False  # For testing without OpenAI API
SHOW_PROCESSING_TIMES = True  # MVP: Display timing metrics

def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a feature is enabled.
    In V2, this could check a database or external config service.
    """
    return globals().get(feature_name, False)

def get_feature_config(feature_name: str, default=None):
    """
    Get feature configuration value.
    """
    return globals().get(feature_name, default)
