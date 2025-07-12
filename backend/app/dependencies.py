from fastapi import Request, Depends
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.comparison_service import ComparisonService

# from app.services.chroma_connector import ChromaConnector # If needed directly


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


def get_comparison_service(
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> ComparisonService:
    """
    Dependency to get the ComparisonService instance.
    Creates a new instance with injected dependencies for each request.
    """
    return ComparisonService(llm_service=llm_service, rag_service=rag_service)


# def get_chroma_connector(request: Request) -> ChromaConnector:
# """
# Dependency to get the ChromaConnector instance from the application state.
# """
#     return request.app.state.chroma_connector
