import logging
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
)  # , Request, HTTPException, status # Request, HTTPException, status not used directly here yet
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.services.llm_service import (
    LLMService,
    OpenAIConfigError,
    LLMServiceError,
)
from backend.app.services.chroma_connector import (
    ChromaConnector,
    ChromaConfigError,
    ChromaConnectionError,
)
from backend.app.services.rag_service import RAGService, RAGServiceError

from backend.app.api.routers import candidate_router  # Corrected import

# from backend.app.api.routers import health_router # Placeholder, health is in main for now

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan: Initializing services...")
    try:
        # Make settings available via app.state if needed, though services take it directly
        app.state.settings = settings

        # Initialize LLMService
        app.state.llm_service = LLMService(settings_obj=settings)
        logger.info("LLMService initialized.")

        # Initialize ChromaConnector
        app.state.chroma_connector = ChromaConnector(settings_obj=settings)
        logger.info("ChromaConnector initialized.")

        # Initialize RAGService, injecting the connector and settings
        app.state.rag_service = RAGService(
            settings_obj=settings, connector=app.state.chroma_connector
        )
        logger.info("RAGService initialized.")

        logger.info("Lifespan: All services initialized successfully.")
    except (
        OpenAIConfigError,
        ChromaConfigError,
        ChromaConnectionError,
        RAGServiceError,
    ) as e:
        logger.critical(
            f"Lifespan: CRITICAL - Service initialization failed: {e}", exc_info=True
        )
        raise RuntimeError(f"Service initialization failed: {e}") from e
    except Exception as e:
        logger.critical(
            f"Lifespan: CRITICAL - Unexpected error during service initialization: {e}",
            exc_info=True,
        )
        raise RuntimeError(
            f"Unexpected error during service initialization: {e}"
        ) from e

    yield

    logger.info("Lifespan: Cleaning up services (if applicable)...")
    # Add cleanup here if services need explicit closing
    logger.info("Lifespan: Shutdown complete.")


app = FastAPI(
    title=(
        settings.app_name
        if hasattr(settings, "app_name") and settings.app_name
        else "RecruiterRadar MVP API"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
origins = [
    "http://localhost:3000",  # Next.js default dev port
    "http://127.0.0.1:3000",
]

# Optional: make it config driven by adding settings.frontend_url to origins
if hasattr(settings, "frontend_url") and settings.frontend_url:
    if settings.frontend_url not in origins:
        origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Placeholder for Health Check Endpoint (can be in main.py or a separate router)
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "API is healthy"}


# Include API routers
app.include_router(candidate_router.router, prefix="/api/v1", tags=["Candidates"])
# app.include_router(health_router.router, prefix="/health", tags=["Health"]) # if moved to its own router

# Configure basic logging for the application
logging.basicConfig(
    level=settings.log_level if hasattr(settings, "log_level") else logging.INFO
)

logger.info("Application startup complete.")

# To run this app (from the backend directory):
# uvicorn app.main:app --reload
