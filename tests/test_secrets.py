"""
Unit tests for secrets management module.
"""

import pytest
import tempfile
from pathlib import Path
from midjourney_studio.utils.secrets import (
    validate_api_token,
    validate_discord_token,
    load_secrets,
    save_secrets,
    sanitize_token_in_error
)


class TestTokenValidation:
    """Test API and Discord token validation."""

    def test_valid_api_token(self):
        is_valid, error = validate_api_token("user:1234-abc123XYZ")
        assert is_valid is True
        assert error is None

    def test_empty_api_token(self):
        is_valid, error = validate_api_token("")
        assert is_valid is False
        assert "cannot be empty" in error

    def test_invalid_format_api_token(self):
        is_valid, error = validate_api_token("invalid-token")
        assert is_valid is False
        assert "Invalid token format" in error

    def test_too_short_api_token(self):
        is_valid, error = validate_api_token("user:123")
        assert is_valid is False
        assert "too short" in error

    def test_valid_discord_token(self):
        # Discord tokens are base64-like, 50+ chars
        token = "a" * 60
        is_valid, error = validate_discord_token(token)
        assert is_valid is True
        assert error is None

    def test_empty_discord_token(self):
        # Empty is valid (Discord token is optional)
        is_valid, error = validate_discord_token("")
        assert is_valid is True

    def test_too_short_discord_token(self):
        token = "short"
        is_valid, error = validate_discord_token(token)
        assert is_valid is False
        assert "too short" in error


class TestSecretsFileOperations:
    """Test loading and saving secrets."""

    def test_load_nonexistent_file(self):
        fake_path = Path("/nonexistent/path/secrets.toml")
        secrets = load_secrets(fake_path)
        assert secrets == {"api_token": "", "discord_token": ""}

    def test_save_and_load_secrets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            secrets_path = Path(tmpdir) / "secrets.toml"

            # Save secrets
            success, error = save_secrets(
                secrets_path,
                "user:1234-testtoken",
                "discordtoken123"
            )
            assert success is True
            assert error is None
            assert secrets_path.exists()

            # Load secrets
            loaded = load_secrets(secrets_path)
            assert loaded["api_token"] == "user:1234-testtoken"
            assert loaded["discord_token"] == "discordtoken123"

    def test_save_invalid_api_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            secrets_path = Path(tmpdir) / "secrets.toml"

            success, error = save_secrets(
                secrets_path,
                "invalid-token",
                ""
            )
            assert success is False
            assert "Invalid token format" in error
            assert not secrets_path.exists()

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            secrets_path = Path(tmpdir) / "subdir" / "secrets.toml"

            success, error = save_secrets(
                secrets_path,
                "user:1234-testtoken",
                ""
            )
            assert success is True
            assert secrets_path.exists()
            assert secrets_path.parent.exists()


class TestTokenSanitization:
    """Test sanitizing tokens in error messages."""

    def test_sanitize_useapi_token(self):
        error = "Connection failed with user:1234-secrettoken"
        sanitized = sanitize_token_in_error(error)
        assert "user:***MASKED***" in sanitized
        assert "secrettoken" not in sanitized

    def test_sanitize_bearer_token(self):
        error = "Authorization failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = sanitize_token_in_error(error)
        assert "Bearer ***MASKED***" in sanitized
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized

    def test_sanitize_multiple_tokens(self):
        error = "user:1234-abc failed Bearer xyz123 api_token=user:5678-def"
        sanitized = sanitize_token_in_error(error)
        assert "user:***MASKED***" in sanitized
        assert "Bearer ***MASKED***" in sanitized
        assert "abc" not in sanitized
        assert "xyz123" not in sanitized
        assert "def" not in sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
