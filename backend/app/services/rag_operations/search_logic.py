import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb  # For type hinting collection: chromadb.api.models.Collection.Collection
from ..search_utils import skills_match_fuzzy, boost_relevance_score
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchOperationError(Exception):
    """Custom error for search operations."""

    pass


async def execute_similarity_search(
    collection: chromadb.api.models.Collection.Collection,
    query_embedding: List[float],
    query_text: str,  # Required for logging and context
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> tuple[List[Dict[str, Any]], int]:
    """Core logic for similarity search, filtering, and skills post-filtering.

    Args:
        collection: ChromaDB collection instance
        query_embedding: The embedded query vector
        query_text: Original query text for logging and context
        k: Number of results to return after filtering
        filters: Metadata filters including skills_query for post-filtering

    Returns:
        Tuple of (filtered_results, count_before_post_filter)
    """
    if not query_embedding:
        logger.error(
            "execute_similarity_search: Invalid or empty query_embedding provided."
        )
        raise ValueError("query_embedding cannot be empty.")

    skills_to_post_filter = filters.get("skills_query") if filters else None
    location_to_post_filter = filters.get("location") if filters else None
    post_filter_threshold_multiplier = 3
    n_results_chroma = (
        k * post_filter_threshold_multiplier
        if (skills_to_post_filter or location_to_post_filter)
        else k
    )

    # If chunking is enabled, increase results to account for multiple chunks per candidate
    if settings.enable_smart_chunking:
        logger.debug("Smart chunking enabled, adjusting n_results for search.")
        chunk_multiplier = (
            5 if (skills_to_post_filter or location_to_post_filter) else 3
        )
        n_results_chroma = k * chunk_multiplier

    collection_count = await asyncio.to_thread(collection.count)
    logger.info(f"ChromaDB collection has {collection_count} total documents")
    n_results_chroma = min(
        n_results_chroma, collection_count if collection_count > 0 else k, 100
    )

    chroma_where_clause: Optional[Dict[str, Any]] = None
    if filters:
        current_filters = {}
        for key, value in filters.items():
            if key not in ["skills_query", "location"] and value is not None:
                current_filters[key] = value

        if current_filters:
            # ChromaDB needs $and operator for multiple conditions
            if len(current_filters) > 1:
                chroma_where_clause = {
                    "$and": [{key: value} for key, value in current_filters.items()]
                }
            else:
                # Single filter doesn't need $and
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

    # Split query into terms for relevance boosting
    query_terms = [term.strip() for term in query_text.lower().split() if term.strip()]

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
        # Apply relevance boosting
        formatted_res["relevance_score"] = boost_relevance_score(
            formatted_res, query_terms
        )
        formatted_results.append(formatted_res)

    # Sort by relevance score
    formatted_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    count_before_post_filter = len(formatted_results)
    logger.info(
        f"execute_similarity_search: Retrieved {count_before_post_filter} candidates from ChromaDB before skills post-filtering."
    )

    if skills_to_post_filter and formatted_results:
        logger.debug(
            f"execute_similarity_search: Applying fuzzy skills matching for: {skills_to_post_filter}"
        )
        final_filtered_results: List[Dict[str, Any]] = []
        for candidate_data in formatted_results:
            candidate_skills_str = candidate_data.get("metadata", {}).get("skills", "")
            candidate_skills_list = (
                [s.strip() for s in candidate_skills_str.split(",") if s.strip()]
                if isinstance(candidate_skills_str, str)
                else []
            )

            if skills_match_fuzzy(skills_to_post_filter, candidate_skills_list):
                final_filtered_results.append(candidate_data)

        formatted_results = final_filtered_results
        logger.info(
            f"execute_similarity_search: {len(formatted_results)} candidates remaining after fuzzy skills matching."
        )

    # Location post-filtering (substring match)
    if location_to_post_filter and formatted_results:
        logger.debug(
            f"execute_similarity_search: Applying post-retrieval location filter for: {location_to_post_filter}"
        )
        location_filtered_results: List[Dict[str, Any]] = []
        for candidate_data in formatted_results:
            candidate_location = candidate_data.get("metadata", {}).get("location", "")
            if (
                isinstance(candidate_location, str)
                and location_to_post_filter.lower() in candidate_location.lower()
            ):
                location_filtered_results.append(candidate_data)
        formatted_results = location_filtered_results
        logger.info(
            f"execute_similarity_search: {len(formatted_results)} candidates remaining after location post-filtering."
        )

    if formatted_results and (skills_to_post_filter or location_to_post_filter):
        logger.info(f"Post-filtering {len(formatted_results)} results...")
        filtered_results = formatted_results
        logger.info(f"Post-filtering complete: {len(filtered_results)} results remain.")
        formatted_results = filtered_results

    # If smart chunking is enabled, deduplicate results by parent_id
    if settings.enable_smart_chunking and formatted_results:
        logger.debug("Deduplicating chunked results by parent_id")

        # Group results by parent_id, keeping the best scoring chunk
        parent_results: Dict[str, Dict[str, Any]] = {}
        for result in formatted_results:
            # Assuming metadata is present and contains parent_id or id
            metadata = result.get("metadata", {})
            parent_id = metadata.get("parent_id", result.get("id"))

            if not parent_id:
                continue

            current_score = result.get("relevance_score", 0.0)

            # If this is the first chunk from this parent, or it has a better score
            if parent_id not in parent_results or current_score > parent_results[
                parent_id
            ].get("relevance_score", 0.0):
                # Update the ID to be the parent ID for consistent display
                result["id"] = parent_id
                parent_results[parent_id] = result

        # Convert back to list maintaining score order
        # Sort by the score of the best chunk we kept for each parent
        final_results = sorted(
            parent_results.values(),
            key=lambda x: x.get("relevance_score", 0.0),
            reverse=True,
        )

        logger.info(
            f"Deduplicated to {len(final_results)} unique candidates "
            f"from chunked search results."
        )
        formatted_results = final_results

    return formatted_results[:k], count_before_post_filter
