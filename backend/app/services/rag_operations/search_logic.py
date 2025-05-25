import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb  # For type hinting collection: chromadb.api.models.Collection.Collection

logger = logging.getLogger(__name__)


class SearchOperationError(Exception):
    """Custom error for search operations."""

    pass


async def execute_similarity_search(
    collection: chromadb.api.models.Collection.Collection,
    query_embedding: List[float],
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> tuple[List[Dict[str, Any]], int]:
    """Core logic for similarity search, filtering, and skills post-filtering."""
    if not query_embedding:
        logger.error(
            "execute_similarity_search: Invalid or empty query_embedding provided."
        )
        raise ValueError("query_embedding cannot be empty.")

    skills_to_post_filter = filters.get("skills_query") if filters else None
    n_results_chroma = k * 3 if skills_to_post_filter else k

    collection_count = await asyncio.to_thread(collection.count)
    n_results_chroma = min(
        n_results_chroma, collection_count if collection_count > 0 else k, 100
    )

    chroma_where_clause: Optional[Dict[str, Any]] = None
    if filters:
        current_filters = {}
        for key, value in filters.items():
            if key not in ["skills_query"] and value is not None:
                current_filters[key] = value
        if current_filters:
            chroma_where_clause = current_filters

    logger.debug(
        f"execute_similarity_search: ChromaDB query: n_results={n_results_chroma}, where_clause={chroma_where_clause}, "
        f"include=['metadatas', 'documents', 'distances']"
    )

    try:
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=n_results_chroma,
            where=chroma_where_clause,
            include=["metadatas", "documents", "distances"],
        )
    except Exception as e:
        logger.error(
            f"execute_similarity_search: ChromaDB query failed: {e}", exc_info=True
        )
        raise SearchOperationError(f"ChromaDB query failed: {e}") from e

    formatted_results: List[Dict[str, Any]] = []
    if not results or not results.get("ids") or not results["ids"][0]:
        logger.info(
            "execute_similarity_search: No initial results found from ChromaDB."
        )
        return [], 0

    res_ids = results["ids"][0]

    # Robust defaulting for documents, metadatas, and distances
    num_ids = len(res_ids)

    temp_docs = (
        results.get("documents", [[]])[0]
        if results.get("documents") and results["documents"]
        else []
    )
    res_docs = temp_docs if len(temp_docs) == num_ids else ([None] * num_ids)

    temp_metadatas = (
        results.get("metadatas", [[]])[0]
        if results.get("metadatas") and results["metadatas"]
        else []
    )
    res_metadatas = (
        temp_metadatas if len(temp_metadatas) == num_ids else ([{}] * num_ids)
    )

    temp_distances = (
        results.get("distances", [[]])[0]
        if results.get("distances") and results["distances"]
        else []
    )
    res_distances = (
        temp_distances if len(temp_distances) == num_ids else ([None] * num_ids)
    )

    for i in range(len(res_ids)):
        doc_id = (
            res_metadatas[i].get("candidate_id", res_ids[i])
            if res_metadatas[i]
            else res_ids[i]
        )
        formatted_res = {
            "id": doc_id,
            "document": res_docs[i],
            "metadata": res_metadatas[i] or {},
            "distance": res_distances[i],
        }
        formatted_results.append(formatted_res)

    count_before_post_filter = len(formatted_results)
    logger.info(
        f"execute_similarity_search: Retrieved {count_before_post_filter} candidates from ChromaDB before skills post-filtering."
    )

    if skills_to_post_filter and formatted_results:
        logger.debug(
            f"execute_similarity_search: Applying post-retrieval skills filter for: {skills_to_post_filter}"
        )
        final_filtered_results: List[Dict[str, Any]] = []
        for candidate_data in formatted_results:
            candidate_skills_str = candidate_data.get("metadata", {}).get("skills", "")
            candidate_skills_list = (
                [
                    s.strip().lower()
                    for s in candidate_skills_str.split(",")
                    if s.strip()
                ]
                if isinstance(candidate_skills_str, str)
                else []
            )

            match_all_skills = True
            for required_skill in skills_to_post_filter:
                if required_skill.strip().lower() not in candidate_skills_list:
                    match_all_skills = False
                    break
            if match_all_skills:
                final_filtered_results.append(candidate_data)

        formatted_results = final_filtered_results
        logger.info(
            f"execute_similarity_search: {len(formatted_results)} candidates remaining after skills post-filtering."
        )

    return formatted_results[:k], count_before_post_filter
