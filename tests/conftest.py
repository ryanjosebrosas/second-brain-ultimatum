"""Shared test fixtures for Second Brain tests."""

import pytest
from unittest.mock import MagicMock

from second_brain.config import BrainConfig


@pytest.fixture
def mock_config(tmp_path):
    """BrainConfig with test values and a temp data path."""
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
    )
