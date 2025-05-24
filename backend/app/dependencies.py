from fastapi import Request
from backend.app.services.llm_service import LLMService
from backend.app.services.rag_service import RAGService

# from backend.app.services.chroma_connector import ChromaConnector # If needed directly


def get_llm_service(request: Request) -> LLMService:
    """
    Dependency to get the LLMService instance from the application state.
    """
    return request.app.state.llm_service


def get_rag_service(request: Request) -> RAGService:
    """
    Dependency to get the RAGService instance from the application state.
    """
    return request.app.state.rag_service


# def get_chroma_connector(request: Request) -> ChromaConnector:
# """
# Dependency to get the ChromaConnector instance from the application state.
# """
#     return request.app.state.chroma_connector
