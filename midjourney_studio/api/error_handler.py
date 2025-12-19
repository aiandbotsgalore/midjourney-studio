"""
UseAPI.net Error Handling Module
=================================

Handles all useapi.net specific error codes with recovery strategies:
- 401: Invalid API token
- 402: Payment required
- 429: Rate limit exceeded (with exponential backoff)
- 596: Content moderation/CAPTCHA
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class UseAPIError(Exception):
    """Base exception for UseAPI.net errors."""

    def __init__(self, status_code: int, message: str, response: Dict[str, Any]):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"[{status_code}] {message}")

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.message


class AuthenticationError(UseAPIError):
    """401 - Invalid API token."""

    def get_user_message(self) -> str:
        return (
            "🔐 **Authentication Failed**\n\n"
            "Your UseAPI.net token is invalid or expired.\n\n"
            "**Action Required:**\n"
            "1. Go to Settings tab\n"
            "2. Verify your API token is correct\n"
            "3. Get a new token at https://useapi.net if needed"
        )


class PaymentRequiredError(UseAPIError):
    """402 - Payment required."""

    def get_user_message(self) -> str:
        return (
            "💳 **Payment Required**\n\n"
            "Your UseAPI.net account requires payment or has insufficient credits.\n\n"
            "**Action Required:**\n"
            "1. Visit https://useapi.net/dashboard\n"
            "2. Add credits or upgrade your plan\n"
            "3. Ensure your Midjourney subscription is active"
        )


class RateLimitError(UseAPIError):
    """429 - Rate limit exceeded."""

    def __init__(self, status_code: int, message: str, response: Dict[str, Any],
                 retry_after: Optional[int] = None):
        super().__init__(status_code, message, response)
        self.retry_after = retry_after or response.get('retry_after', 5)

    def get_user_message(self) -> str:
        return (
            f"⏱️ **Rate Limit Exceeded**\n\n"
            f"Too many requests. The system will automatically retry in {self.retry_after} seconds.\n\n"
            f"**Tip:** Consider reducing concurrent jobs or adding delays between submissions."
        )


class ModerationError(UseAPIError):
    """596 - Content moderated or CAPTCHA required."""

    def get_user_message(self) -> str:
        channel_id = self.response.get('channel', 'your Discord channel')
        return (
            "🚫 **Content Moderation or CAPTCHA Required**\n\n"
            "Midjourney has flagged your content or requires CAPTCHA verification.\n\n"
            "**Action Required:**\n"
            "1. Open Discord and check your Midjourney DM channel\n"
            "2. Complete any CAPTCHA challenges\n"
            "3. Review Midjourney's content policy if content was blocked\n"
            "4. Use the 'Reset Channel' button in Settings tab\n\n"
            f"**Channel ID:** `{channel_id}`"
        )


# ============================================================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# ============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 2.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using exponential backoff."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


def retry_with_backoff(
    func: Callable,
    retry_config: RetryConfig = RetryConfig(),
    retry_on: tuple = (RateLimitError,)
) -> Any:
    """
    Execute function with exponential backoff retry logic.

    Args:
        func: Function to execute
        retry_config: Retry configuration
        retry_on: Tuple of exception types to retry on

    Returns:
        Result of function execution

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(retry_config.max_attempts):
        try:
            return func()
        except retry_on as e:
            last_exception = e

            if attempt < retry_config.max_attempts - 1:
                delay = retry_config.get_delay(attempt)

                if isinstance(e, RateLimitError):
                    # Use API-provided retry_after if available
                    delay = max(delay, e.retry_after)

                logger.warning(
                    f"Attempt {attempt + 1}/{retry_config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {retry_config.max_attempts} attempts exhausted")

    raise last_exception


# ============================================================================
# ERROR RESPONSE HANDLER
# ============================================================================

def handle_api_response(status_code: int, response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Centralized error handling for UseAPI.net responses.

    Args:
        status_code: HTTP status code
        response: Response JSON data

    Returns:
        Response data if successful

    Raises:
        Appropriate UseAPIError subclass for error codes
    """
    # Success codes
    if status_code in [200, 201]:
        return response

    # Extract error message
    error_msg = response.get('error', response.get('message', 'Unknown error'))

    # Map status codes to exceptions
    if status_code == 401:
        raise AuthenticationError(
            status_code=status_code,
            message=f"Invalid API token: {error_msg}",
            response=response
        )

    elif status_code == 402:
        raise PaymentRequiredError(
            status_code=status_code,
            message=f"Payment required: {error_msg}",
            response=response
        )

    elif status_code == 429:
        retry_after = response.get('retry_after', 5)
        raise RateLimitError(
            status_code=status_code,
            message=f"Rate limit exceeded: {error_msg}",
            response=response,
            retry_after=retry_after
        )

    elif status_code == 596:
        raise ModerationError(
            status_code=status_code,
            message=f"Content moderated or CAPTCHA required: {error_msg}",
            response=response
        )

    # Generic error for other codes
    else:
        raise UseAPIError(
            status_code=status_code,
            message=error_msg,
            response=response
        )


def sanitize_error_for_display(error: Exception, hide_token: bool = True) -> str:
    """
    Sanitize error messages to prevent token leakage.

    Args:
        error: Exception to sanitize
        hide_token: Whether to mask API tokens in error messages

    Returns:
        Safe error message for display
    """
    error_str = str(error)

    if hide_token:
        # Mask anything that looks like a token (user:XXXX-XXXXX pattern or Bearer tokens)
        import re
        error_str = re.sub(r'user:\d+-[a-zA-Z0-9]+', 'user:***MASKED***', error_str)
        error_str = re.sub(r'Bearer\s+[a-zA-Z0-9_-]+', 'Bearer ***MASKED***', error_str)
        error_str = re.sub(r'api_token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+', 'api_token=***MASKED***', error_str)

    return error_str
