"""
Secrets management utilities with validation and sanitization.
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_api_token(token: str) -> Tuple[bool, Optional[str]]:
    """
    Validate UseAPI.net token format.

    Args:
        token: API token to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token or not token.strip():
        return False, "API token cannot be empty"

    token = token.strip()

    # UseAPI.net tokens typically have format: user:XXXX-XXXXXXXXXXXXX
    # Example: user:2163-qzTNqFIQv2xsFVWWbdh5J
    if not re.match(r'^user:\d+-[a-zA-Z0-9]+$', token):
        return False, (
            "Invalid token format. UseAPI.net tokens should be in format: "
            "user:XXXX-XXXXXXXXXXXXX"
        )

    if len(token) < 20:
        return False, "Token appears too short to be valid"

    return True, None


def validate_discord_token(token: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Discord token format (basic check).

    Args:
        token: Discord token to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token:
        # Discord token is optional
        return True, None

    token = token.strip()

    # Discord tokens are base64-like strings, typically 50+ chars
    if len(token) < 50:
        return False, "Discord token appears too short"

    # Basic character check (alphanumeric + some special chars)
    if not re.match(r'^[a-zA-Z0-9._-]+$', token):
        return False, "Discord token contains invalid characters"

    return True, None


def load_secrets(secrets_path: Path) -> dict:
    """
    Load API credentials from secrets.toml with validation.

    Args:
        secrets_path: Path to secrets.toml file

    Returns:
        Dictionary with 'api_token' and 'discord_token' keys
    """
    secrets = {"api_token": "", "discord_token": ""}

    if not secrets_path.exists():
        logger.info(f"Secrets file not found: {secrets_path}")
        return secrets

    try:
        import toml
        loaded_secrets = toml.load(secrets_path)

        # Validate and load API token
        if "api_token" in loaded_secrets:
            token = loaded_secrets["api_token"]
            is_valid, error = validate_api_token(token)
            if is_valid:
                secrets["api_token"] = token
                logger.info("API token loaded successfully")
            else:
                logger.warning(f"Invalid API token in secrets: {error}")

        # Validate and load Discord token
        if "discord_token" in loaded_secrets:
            token = loaded_secrets["discord_token"]
            is_valid, error = validate_discord_token(token)
            if is_valid:
                secrets["discord_token"] = token
                logger.info("Discord token loaded successfully")
            else:
                logger.warning(f"Invalid Discord token in secrets: {error}")

        return secrets

    except Exception as e:
        logger.error(f"Failed to load secrets: {e}")
        return secrets


def save_secrets(secrets_path: Path, api_token: str, discord_token: str = "") -> Tuple[bool, Optional[str]]:
    """
    Save API credentials to secrets.toml with validation.

    Args:
        secrets_path: Path to secrets.toml file
        api_token: UseAPI.net API token
        discord_token: Discord token (optional)

    Returns:
        Tuple of (success, error_message)
    """
    # Validate tokens before saving
    is_valid, error = validate_api_token(api_token)
    if not is_valid:
        logger.error(f"Cannot save invalid API token: {error}")
        return False, error

    is_valid, error = validate_discord_token(discord_token)
    if not is_valid:
        logger.error(f"Cannot save invalid Discord token: {error}")
        return False, error

    try:
        # Ensure parent directory exists
        secrets_path.parent.mkdir(parents=True, exist_ok=True)

        # Write secrets file
        content = f'''# Midjourney v3 Studio Secrets
# KEEP THIS FILE SECURE - Do not commit to version control

api_token = "{api_token.strip()}"
discord_token = "{discord_token.strip()}"
'''

        # Write with restricted permissions on Unix-like systems
        secrets_path.write_text(content, encoding='utf-8')

        # Try to set restrictive permissions (ignore errors on Windows)
        try:
            import stat
            secrets_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except (OSError, AttributeError):
            pass  # Windows doesn't support chmod

        logger.info(f"Secrets saved successfully to {secrets_path}")
        return True, None

    except Exception as e:
        error_msg = f"Failed to save secrets: {e}"
        logger.error(error_msg)
        return False, error_msg


def sanitize_token_in_error(error_msg: str) -> str:
    """
    Remove tokens from error messages to prevent leakage.

    Args:
        error_msg: Error message that might contain tokens

    Returns:
        Sanitized error message
    """
    # Mask UseAPI tokens
    sanitized = re.sub(r'user:\d+-[a-zA-Z0-9]+', 'user:***MASKED***', error_msg)

    # Mask Bearer tokens
    sanitized = re.sub(r'Bearer\s+[a-zA-Z0-9._-]+', 'Bearer ***MASKED***', sanitized)

    # Mask Discord tokens (long alphanumeric strings)
    sanitized = re.sub(r'\b[a-zA-Z0-9._-]{50,}\b', '***MASKED***', sanitized)

    return sanitized
