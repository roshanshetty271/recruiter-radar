import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb  # For type hinting collection: chromadb.api.models.Collection.Collection
from ..search_utils import skills_match_fuzzy, boost_relevance_score

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
    n_results_chroma = (
        k * 3 if (skills_to_post_filter or location_to_post_filter) else k
    )

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

    # Extract skills once for all candidates to avoid performance bottleneck
    from app.services.search_utils import extract_skills_from_query

    extracted_query_skills = extract_skills_from_query(query_text)

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
        # Apply relevance boosting with pre-extracted skills
        formatted_res["relevance_score"] = boost_relevance_score(
            formatted_res, query_terms, extracted_query_skills
        )
        formatted_results.append(formatted_res)

    # Sort by relevance score
    formatted_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    count_before_post_filter = len(formatted_results)
    logger.info(
        f"execute_similarity_search: Retrieved {count_before_post_filter} candidates from ChromaDB before skills post-filtering."
    )

    # Apply fuzzy skills filter if skills are provided
    if skills_to_post_filter:
        logger.info(f"🔍 Skills matching: Required: {skills_to_post_filter}")
        filtered_results = skills_match_fuzzy(formatted_results, skills_to_post_filter)
        logger.info(
            f"📊 {len(filtered_results)} candidates remaining after fuzzy skills matching."
        )
    else:
        filtered_results = formatted_results

    # Sort by preferred match score if available, else by distance
    filtered_results.sort(
        key=lambda x: (x.get("preferred_match_score", 0), -x["distance"])
    )

    # 🗺️ SMART LOCATION POST-FILTERING (using LocationMappingService)
    if location_to_post_filter and filtered_results:
        logger.info(
            f"🗺️ Applying SMART location filter for: '{location_to_post_filter}'"
        )

        # Import the location service
        from app.services.location_service import location_service

        location_filtered_results: List[Dict[str, Any]] = []
        matches_found = 0
        no_matches_logged = []

        for candidate_data in filtered_results:
            candidate_location = candidate_data.get("metadata", {}).get("location", "")
            candidate_name = candidate_data.get("metadata", {}).get("name", "Unknown")

            if isinstance(candidate_location, str) and candidate_location.strip():
                # Use smart location matching instead of broken substring matching
                matches, confidence, reason = location_service.location_matches(
                    search_location=location_to_post_filter,
                    candidate_location=candidate_location,
                    confidence_threshold=0.6,  # Allow more flexible matching
                )

                if matches:
                    location_filtered_results.append(candidate_data)
                    matches_found += 1
                    logger.debug(
                        f"   ✅ MATCH: {candidate_name} in '{candidate_location}' "
                        f"(confidence: {confidence:.2f}, reason: {reason})"
                    )
                else:
                    no_matches_logged.append(
                        f"{candidate_name}: '{candidate_location}' -> {reason}"
                    )

        # Log results summary
        logger.info(f"🗺️ Location filtering results:")
        logger.info(
            f"   ✅ {matches_found} candidates matched location '{location_to_post_filter}'"
        )
        logger.info(
            f"   ❌ {len(filtered_results) - matches_found} candidates filtered out"
        )

        # Log a few examples of non-matches for debugging
        if no_matches_logged and matches_found == 0:
            logger.warning(f"🚨 NO LOCATION MATCHES! Examples of non-matches:")
            for example in no_matches_logged[:3]:  # Show first 3 examples
                logger.warning(f"      {example}")

            # Get suggestions for better search
            suggestions = location_service.get_location_suggestions(
                location_to_post_filter
            )
            if suggestions:
                logger.info(f"💡 Suggestions: {'; '.join(suggestions)}")

        filtered_results = location_filtered_results
        logger.info(
            f"execute_similarity_search: {len(filtered_results)} candidates remaining after SMART location post-filtering."
        )

    return filtered_results[:k], count_before_post_filter
