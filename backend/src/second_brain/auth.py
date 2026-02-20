"""OAuth authentication for Claude subscription billing.

Reads OAuth tokens from OS credential stores and configures
the environment for claude-agent-sdk to use subscription auth.
"""

import json
import logging
import os
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
OAUTH_TOKEN_PREFIX = "sk-ant-oat01-"
CREDENTIALS_FILENAME = ".credentials.json"
KEYCHAIN_SERVICE = "Claude Code-credentials"
DEFAULT_CONFIG_DIR = Path.home() / ".claude"


def get_oauth_token(config_dir: Path | None = None) -> str | None:
    """Get OAuth token from environment or OS credential store.

    Priority: env var > credential store (Windows JSON / macOS Keychain / Linux Secret Service).

    Args:
        config_dir: Override config directory. Defaults to ~/.claude.

    Returns:
        OAuth token string or None if not found.
    """
    # 1. Check environment variable (highest priority)
    logger.debug("Checking CLAUDE_CODE_OAUTH_TOKEN env var")
    env_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if env_token:
        logger.info("Found OAuth token from environment variable")
        return env_token.strip()

    # 2. Try credential store based on platform
    logger.debug("Checking credential store for OAuth token")
    system = platform.system()
    config_path = config_dir or DEFAULT_CONFIG_DIR

    if system == "Windows":
        return _read_windows_credentials(config_path)
    elif system == "Darwin":
        return _read_macos_keychain()
    elif system == "Linux":
        return _read_linux_secret_service(config_path)
    else:
        logger.debug("Unsupported platform for credential store: %s", system)
        return None


def _read_windows_credentials(config_dir: Path) -> str | None:
    """Read OAuth token from Windows .credentials.json file."""
    creds_path = config_dir / CREDENTIALS_FILENAME
    logger.debug("Looking for credentials at: %s", creds_path)

    if not creds_path.exists():
        logger.debug("Credentials file not found: %s", creds_path)
        return None

    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
        token = data.get("claudeAiOauth", {}).get("accessToken")
        if token:
            logger.info("Found OAuth token from Windows credential store")
            return token.strip()
        logger.debug("No OAuth token in credentials file")
        return None
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("Failed to read credentials file: %s", e)
        return None


def _read_macos_keychain() -> str | None:
    """Read OAuth token from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Found OAuth token from macOS Keychain")
            return result.stdout.strip()
        logger.debug("No OAuth token in macOS Keychain")
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug("macOS Keychain access failed: %s", e)
        return None


def _read_linux_secret_service(config_dir: Path = DEFAULT_CONFIG_DIR) -> str | None:
    """Read OAuth token from Linux Secret Service via secret-tool.

    Falls back to reading .credentials.json (same as Windows)
    when secret-tool is unavailable (e.g., WSL environments).

    Args:
        config_dir: Config directory containing .credentials.json fallback.
    """
    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", KEYCHAIN_SERVICE],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Found OAuth token from Linux Secret Service")
            return result.stdout.strip()
        logger.debug("No OAuth token in Linux Secret Service")
    except FileNotFoundError:
        logger.debug("secret-tool not found; likely WSL or headless Linux")
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("Linux Secret Service failed unexpectedly: %s", e)

    # Fallback: read .credentials.json (covers WSL and headless Linux)
    logger.warning("Falling back to .credentials.json for OAuth token")
    return _read_windows_credentials(config_dir)


def validate_oauth_token(token: str) -> bool:
    """Validate OAuth token format.

    Checks prefix (sk-ant-oat01-) and minimum length.
    Does NOT check expiry (requires API call).

    Args:
        token: The OAuth token string to validate.

    Returns:
        True if token format is valid.
    """
    logger.debug("Validating OAuth token format")
    if not token or len(token) < 20:
        logger.warning("OAuth token too short or empty")
        return False
    if not token.startswith(OAUTH_TOKEN_PREFIX):
        logger.warning(
            "Invalid OAuth token format: expected prefix %s",
            OAUTH_TOKEN_PREFIX,
        )
        return False
    return True


def verify_claude_cli() -> tuple[bool, str]:
    """Verify that the claude CLI is installed and accessible.

    On Windows, tries 'claude', 'claude.cmd', and 'claude.exe'.

    Returns:
        Tuple of (success: bool, info: str).
        If success, info is the version string.
        If failure, info is the error message.
    """
    logger.debug("Checking for claude CLI")
    commands = ["claude"]
    if platform.system() == "Windows":
        commands.extend(["claude.cmd", "claude.exe"])

    for cmd in commands:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("Found claude CLI: %s", version)
                return True, version
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            logger.warning("claude CLI timed out")
            return False, "CLI command timed out"
        except OSError as e:
            logger.debug("CLI check failed for %s: %s", cmd, e)
            continue

    error = "claude CLI not found. Install via: npm install -g @anthropic-ai/claude-code"
    logger.warning(error)
    return False, error


def configure_subscription_env(token: str) -> None:
    """Set CLAUDE_CODE_OAUTH_TOKEN env var for SDK subprocess inheritance.

    The claude-agent-sdk spawns a CLI subprocess that reads this env var
    for OAuth authentication. Call this before creating the SDK client.

    Args:
        token: The OAuth token to set.
    """
    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token
    logger.info("Configured CLAUDE_CODE_OAUTH_TOKEN environment variable")
