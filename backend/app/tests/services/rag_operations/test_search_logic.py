import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.rag_operations.search_logic import (
    execute_similarity_search,
    SearchOperationError,
)

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestExecuteSimilaritySearch:
    """
    Unit tests for the execute_similarity_search function.
    """

    @pytest.fixture
    def mock_chroma_collection(self):
        """Fixture to create a mock ChromaDB collection object."""
        collection = MagicMock()
        # Mock methods that will be called by execute_similarity_search
        collection.count = MagicMock(return_value=50)  # Default count
        collection.query = MagicMock()  # Will be configured per test
        return collection

    async def test_basic_successful_search_no_filters(self, mock_chroma_collection):
        """Test basic search returning k results without any filters."""
        mock_query_embedding = [0.1] * 1536  # Example embedding
        k_results = 5

        # Mock ChromaDB response
        mock_chroma_collection.query.return_value = {
            "ids": [["id1", "id2", "id3", "id4", "id5"]],
            "documents": [["doc1", "doc2", "doc3", "doc4", "doc5"]],
            "metadatas": [[{"skill": "python"}, {"skill": "java"}, {}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_chroma_collection.count.return_value = 10  # Ensure count is sufficient

        results = await execute_similarity_search(
            collection=mock_chroma_collection,
            query_embedding=mock_query_embedding,
            k=k_results,
            filters=None,
        )

        assert len(results) == k_results
        assert results[0]["id"] == "id1"
        assert results[0]["document"] == "doc1"
        assert results[0]["metadata"] == {"skill": "python"}
        assert results[0]["distance"] == 0.1
        mock_chroma_collection.query.assert_called_once()
        # Assert n_results in call_args based on no skills_query
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_results
        assert call_args[1]["where"] is None

    async def test_search_with_k_limiting(self, mock_chroma_collection):
        """Test that results are limited to k even if Chroma returns more."""
        mock_query_embedding = [0.2] * 1536
        k_results = 3

        mock_chroma_collection.query.return_value = {
            "ids": [["id1", "id2", "id3", "id4", "id5"]],  # Returns 5
            "documents": [["d1", "d2", "d3", "d4", "d5"]],
            "metadatas": [[{}, {}, {}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_chroma_collection.count.return_value = 5

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, None
        )

        assert len(results) == k_results
        assert results[0]["id"] == "id1"
        assert results[2]["id"] == "id3"

    async def test_search_with_metadata_filters_no_skills(self, mock_chroma_collection):
        """Test search with non-skill metadata filters."""
        mock_query_embedding = [0.3] * 1536
        k_results = 2
        filters = {"location": "Test Location", "experience_years": {"$gte": 3}}

        # Mock return value, assuming Chroma filtered internally
        mock_chroma_collection.query.return_value = {
            "ids": [["filtered_id1", "filtered_id2"]],
            "documents": [["doc_f1", "doc_f2"]],
            "metadatas": [
                [{"location": "Test Location"}, {"location": "Test Location"}]
            ],
            "distances": [[0.15, 0.25]],
        }
        mock_chroma_collection.count.return_value = 2

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == k_results
        mock_chroma_collection.query.assert_called_once_with(
            query_embeddings=[mock_query_embedding],
            n_results=k_results,  # No skills_query, so n_results_chroma = k
            where={"location": "Test Location", "experience_years": {"$gte": 3}},
            include=["metadatas", "documents", "distances"],
        )

    async def test_search_with_skills_post_filtering_match_all(
        self, mock_chroma_collection
    ):
        """Test skills post-filtering where candidates match all required skills."""
        mock_query_embedding = [0.4] * 1536
        k_final_results = 1
        # skills_query implies k*3 for n_results_chroma
        n_results_chroma_expected = k_final_results * 3
        filters = {"skills_query": ["python", "fastapi"]}

        mock_chroma_collection.query.return_value = {
            "ids": [["s_id1", "s_id2", "s_id3"]],
            "documents": [["s_d1", "s_d2", "s_d3"]],
            "metadatas": [
                [
                    {"skills": "Python, FastAPI, Docker"},  # Match
                    {"skills": "Java, Spring"},  # No match
                    {"skills": "Python, Docker"},
                ]  # No match (missing fastapi)
            ],
            "distances": [[0.1, 0.2, 0.3]],
        }
        mock_chroma_collection.count.return_value = 3

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "s_id1"
        assert results[0]["metadata"]["skills"] == "Python, FastAPI, Docker"

        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == n_results_chroma_expected
        assert (
            call_args[1]["where"] is None
        )  # Only skills_query, so no Chroma where clause

    async def test_skills_post_filtering_case_insensitivity(
        self, mock_chroma_collection
    ):
        """Test skills post-filtering is case insensitive."""
        mock_query_embedding = [0.5] * 1536
        k_results = 1
        filters = {"skills_query": ["PYTHON"]}  # Uppercase query skill

        mock_chroma_collection.query.return_value = {
            "ids": [["id_case"]],
            "documents": [["doc_case"]],
            "metadatas": [[{"skills": "python, react"}]],  # Lowercase candidate skill
            "distances": [[0.1]],
        }
        mock_chroma_collection.count.return_value = 1

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "id_case"

    async def test_skills_post_filtering_no_match(self, mock_chroma_collection):
        """Test skills post-filtering when no candidates match the skills criteria."""
        mock_query_embedding = [0.6] * 1536
        k_results = 2
        filters = {"skills_query": ["nonexistent_skill"]}

        mock_chroma_collection.query.return_value = {  # Chroma returns some candidates
            "ids": [["id_a", "id_b"]],
            "documents": [["doc_a", "doc_b"]],
            "metadatas": [[{"skills": "python"}], [{"skills": "java"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_chroma_collection.count.return_value = 2

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 0

    async def test_empty_chromadb_results(self, mock_chroma_collection):
        """Test behavior when ChromaDB query returns no results."""
        mock_query_embedding = [0.7] * 1536
        mock_chroma_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_chroma_collection.count.return_value = 0

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, 5, None
        )

        assert len(results) == 0

    async def test_invalid_query_embedding_raises_valueerror(
        self, mock_chroma_collection
    ):
        """Test that a ValueError is raised for invalid query_embedding."""
        with pytest.raises(ValueError, match="query_embedding cannot be empty"):
            await execute_similarity_search(mock_chroma_collection, None, 5, None)

        with pytest.raises(ValueError, match="query_embedding cannot be empty"):
            await execute_similarity_search(mock_chroma_collection, [], 5, None)

    async def test_chromadb_query_raises_exception(self, mock_chroma_collection):
        """Test that SearchOperationError is raised if collection.query fails."""
        mock_query_embedding = [0.8] * 1536
        mock_chroma_collection.query.side_effect = Exception("ChromaDB internal error")

        with pytest.raises(
            SearchOperationError, match="ChromaDB query failed: ChromaDB internal error"
        ):
            await execute_similarity_search(
                mock_chroma_collection, mock_query_embedding, 5, None
            )

    async def test_n_results_chroma_capping_logic(self, mock_chroma_collection):
        """Test n_results_chroma calculation considering collection count and k*3 for skills."""
        mock_query_embedding = [0.9] * 1536
        k_final = 5

        # Scenario 1: skills_query present, k*3 < collection.count
        filters_with_skills = {"skills_query": ["test"]}
        mock_chroma_collection.count.return_value = 50
        mock_chroma_collection.query.return_value = {"ids": [[]]}  # Minimal mock
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, filters_with_skills
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_final * 3  # 15

        # Scenario 2: skills_query present, k*3 > collection.count
        mock_chroma_collection.count.return_value = 7
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, filters_with_skills
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == 7  # Capped by collection_count

        # Scenario 3: No skills_query, n_results_chroma should be k
        mock_chroma_collection.count.return_value = 50
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, None
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_final  # 5

    async def test_metadata_filters_passed_correctly(self, mock_chroma_collection):
        """Test that metadata filters (excluding skills_query) are passed to ChromaDB correctly."""
        mock_query_embedding = [0.1] * 1536
        k_results = 2
        filters = {
            "location": "Remote",
            "visa_status": "GC",
            "experience_years": {"$gte": 2},
            "skills_query": ["dont_pass_this_to_where"],
        }
        expected_where_clause = {
            "location": "Remote",
            "visa_status": "GC",
            "experience_years": {"$gte": 2},
        }

        mock_chroma_collection.query.return_value = {"ids": [[]]}  # Minimal mock

        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["where"] == expected_where_clause
        # n_results should be k_results * 3 because skills_query is present
        assert call_args[1]["n_results"] == k_results * 3

    # Add more tests for edge cases in skills string parsing (e.g., empty strings, extra commas) if needed
    # Test what happens if metadata["skills"] is not a string or is missing
    async def test_skills_parsing_edge_cases_in_metadata(self, mock_chroma_collection):
        """Test how skills post-filtering handles malformed or missing skills in candidate metadata."""
        mock_query_embedding = [0.1] * 1536
        k_results = 1
        filters = {"skills_query": ["python"]}

        # Scenario 1: skills metadata is None
        # Scenario 2: skills metadata is not a string (e.g., a list already, though our code expects string)
        # Scenario 3: skills metadata is an empty string
        # Scenario 4: skills metadata has extra commas or whitespace

        test_cases_metadata = [
            {
                "id": "c1",
                "metadata": {"skills": None, "name": "Cand1"},
                "doc": "d1",
                "dist": 0.1,
            },  # Should not match "python"
            {
                "id": "c2",
                "metadata": {"skills": ["python", "java"], "name": "Cand2"},
                "doc": "d2",
                "dist": 0.2,
            },  # Code expects string, so this won't match
            {
                "id": "c3",
                "metadata": {"skills": "", "name": "Cand3"},
                "doc": "d3",
                "dist": 0.3,
            },  # Should not match
            {
                "id": "c4",
                "metadata": {"skills": "  python  ,,  java  ", "name": "Cand4"},
                "doc": "d4",
                "dist": 0.4,
            },  # Should match "python"
            {
                "id": "c5",
                "metadata": {"name": "Cand5_no_skills_key"},
                "doc": "d5",
                "dist": 0.5,
            },  # No skills key, should not match
        ]

        mock_chroma_collection.query.return_value = {
            "ids": [[tc["id"] for tc in test_cases_metadata]],
            "documents": [[tc["doc"] for tc in test_cases_metadata]],
            "metadatas": [[tc["metadata"] for tc in test_cases_metadata]],
            "distances": [[tc["dist"] for tc in test_cases_metadata]],
        }
        mock_chroma_collection.count.return_value = len(test_cases_metadata)

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "c4"  # Only c4 should match "python" after parsing
        assert (
            results[0]["metadata"]["skills"] == "  python  ,,  java  "
        )  # Original metadata is preserved


# Example of how to run these tests with pytest:
# Ensure pytest and pytest-asyncio are installed: pip install pytest pytest-asyncio
# Run from the root of your project or backend directory: pytest path/to/test_search_logic.py
# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestExecuteSimilaritySearch:
    """
    Unit tests for the execute_similarity_search function.
    """

    @pytest.fixture
    def mock_chroma_collection(self):
        """Fixture to create a mock ChromaDB collection object."""
        collection = MagicMock()
        # Mock methods that will be called by execute_similarity_search
        collection.count = MagicMock(return_value=50)  # Default count
        collection.query = MagicMock()  # Will be configured per test
        return collection

    async def test_basic_successful_search_no_filters(self, mock_chroma_collection):
        """Test basic search returning k results without any filters."""
        mock_query_embedding = [0.1] * 1536  # Example embedding
        k_results = 5

        # Mock ChromaDB response
        mock_chroma_collection.query.return_value = {
            "ids": [["id1", "id2", "id3", "id4", "id5"]],
            "documents": [["doc1", "doc2", "doc3", "doc4", "doc5"]],
            "metadatas": [[{"skill": "python"}, {"skill": "java"}, {}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_chroma_collection.count.return_value = 10  # Ensure count is sufficient

        results = await execute_similarity_search(
            collection=mock_chroma_collection,
            query_embedding=mock_query_embedding,
            k=k_results,
            filters=None,
        )

        assert len(results) == k_results
        assert results[0]["id"] == "id1"
        assert results[0]["document"] == "doc1"
        assert results[0]["metadata"] == {"skill": "python"}
        assert results[0]["distance"] == 0.1
        mock_chroma_collection.query.assert_called_once()
        # Assert n_results in call_args based on no skills_query
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_results
        assert call_args[1]["where"] is None

    async def test_search_with_k_limiting(self, mock_chroma_collection):
        """Test that results are limited to k even if Chroma returns more."""
        mock_query_embedding = [0.2] * 1536
        k_results = 3

        mock_chroma_collection.query.return_value = {
            "ids": [["id1", "id2", "id3", "id4", "id5"]],  # Returns 5
            "documents": [["d1", "d2", "d3", "d4", "d5"]],
            "metadatas": [[{}, {}, {}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_chroma_collection.count.return_value = 5

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, None
        )

        assert len(results) == k_results
        assert results[0]["id"] == "id1"
        assert results[2]["id"] == "id3"

    async def test_search_with_metadata_filters_no_skills(self, mock_chroma_collection):
        """Test search with non-skill metadata filters."""
        mock_query_embedding = [0.3] * 1536
        k_results = 2
        filters = {"location": "Test Location", "experience_years": {"$gte": 3}}

        # Mock return value, assuming Chroma filtered internally
        mock_chroma_collection.query.return_value = {
            "ids": [["filtered_id1", "filtered_id2"]],
            "documents": [["doc_f1", "doc_f2"]],
            "metadatas": [
                [{"location": "Test Location"}, {"location": "Test Location"}]
            ],
            "distances": [[0.15, 0.25]],
        }
        mock_chroma_collection.count.return_value = 2

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == k_results
        mock_chroma_collection.query.assert_called_once_with(
            query_embeddings=[mock_query_embedding],
            n_results=k_results,  # No skills_query, so n_results_chroma = k
            where={"location": "Test Location", "experience_years": {"$gte": 3}},
            include=["metadatas", "documents", "distances"],
        )

    async def test_search_with_skills_post_filtering_match_all(
        self, mock_chroma_collection
    ):
        """Test skills post-filtering where candidates match all required skills."""
        mock_query_embedding = [0.4] * 1536
        k_final_results = 1
        # skills_query implies k*3 for n_results_chroma
        n_results_chroma_expected = k_final_results * 3
        filters = {"skills_query": ["python", "fastapi"]}

        mock_chroma_collection.query.return_value = {
            "ids": [["s_id1", "s_id2", "s_id3"]],
            "documents": [["s_d1", "s_d2", "s_d3"]],
            "metadatas": [
                [
                    {"skills": "Python, FastAPI, Docker"},  # Match
                    {"skills": "Java, Spring"},  # No match
                    {"skills": "Python, Docker"},
                ]  # No match (missing fastapi)
            ],
            "distances": [[0.1, 0.2, 0.3]],
        }
        mock_chroma_collection.count.return_value = 3

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "s_id1"
        assert results[0]["metadata"]["skills"] == "Python, FastAPI, Docker"

        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == n_results_chroma_expected
        assert (
            call_args[1]["where"] is None
        )  # Only skills_query, so no Chroma where clause

    async def test_skills_post_filtering_case_insensitivity(
        self, mock_chroma_collection
    ):
        """Test skills post-filtering is case insensitive."""
        mock_query_embedding = [0.5] * 1536
        k_results = 1
        filters = {"skills_query": ["PYTHON"]}  # Uppercase query skill

        mock_chroma_collection.query.return_value = {
            "ids": [["id_case"]],
            "documents": [["doc_case"]],
            "metadatas": [[{"skills": "python, react"}]],  # Lowercase candidate skill
            "distances": [[0.1]],
        }
        mock_chroma_collection.count.return_value = 1

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "id_case"

    async def test_skills_post_filtering_no_match(self, mock_chroma_collection):
        """Test skills post-filtering when no candidates match the skills criteria."""
        mock_query_embedding = [0.6] * 1536
        k_results = 2
        filters = {"skills_query": ["nonexistent_skill"]}

        mock_chroma_collection.query.return_value = {  # Chroma returns some candidates
            "ids": [["id_a", "id_b"]],
            "documents": [["doc_a", "doc_b"]],
            "metadatas": [[{"skills": "python"}], [{"skills": "java"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_chroma_collection.count.return_value = 2

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 0

    async def test_empty_chromadb_results(self, mock_chroma_collection):
        """Test behavior when ChromaDB query returns no results."""
        mock_query_embedding = [0.7] * 1536
        mock_chroma_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_chroma_collection.count.return_value = 0

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, 5, None
        )

        assert len(results) == 0

    async def test_invalid_query_embedding_raises_valueerror(
        self, mock_chroma_collection
    ):
        """Test that a ValueError is raised for invalid query_embedding."""
        with pytest.raises(ValueError, match="query_embedding cannot be empty"):
            await execute_similarity_search(mock_chroma_collection, None, 5, None)

        with pytest.raises(ValueError, match="query_embedding cannot be empty"):
            await execute_similarity_search(mock_chroma_collection, [], 5, None)

    async def test_chromadb_query_raises_exception(self, mock_chroma_collection):
        """Test that SearchOperationError is raised if collection.query fails."""
        mock_query_embedding = [0.8] * 1536
        mock_chroma_collection.query.side_effect = Exception("ChromaDB internal error")

        with pytest.raises(
            SearchOperationError, match="ChromaDB query failed: ChromaDB internal error"
        ):
            await execute_similarity_search(
                mock_chroma_collection, mock_query_embedding, 5, None
            )

    async def test_n_results_chroma_capping_logic(self, mock_chroma_collection):
        """Test n_results_chroma calculation considering collection count and k*3 for skills."""
        mock_query_embedding = [0.9] * 1536
        k_final = 5

        # Scenario 1: skills_query present, k*3 < collection.count
        filters_with_skills = {"skills_query": ["test"]}
        mock_chroma_collection.count.return_value = 50
        mock_chroma_collection.query.return_value = {"ids": [[]]}  # Minimal mock
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, filters_with_skills
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_final * 3  # 15

        # Scenario 2: skills_query present, k*3 > collection.count
        mock_chroma_collection.count.return_value = 7
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, filters_with_skills
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == 7  # Capped by collection_count

        # Scenario 3: No skills_query, n_results_chroma should be k
        mock_chroma_collection.count.return_value = 50
        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_final, None
        )
        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["n_results"] == k_final  # 5

    async def test_metadata_filters_passed_correctly(self, mock_chroma_collection):
        """Test that metadata filters (excluding skills_query) are passed to ChromaDB correctly."""
        mock_query_embedding = [0.1] * 1536
        k_results = 2
        filters = {
            "location": "Remote",
            "visa_status": "GC",
            "experience_years": {"$gte": 2},
            "skills_query": ["dont_pass_this_to_where"],
        }
        expected_where_clause = {
            "location": "Remote",
            "visa_status": "GC",
            "experience_years": {"$gte": 2},
        }

        mock_chroma_collection.query.return_value = {"ids": [[]]}  # Minimal mock

        await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        call_args = mock_chroma_collection.query.call_args
        assert call_args[1]["where"] == expected_where_clause
        # n_results should be k_results * 3 because skills_query is present
        assert call_args[1]["n_results"] == k_results * 3

    # Add more tests for edge cases in skills string parsing (e.g., empty strings, extra commas) if needed
    # Test what happens if metadata["skills"] is not a string or is missing
    async def test_skills_parsing_edge_cases_in_metadata(self, mock_chroma_collection):
        """Test how skills post-filtering handles malformed or missing skills in candidate metadata."""
        mock_query_embedding = [0.1] * 1536
        k_results = 1
        filters = {"skills_query": ["python"]}

        # Scenario 1: skills metadata is None
        # Scenario 2: skills metadata is not a string (e.g., a list already, though our code expects string)
        # Scenario 3: skills metadata is an empty string
        # Scenario 4: skills metadata has extra commas or whitespace

        test_cases_metadata = [
            {
                "id": "c1",
                "metadata": {"skills": None, "name": "Cand1"},
                "doc": "d1",
                "dist": 0.1,
            },  # Should not match "python"
            {
                "id": "c2",
                "metadata": {"skills": ["python", "java"], "name": "Cand2"},
                "doc": "d2",
                "dist": 0.2,
            },  # Code expects string, so this won't match
            {
                "id": "c3",
                "metadata": {"skills": "", "name": "Cand3"},
                "doc": "d3",
                "dist": 0.3,
            },  # Should not match
            {
                "id": "c4",
                "metadata": {"skills": "  python  ,,  java  ", "name": "Cand4"},
                "doc": "d4",
                "dist": 0.4,
            },  # Should match "python"
            {
                "id": "c5",
                "metadata": {"name": "Cand5_no_skills_key"},
                "doc": "d5",
                "dist": 0.5,
            },  # No skills key, should not match
        ]

        mock_chroma_collection.query.return_value = {
            "ids": [[tc["id"] for tc in test_cases_metadata]],
            "documents": [[tc["doc"] for tc in test_cases_metadata]],
            "metadatas": [[tc["metadata"] for tc in test_cases_metadata]],
            "distances": [[tc["dist"] for tc in test_cases_metadata]],
        }
        mock_chroma_collection.count.return_value = len(test_cases_metadata)

        results = await execute_similarity_search(
            mock_chroma_collection, mock_query_embedding, k_results, filters
        )

        assert len(results) == 1
        assert results[0]["id"] == "c4"  # Only c4 should match "python" after parsing
        assert (
            results[0]["metadata"]["skills"] == "  python  ,,  java  "
        )  # Original metadata is preserved


# Example of how to run these tests with pytest:
# Ensure pytest and pytest-asyncio are installed: pip install pytest pytest-asyncio
# Run from the root of your project or backend directory: pytest path/to/test_search_logic.py
