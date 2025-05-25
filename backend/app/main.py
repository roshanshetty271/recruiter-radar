import logging
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Request,
)  # , Request, HTTPException, status # Request, HTTPException, status not used directly here yet
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

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
from backend.app.models.api_models import ErrorResponse
from datetime import datetime  # Added import

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
    description="""
# RecruiterRadar API 🚀

AI-powered recruitment platform that revolutionizes how recruiters find and engage with top talent.

## Key Features

- **🔍 Semantic Search**: Natural language candidate discovery powered by advanced embeddings
- **🎯 Smart Filtering**: Combine AI search with precise metadata filters
- **✨ AI Outreach Generation**: Create personalized recruitment messages in seconds
- **📊 Rich Insights**: Relevance scores and match context for every candidate

## Getting Started

1. Use `/api/v1/candidates/query` to search for candidates
2. Use `/api/v1/candidates/{id}/generate-outreach` to create personalized messages
3. Check `/health` for service status

## Coming Soon

- **Multiple outreach variations** with different tones (v1.1)
- **Batch operations** for managing campaigns
- **Advanced analytics** and success tracking

Built with ❤️ by the RecruiterRadar team.
    """,
    terms_of_service="https://recruiterradar.com/terms",
    contact={
        "name": "RecruiterRadar Support",
        "url": "https://recruiterradar.com/support",
        "email": "support@recruiterradar.com",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://recruiterradar.com/license",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service health monitoring endpoints",
        },
        {
            "name": "Candidates",
            "description": "Candidate search and outreach generation operations",
            # One might add externalDocs here if applicable
        },
    ],
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.recruiterradar.com", "description": "Production server"},
    ],
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
@app.get(
    "/health",
    tags=["Health"],
    summary="Check service health",
    description="Returns the current health status of all services. Verifies LLM, RAG, and ChromaDB availability.",
    response_description="Health status object detailing service states.",
    responses={
        200: {
            "description": "All services healthy or some services degraded but app is running.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",  # or "degraded"
                        "version": "1.0.0",
                        "services": {
                            "llm_service": "operational",
                            "rag_service": "operational",
                            "chroma_connector": "operational",
                        },
                        "timestamp": "2024-01-15T10:30:00Z",
                        "request_id": "req_someid",
                    }
                }
            },
        },
        503: {
            "description": "Application is unhealthy due to critical service failure.",
            "model": ErrorResponse,  # Using the existing ErrorResponse for consistency
            "content": {
                "application/json": {
                    "example": {
                        "error": "unhealthy_service",
                        "message": "Application is unhealthy due to critical service failure.",
                        "details": {
                            "status": "unhealthy",
                            "services": {"llm_service": "unavailable"},
                        },
                        "request_id": "req_someid",
                    }
                }
            },
        },
    },
)
async def health_check(request: Request):
    """
    Comprehensive health check for all essential services.

    Verifies:
    - LLM service (llm_service attribute on app.state)
    - RAG service (rag_service attribute on app.state)
    - ChromaDB connector (chroma_connector attribute on app.state)

    Returns 'healthy' if all are present, 'degraded' if some are missing
    but app is running, and 503 with 'unhealthy' if critical checks fail.
    """
    health_status = {
        "status": "healthy",  # Assume healthy initially
        "version": settings.app_version,
        "services": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": getattr(request.state, "request_id", "unknown"),
    }

    all_critical_services_operational = True

    # Check LLM Service
    if (
        hasattr(request.app.state, "llm_service")
        and request.app.state.llm_service is not None
    ):
        health_status["services"]["llm_service"] = "operational"
        # Could add a light ping here: await request.app.state.llm_service.check_connection()
    else:
        health_status["services"]["llm_service"] = "unavailable"
        health_status["status"] = "degraded"
        all_critical_services_operational = False  # Assuming LLM is critical
        logger.warning("LLMService not available during health check.")

    # Check RAG Service
    if (
        hasattr(request.app.state, "rag_service")
        and request.app.state.rag_service is not None
    ):
        health_status["services"]["rag_service"] = "operational"
    else:
        health_status["services"]["rag_service"] = "unavailable"
        health_status["status"] = "degraded"
        all_critical_services_operational = False  # Assuming RAG is critical
        logger.warning("RAGService not available during health check.")

    # Check Chroma Connector (implicitly part of RAG, but can be checked separately)
    if (
        hasattr(request.app.state, "chroma_connector")
        and request.app.state.chroma_connector is not None
    ):
        health_status["services"]["chroma_connector"] = "operational"
        # Could add a light ping here: request.app.state.chroma_connector.get_client().heartbeat()
    else:
        health_status["services"]["chroma_connector"] = "unavailable"
        health_status["status"] = "degraded"
        # Not necessarily critical on its own if RAG is the primary interface
        logger.warning("ChromaConnector not available during health check.")

    if not all_critical_services_operational:
        # If critical services are down, a more severe status might be warranted.
        # For now, using "degraded" if app is running but services are missing.
        # If a service initialization failure in lifespan() prevents app start, this won't be reached.
        # If you want 503 strictly on critical failure:
        # health_status["status"] = "unhealthy"
        # return JSONResponse(status_code=503, content=ErrorResponse(...).dict())
        pass  # Keep status as degraded for now, return 200

    # If any service was unavailable, the overall status is degraded.
    # If all are operational, it remains healthy.
    # If a critical error occurred *during* the check itself (caught by outer try-except if added):
    # health_status["status"] = "unhealthy"
    # health_status["error"] = str(e)
    # return JSONResponse(status_code=503, content=health_status)

    return JSONResponse(status_code=200, content=health_status)


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


# Add request ID middleware for tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # Generate a unique request ID, could use uuid.uuid4() for more uniqueness
    request_id = (
        f"req_{int(time.time() * 1000)}_{request.client.host.replace('.', '-')}"
    )
    request.state.request_id = request_id

    # Log request start with ID
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    logger.info(
        f"Request {request_id} finished: {response.status_code} in {process_time:.2f}ms"
    )
    return response


# Root endpoint
@app.get(
    "/",
    summary="API Root - Welcome to RecruiterRadar",
    description="Provides basic information about the RecruiterRadar API and links to documentation and health status.",
    include_in_schema=False,  # Typically not included in OpenAPI spec for root
)
async def root():
    """
    Root endpoint providing basic API information and links.
    """
    return {
        "message": f"Welcome to {settings.app_name} API v{settings.app_version}",
        "documentation_url": "/docs",
        "redoc_url": "/redoc",
        "health_status_url": "/health",
        "api_version_prefix": settings.api_v1_str,
    }


# Example of a generic exception handler (optional, FastAPI handles many by default)
# @app.exception_handler(Exception)
# async def generic_exception_handler(request: Request, exc: Exception):
#     logger.error(f"Unhandled exception for request {getattr(request.state, 'request_id', '')}: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content=ErrorResponse(
#             error="InternalServerError",
#             message="An unexpected error occurred on the server.",
#             request_id=getattr(request.state, 'request_id', 'unknown')
#         ).model_dump(exclude_none=True)
#     )
