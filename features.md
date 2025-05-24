### ✅ BE-6: Basic FastAPI Application Setup
**Status:** DONE 🚀
**Branch:** `feature/BE-6-fastapi-setup`
**Description:**
Established the core FastAPI application structure in `backend/app/main.py`. This includes:
-   **FastAPI App Initialization:** Basic app setup with title and version.
-   **Lifespan Management:** Implemented an `asynccontextmanager` named `lifespan` to initialize and manage the lifecycle of key services (`LLMService`, `ChromaConnector`, `RAGService`). Services are instantiated on startup and stored in `app.state` for application-wide access. Robust error handling is included for service initialization.
-   **CORS Middleware:** Configured `CORSMiddleware` to allow requests from the frontend (e.g., `http://localhost:3000`).
-   **Dependency Injection Setup:** Created `backend/app/dependencies.py` with provider functions (e.g., `get_llm_service`, `get_rag_service`) that retrieve service instances from `app.state` via `request.app.state`. These will be used by API endpoints.
-   **API Router Structure:** Set up the `backend/app/api/routers/` directory with an `__init__.py` and a shell `candidate_router.py` containing an empty `APIRouter`.
-   **Health Check Endpoint:** Added a `/health` endpoint to `main.py` for basic API health monitoring.
-   **Configuration Integration:** Ensured services and app settings are driven by `app.core.config.settings`.
-   **Logging:** Basic logging setup in `main.py`.
**Key Files Touched/Created:**
-   `backend/app/main.py` (Modified)
-   `backend/app/dependencies.py` (Created)
-   `backend/app/api/routers/__init__.py` (Created)
-   `backend/app/api/routers/candidate_router.py` (Created)
**Next Steps:** BE-7: Candidate Search Endpoint (`/query`) & RAG Logic.

--- 