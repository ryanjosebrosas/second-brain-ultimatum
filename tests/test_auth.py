"""Tests for OAuth authentication module."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from second_brain.auth import (
    CREDENTIALS_FILENAME,
    DEFAULT_CONFIG_DIR,
    OAUTH_TOKEN_PREFIX,
    configure_subscription_env,
    get_oauth_token,
    validate_oauth_token,
    verify_claude_cli,
)


class TestValidateOAuthToken:
    """Tests for validate_oauth_token()."""

    def test_valid_token(self):
        assert validate_oauth_token("sk-ant-oat01-valid-token-here") is True

    def test_invalid_prefix(self):
        assert validate_oauth_token("sk-ant-api03-wrong-prefix") is False

    def test_empty_token(self):
        assert validate_oauth_token("") is False

    def test_too_short(self):
        assert validate_oauth_token("sk-ant-oat01-") is False

    def test_none_like(self):
        assert validate_oauth_token("none") is False

    def test_api_key_not_oauth(self):
        assert validate_oauth_token("sk-ant-api03-real-api-key") is False


class TestGetOAuthToken:
    """Tests for get_oauth_token()."""

    def test_from_env_var(self, monkeypatch):
        """Token from CLAUDE_CODE_OAUTH_TOKEN env var takes priority."""
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-from-env")
        token = get_oauth_token()
        assert token == "sk-ant-oat01-from-env"

    def test_env_var_not_set(self, monkeypatch):
        """Returns None when env var not set and no credential store."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with patch("second_brain.auth.platform.system", return_value="Unknown"):
            token = get_oauth_token(config_dir=Path("/nonexistent"))
            assert token is None

    def test_from_credentials_file(self, credentials_file, monkeypatch):
        """Token read from .credentials.json on Windows."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with patch("second_brain.auth.platform.system", return_value="Windows"):
            token = get_oauth_token(config_dir=credentials_file)
            assert token == "sk-ant-oat01-from-credentials-file"

    def test_credentials_file_missing(self, tmp_path, monkeypatch):
        """Returns None when credentials file doesn't exist."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with patch("second_brain.auth.platform.system", return_value="Windows"):
            token = get_oauth_token(config_dir=tmp_path)
            assert token is None

    def test_credentials_file_malformed(self, tmp_path, monkeypatch):
        """Returns None when credentials file has bad JSON."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        creds_file = tmp_path / CREDENTIALS_FILENAME
        creds_file.write_text("not json")
        with patch("second_brain.auth.platform.system", return_value="Windows"):
            token = get_oauth_token(config_dir=tmp_path)
            assert token is None

    def test_credentials_file_missing_key(self, tmp_path, monkeypatch):
        """Returns None when credentials JSON lacks expected key."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        creds_file = tmp_path / CREDENTIALS_FILENAME
        creds_file.write_text(json.dumps({"other": "data"}))
        with patch("second_brain.auth.platform.system", return_value="Windows"):
            token = get_oauth_token(config_dir=tmp_path)
            assert token is None

    @patch("second_brain.auth.subprocess.run")
    def test_from_macos_keychain(self, mock_run, monkeypatch):
        """Token read from macOS Keychain via security command."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="sk-ant-oat01-from-keychain\n",
        )
        with patch("second_brain.auth.platform.system", return_value="Darwin"):
            token = get_oauth_token()
            assert token == "sk-ant-oat01-from-keychain"

    @patch("second_brain.auth.subprocess.run")
    def test_from_linux_secret_service(self, mock_run, monkeypatch):
        """Token read from Linux Secret Service via secret-tool."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="sk-ant-oat01-from-secret-service\n",
        )
        with patch("second_brain.auth.platform.system", return_value="Linux"):
            token = get_oauth_token()
            assert token == "sk-ant-oat01-from-secret-service"

    @patch("second_brain.auth.subprocess.run")
    def test_keychain_command_fails(self, mock_run, monkeypatch):
        """Returns None when keychain command fails."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        mock_run.side_effect = FileNotFoundError("security not found")
        with patch("second_brain.auth.platform.system", return_value="Darwin"):
            token = get_oauth_token()
            assert token is None


class TestVerifyClaudeCli:
    """Tests for verify_claude_cli()."""

    @patch("second_brain.auth.subprocess.run")
    def test_cli_found(self, mock_run):
        """Returns (True, version) when CLI is found."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="claude 1.2.3\n",
        )
        ok, info = verify_claude_cli()
        assert ok is True
        assert "1.2.3" in info

    @patch("second_brain.auth.subprocess.run")
    def test_cli_not_found(self, mock_run):
        """Returns (False, error) when CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("claude not found")
        ok, info = verify_claude_cli()
        assert ok is False
        assert "not found" in info.lower()

    @patch("second_brain.auth.subprocess.run")
    def test_cli_timeout(self, mock_run):
        """Returns (False, error) when CLI command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 10)
        ok, info = verify_claude_cli()
        assert ok is False


class TestConfigureSubscriptionEnv:
    """Tests for configure_subscription_env()."""

    def test_sets_env_var(self, monkeypatch):
        """Sets CLAUDE_CODE_OAUTH_TOKEN env var."""
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        configure_subscription_env("sk-ant-oat01-test")
        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "sk-ant-oat01-test"

    def test_overwrites_existing(self, monkeypatch):
        """Overwrites existing CLAUDE_CODE_OAUTH_TOKEN."""
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "old-token")
        configure_subscription_env("sk-ant-oat01-new")
        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "sk-ant-oat01-new"
