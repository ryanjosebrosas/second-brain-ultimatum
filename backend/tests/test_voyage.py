"""Tests for VoyageService and rerank_memories utility."""

import sys

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from second_brain.services.voyage import VoyageService


@pytest.fixture
def voyage_config(tmp_path):
    from second_brain.config import BrainConfig
    return BrainConfig(
        voyage_api_key="test-voyage-key",
        voyage_embedding_model="voyage-4-lite",
        voyage_rerank_model="rerank-2-lite",
        voyage_rerank_top_k=5,
        embedding_dimensions=1024,
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
        _env_file=None,
    )


@pytest.fixture
def mock_voyageai():
    """Mock the voyageai module in sys.modules for lazy import."""
    mock_mod = MagicMock()
    with patch.dict(sys.modules, {"voyageai": mock_mod}):
        yield mock_mod


class TestVoyageServiceEmbed:
    async def test_embed_single(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.multimodal_embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        result = await service.embed("test text")

        assert len(result) == 1024
        mock_client.multimodal_embed.assert_called_once_with(
            [["test text"]],
            model="voyage-4-lite",
            input_type="document",
        )

    async def test_embed_query(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.2] * 1024]
        mock_client.multimodal_embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        result = await service.embed_query("search query")

        assert len(result) == 1024
        mock_client.multimodal_embed.assert_called_once_with(
            [["search query"]],
            model="voyage-4-lite",
            input_type="query",
        )

    async def test_embed_batch(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]
        mock_client.multimodal_embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        result = await service.embed_batch(["text1", "text2"])

        assert len(result) == 2
        assert len(result[0]) == 1024

    async def test_embed_batch_input_type(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.multimodal_embed.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        await service.embed_batch(["text1"], input_type="query")

        mock_client.multimodal_embed.assert_called_once_with(
            [["text1"]],
            model="voyage-4-lite",
            input_type="query",
        )

    async def test_embed_no_api_key(self, tmp_path):
        from second_brain.config import BrainConfig
        config = BrainConfig(
            voyage_api_key=None,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        service = VoyageService(config)
        with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
            await service.embed("test")

    async def test_embed_batch_respects_128_limit(self, mock_voyageai, voyage_config):
        """Verify batch chunking when batch_size > 128."""
        voyage_config.embedding_batch_size = 200  # exceeds 128 limit
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024] * 128
        mock_result2 = MagicMock()
        mock_result2.embeddings = [[0.1] * 1024] * 2
        mock_client.multimodal_embed.side_effect = [mock_result, mock_result2]
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        texts = ["text"] * 130
        result = await service.embed_batch(texts)

        assert len(result) == 130
        assert mock_client.multimodal_embed.call_count == 2


class TestVoyageServiceRerank:
    async def test_rerank(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_rr1 = MagicMock(index=2, document="doc C", relevance_score=0.95)
        mock_rr2 = MagicMock(index=0, document="doc A", relevance_score=0.80)
        mock_result = MagicMock()
        mock_result.results = [mock_rr1, mock_rr2]
        mock_client.rerank.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        result = await service.rerank("query", ["doc A", "doc B", "doc C"], top_k=2)

        assert len(result) == 2
        assert result[0]["index"] == 2
        assert result[0]["relevance_score"] == 0.95
        assert result[1]["index"] == 0
        mock_client.rerank.assert_called_once_with(
            "query", ["doc A", "doc B", "doc C"],
            model="rerank-2-lite", top_k=2,
        )

    async def test_rerank_uses_config_top_k(self, mock_voyageai, voyage_config):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.results = []
        mock_client.rerank.return_value = mock_result
        mock_voyageai.Client.return_value = mock_client

        service = VoyageService(voyage_config)
        await service.rerank("query", ["doc"])

        mock_client.rerank.assert_called_once_with(
            "query", ["doc"],
            model="rerank-2-lite", top_k=5,  # config default
        )

    async def test_rerank_empty_documents(self, voyage_config):
        service = VoyageService(voyage_config)
        result = await service.rerank("query", [])
        assert result == []

    async def test_close(self, voyage_config):
        service = VoyageService(voyage_config)
        await service.close()
        assert service._client is None


class TestRerankMemories:
    async def test_rerank_with_voyage(self, mock_deps):
        from second_brain.agents.utils import rerank_memories
        memories = [
            {"memory": "less relevant", "score": 0.7},
            {"memory": "most relevant", "score": 0.8},
        ]
        mock_deps.voyage_service.rerank = AsyncMock(return_value=[
            {"index": 1, "document": "most relevant", "relevance_score": 0.95},
            {"index": 0, "document": "less relevant", "relevance_score": 0.60},
        ])
        result = await rerank_memories(mock_deps, "test query", memories)
        assert result[0]["memory"] == "most relevant"
        assert result[0]["rerank_score"] == 0.95
        assert result[1]["memory"] == "less relevant"

    async def test_rerank_without_voyage(self, mock_deps):
        from second_brain.agents.utils import rerank_memories
        mock_deps.voyage_service = None
        memories = [{"memory": "a", "score": 0.9}]
        result = await rerank_memories(mock_deps, "query", memories)
        assert result == memories

    async def test_rerank_graceful_failure(self, mock_deps):
        from second_brain.agents.utils import rerank_memories
        mock_deps.voyage_service.rerank = AsyncMock(side_effect=Exception("API error"))
        memories = [{"memory": "a", "score": 0.9}]
        result = await rerank_memories(mock_deps, "query", memories)
        assert result == memories

    async def test_rerank_empty_memories(self, mock_deps):
        from second_brain.agents.utils import rerank_memories
        result = await rerank_memories(mock_deps, "query", [])
        assert result == []

    async def test_rerank_preserves_original_dict_structure(self, mock_deps):
        from second_brain.agents.utils import rerank_memories
        memories = [
            {"memory": "content A", "score": 0.9, "id": "mem-1", "extra": "data"},
            {"memory": "content B", "score": 0.7, "id": "mem-2"},
        ]
        mock_deps.voyage_service.rerank = AsyncMock(return_value=[
            {"index": 1, "document": "content B", "relevance_score": 0.99},
            {"index": 0, "document": "content A", "relevance_score": 0.50},
        ])
        result = await rerank_memories(mock_deps, "query", memories)
        assert result[0]["id"] == "mem-2"
        assert result[0]["rerank_score"] == 0.99
        assert result[1]["extra"] == "data"

    async def test_rerank_with_result_key(self, mock_deps):
        """Test memories using 'result' key instead of 'memory'."""
        from second_brain.agents.utils import rerank_memories
        memories = [
            {"result": "content A", "score": 0.9},
        ]
        mock_deps.voyage_service.rerank = AsyncMock(return_value=[
            {"index": 0, "document": "content A", "relevance_score": 0.95},
        ])
        result = await rerank_memories(mock_deps, "query", memories)
        assert len(result) == 1
        assert result[0]["result"] == "content A"


class TestEmbeddingServiceDelegation:
    @patch("second_brain.services.voyage.VoyageService")
    async def test_uses_voyage_when_key_set(self, mock_vs_cls, tmp_path):
        from second_brain.config import BrainConfig
        from second_brain.services.embeddings import EmbeddingService

        config = BrainConfig(
            voyage_api_key="test-key",
            openai_api_key="test-openai",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        mock_voyage = MagicMock()
        mock_voyage.embed = AsyncMock(return_value=[0.1] * 1024)
        mock_vs_cls.return_value = mock_voyage

        service = EmbeddingService(config)
        result = await service.embed("test")

        assert result == [0.1] * 1024
        mock_voyage.embed.assert_called_once_with("test")

    @patch("second_brain.services.voyage.VoyageService")
    async def test_embed_query_delegates_to_voyage(self, mock_vs_cls, tmp_path):
        from second_brain.config import BrainConfig
        from second_brain.services.embeddings import EmbeddingService

        config = BrainConfig(
            voyage_api_key="test-key",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        mock_voyage = MagicMock()
        mock_voyage.embed_query = AsyncMock(return_value=[0.2] * 1024)
        mock_vs_cls.return_value = mock_voyage

        service = EmbeddingService(config)
        result = await service.embed_query("search")

        assert result == [0.2] * 1024
        mock_voyage.embed_query.assert_called_once_with("search")

    async def test_requires_some_api_key(self, tmp_path):
        from second_brain.config import BrainConfig
        from second_brain.services.embeddings import EmbeddingService

        config = BrainConfig(
            voyage_api_key=None,
            openai_api_key=None,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        with pytest.raises(ValueError, match="VOYAGE_API_KEY or OPENAI_API_KEY"):
            EmbeddingService(config)

    @patch("second_brain.services.voyage.VoyageService")
    async def test_close_delegates_to_voyage(self, mock_vs_cls, tmp_path):
        from second_brain.config import BrainConfig
        from second_brain.services.embeddings import EmbeddingService

        config = BrainConfig(
            voyage_api_key="test-key",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        mock_voyage = MagicMock()
        mock_voyage.close = AsyncMock()
        mock_vs_cls.return_value = mock_voyage

        service = EmbeddingService(config)
        await service.close()
        mock_voyage.close.assert_called_once()


class TestVoyageConfig:
    def test_default_voyage_fields(self, tmp_path):
        from second_brain.config import BrainConfig
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.voyage_api_key is None
        assert config.voyage_embedding_model == "voyage-multimodal-3.5"
        assert config.voyage_rerank_model == "rerank-2-lite"
        assert config.voyage_rerank_top_k == 10
        assert config.embedding_dimensions == 1024
        assert config.embedding_model == "voyage-multimodal-3.5"

    def test_voyage_rerank_top_k_bounds(self, tmp_path):
        from second_brain.config import BrainConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrainConfig(
                voyage_rerank_top_k=0,
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )
        with pytest.raises(ValidationError):
            BrainConfig(
                voyage_rerank_top_k=101,
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )


class TestVoyageMultimodal:
    """Tests for VoyageService multimodal embedding methods."""

    async def test_embed_uses_multimodal_api(self, voyage_config):
        """Verify embed() now calls client.multimodal_embed instead of client.embed."""
        service = VoyageService(voyage_config)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.multimodal_embed = MagicMock(return_value=mock_result)
        service._client = mock_client

        result = await service.embed("test text")

        mock_client.multimodal_embed.assert_called_once()
        call_args = mock_client.multimodal_embed.call_args
        assert call_args[0][0] == [["test text"]]
        assert call_args[1]["model"] == voyage_config.voyage_embedding_model
        assert call_args[1]["input_type"] == "document"
        assert result == [0.1] * 1024

    async def test_embed_query_uses_query_input_type(self, voyage_config):
        """Verify embed_query() passes input_type='query'."""
        service = VoyageService(voyage_config)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.2] * 1024]
        mock_client.multimodal_embed = MagicMock(return_value=mock_result)
        service._client = mock_client

        await service.embed_query("search query")

        call_args = mock_client.multimodal_embed.call_args
        assert call_args[1]["input_type"] == "query"

    async def test_multimodal_embed_with_mixed_input(self, voyage_config):
        """Test multimodal_embed() with mixed text and image-like inputs."""
        service = VoyageService(voyage_config)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.3] * 1024]
        mock_client.multimodal_embed = MagicMock(return_value=mock_result)
        service._client = mock_client

        inputs = [["description", "fake_image_object"]]
        result = await service.multimodal_embed(inputs, input_type="document")

        mock_client.multimodal_embed.assert_called_once_with(
            inputs, model=voyage_config.voyage_embedding_model, input_type="document"
        )
        assert result == [[0.3] * 1024]

    async def test_embed_batch_uses_multimodal_api(self, voyage_config):
        """Verify embed_batch() calls multimodal_embed for batches."""
        service = VoyageService(voyage_config)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]
        mock_client.multimodal_embed = MagicMock(return_value=mock_result)
        service._client = mock_client

        result = await service.embed_batch(["text1", "text2"])

        call_args = mock_client.multimodal_embed.call_args
        assert call_args[0][0] == [["text1"], ["text2"]]
        assert len(result) == 2

    async def test_multimodal_embed_no_output_dimension(self, voyage_config):
        """Verify multimodal_embed does NOT pass output_dimension parameter."""
        service = VoyageService(voyage_config)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.multimodal_embed = MagicMock(return_value=mock_result)
        service._client = mock_client

        await service.embed("test")

        call_kwargs = mock_client.multimodal_embed.call_args[1]
        assert "output_dimension" not in call_kwargs
