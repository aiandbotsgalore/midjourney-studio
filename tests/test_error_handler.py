"""
Unit tests for error handling module.
"""

import pytest
from midjourney_studio.api.error_handler import (
    UseAPIError,
    AuthenticationError,
    PaymentRequiredError,
    RateLimitError,
    ModerationError,
    handle_api_response,
    sanitize_error_for_display,
    RetryConfig,
    retry_with_backoff
)


class TestErrorClasses:
    """Test custom exception classes."""

    def test_authentication_error(self):
        error = AuthenticationError(401, "Invalid token", {"error": "auth failed"})
        assert error.status_code == 401
        assert "Authentication Failed" in error.get_user_message()
        assert "Settings tab" in error.get_user_message()

    def test_payment_required_error(self):
        error = PaymentRequiredError(402, "Payment required", {"error": "no credits"})
        assert error.status_code == 402
        assert "Payment Required" in error.get_user_message()
        assert "useapi.net/dashboard" in error.get_user_message()

    def test_rate_limit_error(self):
        error = RateLimitError(429, "Too many requests", {"retry_after": 10})
        assert error.status_code == 429
        assert error.retry_after == 10
        assert "Rate Limit" in error.get_user_message()

    def test_moderation_error(self):
        error = ModerationError(596, "Content blocked", {"channel": "123456"})
        assert error.status_code == 596
        assert "CAPTCHA" in error.get_user_message()
        assert "Reset Channel" in error.get_user_message()


class TestHandleAPIResponse:
    """Test API response handler."""

    def test_success_200(self):
        response = {"jobid": "123", "status": "created"}
        result = handle_api_response(200, response)
        assert result == response

    def test_success_201(self):
        response = {"jobid": "456"}
        result = handle_api_response(201, response)
        assert result == response

    def test_auth_error_401(self):
        with pytest.raises(AuthenticationError) as exc_info:
            handle_api_response(401, {"error": "Invalid token"})
        assert exc_info.value.status_code == 401

    def test_payment_error_402(self):
        with pytest.raises(PaymentRequiredError) as exc_info:
            handle_api_response(402, {"error": "Payment required"})
        assert exc_info.value.status_code == 402

    def test_rate_limit_429(self):
        with pytest.raises(RateLimitError) as exc_info:
            handle_api_response(429, {"error": "Too many requests", "retry_after": 5})
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 5

    def test_moderation_596(self):
        with pytest.raises(ModerationError) as exc_info:
            handle_api_response(596, {"error": "Content moderated"})
        assert exc_info.value.status_code == 596

    def test_generic_error(self):
        with pytest.raises(UseAPIError) as exc_info:
            handle_api_response(500, {"error": "Internal server error"})
        assert exc_info.value.status_code == 500


class TestTokenSanitization:
    """Test token sanitization in error messages."""

    def test_sanitize_useapi_token(self):
        error_msg = "Failed to connect with token user:1234-abcdefgh"
        sanitized = sanitize_error_for_display(error_msg)
        assert "user:***MASKED***" in sanitized
        assert "1234-abcdefgh" not in sanitized

    def test_sanitize_bearer_token(self):
        error_msg = "Authorization: Bearer abc123xyz"
        sanitized = sanitize_error_for_display(error_msg)
        assert "Bearer ***MASKED***" in sanitized
        assert "abc123xyz" not in sanitized

    def test_sanitize_api_token_assignment(self):
        error_msg = 'api_token="user:9999-testtoken"'
        sanitized = sanitize_error_for_display(error_msg)
        assert "user:***MASKED***" in sanitized
        assert "testtoken" not in sanitized


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0

    def test_exponential_backoff(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0)
        assert config.get_delay(0) == 1.0  # 1 * 2^0
        assert config.get_delay(1) == 2.0  # 1 * 2^1
        assert config.get_delay(2) == 4.0  # 1 * 2^2
        assert config.get_delay(3) == 8.0  # 1 * 2^3

    def test_max_delay_cap(self):
        config = RetryConfig(base_delay=10.0, max_delay=20.0, exponential_base=2.0)
        # Would be 10 * 2^3 = 80, but capped at 20
        assert config.get_delay(3) == 20.0


class TestRetryLogic:
    """Test retry with backoff."""

    def test_success_on_first_try(self):
        call_count = [0]

        def successful_func():
            call_count[0] += 1
            return "success"

        result = retry_with_backoff(successful_func, RetryConfig(max_attempts=3))
        assert result == "success"
        assert call_count[0] == 1

    def test_success_on_second_try(self):
        call_count = [0]

        def func_succeeds_on_second():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError(429, "Rate limit", {}, retry_after=0.01)
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = retry_with_backoff(func_succeeds_on_second, config)
        assert result == "success"
        assert call_count[0] == 2

    def test_all_retries_exhausted(self):
        call_count = [0]

        def always_fails():
            call_count[0] += 1
            raise RateLimitError(429, "Rate limit", {}, retry_after=0.01)

        config = RetryConfig(max_attempts=3, base_delay=0.01)

        with pytest.raises(RateLimitError):
            retry_with_backoff(always_fails, config)

        assert call_count[0] == 3  # All 3 attempts made


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
