"""
Midjourney v3 API Client (UseAPI.net Provider)
===============================================

Refactored API client with proper error handling, logging, and retry logic.

Documentation References:
- post-midjourney-jobs-imagine.md: /imagine endpoint
- post-midjourney-jobs-blend.md: /blend with imageBlob uploads
- post-midjourney-jobs-describe.md: /describe with imageBlob
- post-midjourney-jobs-button.md: Button actions (U1-U4, V1-V4, etc.)
- get-midjourney-jobs-jobid.md: Job status polling
"""

import requests
import logging
import json
from typing import Dict, Any, List, Tuple, Optional
from .error_handler import (
    handle_api_response,
    UseAPIError,
    RateLimitError,
    retry_with_backoff,
    RetryConfig,
    sanitize_error_for_display
)

logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "https://api.useapi.net/v3/midjourney"
PROXY_CDN_URL = "https://api.useapi.net/v1/proxy/cdn-midjourney/"


class MidjourneyAPI:
    """
    Midjourney v3 API Client with comprehensive error handling.

    All methods reference specific UseAPI.net documentation files.
    """

    def __init__(self, api_token: str):
        """
        Initialize API client.

        Args:
            api_token: UseAPI.net API token (format: user:XXXX-XXXXX)
        """
        if not api_token or not api_token.strip():
            raise ValueError("API token cannot be empty")

        self.api_token = api_token.strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        logger.info("MidjourneyAPI client initialized")

    def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[int, Dict]:
        """
        Make API request with proper error handling.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (e.g., '/jobs/imagine')
            **kwargs: Additional requests parameters

        Returns:
            Tuple of (status_code, response_dict)

        Note: This method returns status_code for backward compatibility.
              New code should use the typed methods that raise exceptions.
        """
        url = f"{API_BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", self.headers.copy())

        # Log request (sanitized)
        logger.debug(f"{method} {endpoint}")

        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Raw response: {response.text[:500]}")
                data = {
                    "error": "Invalid JSON response from API",
                    "raw": response.text[:1000]
                }

            # Log response status
            if response.status_code >= 400:
                logger.warning(
                    f"{method} {endpoint} -> {response.status_code}: "
                    f"{data.get('error', 'Unknown error')}"
                )
            else:
                logger.debug(f"{method} {endpoint} -> {response.status_code}")

            return response.status_code, data

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {endpoint}")
            return 504, {"error": f"Request timeout: {str(e)}"}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {endpoint}")
            return 503, {"error": f"Connection error: {str(e)}"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {endpoint} - {sanitize_error_for_display(e)}")
            return 500, {"error": f"Request failed: {str(e)}"}

        except Exception as e:
            logger.exception(f"Unexpected error in API request: {endpoint}")
            return 500, {"error": f"Unexpected error: {str(e)}"}

    def _request_with_validation(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make API request and validate response (raises exceptions on error).

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional requests parameters

        Returns:
            Response data dictionary

        Raises:
            UseAPIError subclasses for error responses
        """
        status_code, data = self._request(method, endpoint, **kwargs)
        return handle_api_response(status_code, data)

    # -------------------------------------------------------------------------
    # Account Management
    # -------------------------------------------------------------------------

    def configure_channel(self, discord_token: str, max_jobs: int = 12,
                         max_image_jobs: int = 12, max_video_jobs: int = 3,
                         reply_url: str = None) -> Tuple[int, Dict]:
        """
        Configure Midjourney Discord channel.
        Ref: post-midjourney-accounts.md

        Args:
            discord_token: Discord user token
            max_jobs: Maximum concurrent jobs
            max_image_jobs: Maximum concurrent image jobs
            max_video_jobs: Maximum concurrent video jobs
            reply_url: Optional webhook URL for job updates

        Returns:
            Tuple of (status_code, response_dict)
        """
        payload = {
            "discord": discord_token,
            "maxJobs": max_jobs,
            "maxImageJobs": max_image_jobs,
            "maxVideoJobs": max_video_jobs
        }
        if reply_url:
            payload["replyUrl"] = reply_url

        logger.info(f"Configuring channel with maxJobs={max_jobs}")
        return self._request("POST", "/accounts", json=payload)

    def get_accounts(self) -> Tuple[int, Dict]:
        """
        List all configured channels.
        Ref: get-midjourney-accounts.md

        Returns:
            Tuple of (status_code, response_dict)
        """
        return self._request("GET", "/accounts")

    def get_account_channel(self, channel_id: str) -> Tuple[int, Dict]:
        """
        Get specific channel configuration.
        Ref: get-midjourney-accounts-channel.md
        """
        return self._request("GET", f"/accounts/{channel_id}")

    def delete_channel(self, channel_id: str) -> Tuple[int, Dict]:
        """
        Delete channel configuration.
        Ref: delete-midjourney-accounts-channel.md
        """
        logger.info(f"Deleting channel: {channel_id}")
        return self._request("DELETE", f"/accounts/{channel_id}")

    def reset_channel(self, channel_id: str) -> Tuple[int, Dict]:
        """
        Reset channel after moderation/CAPTCHA (596 error).
        Ref: post-midjourney-accounts-reset.md

        Use this after receiving a 596 error and resolving CAPTCHA in Discord.
        """
        logger.info(f"Resetting channel: {channel_id}")
        return self._request("POST", f"/accounts/reset/{channel_id}")

    # -------------------------------------------------------------------------
    # Job Creation
    # -------------------------------------------------------------------------

    def imagine(self, prompt: str, channel: str = None, stream: bool = False,
                reply_url: str = None, reply_ref: str = None) -> Tuple[int, Dict]:
        """
        Generate images from text prompt.
        Ref: post-midjourney-jobs-imagine.md

        Args:
            prompt: Text prompt with MJ parameters (--ar, --s, --v, etc.)
            channel: Optional specific channel ID
            stream: Enable streaming updates
            reply_url: Optional webhook URL for this job
            reply_ref: Optional reference ID for webhook

        Returns:
            Tuple of (status_code, response_dict)
            Response contains: jobid, status, verb, etc.
        """
        payload = {"prompt": prompt, "stream": stream}
        if channel:
            payload["channel"] = channel
        if reply_url:
            payload["replyUrl"] = reply_url
        if reply_ref:
            payload["replyRef"] = reply_ref

        logger.info(f"Imagine: {prompt[:100]}...")
        return self._request("POST", "/jobs/imagine", json=payload)

    def blend(self, files: List[Tuple[str, bytes, str]], dimensions: str = "Square",
              channel: str = None, stream: bool = False) -> Tuple[int, Dict]:
        """
        Blend 2-5 images using multipart/form-data.
        Ref: post-midjourney-jobs-blend.md

        CRITICAL: Uses imageBlob_1, imageBlob_2, ... imageBlob_5 parameter names.

        Args:
            files: List of (filename, file_bytes, content_type) tuples (2-5 images)
            dimensions: "Square", "Portrait", or "Landscape"
            channel: Optional specific channel ID
            stream: Enable streaming updates

        Returns:
            Tuple of (status_code, response_dict)
        """
        if len(files) < 2 or len(files) > 5:
            logger.error(f"Blend requires 2-5 images, got {len(files)}")
            return 400, {"error": "Blend requires 2-5 images"}

        # Validate file sizes (<10MB each)
        for i, (filename, file_bytes, _) in enumerate(files, 1):
            size_mb = len(file_bytes) / (1024 * 1024)
            if size_mb > 10:
                logger.error(f"Image {i} ({filename}) exceeds 10MB: {size_mb:.2f}MB")
                return 400, {"error": f"Image {i} exceeds 10MB limit ({size_mb:.2f}MB)"}

        # Build multipart form data
        form_data = {
            "blendDimensions": (None, dimensions),
            "stream": (None, str(stream).lower())
        }

        if channel:
            form_data["channel"] = (None, channel)

        # Add images as imageBlob_N
        for i, (filename, file_bytes, content_type) in enumerate(files, 1):
            form_data[f"imageBlob_{i}"] = (filename, file_bytes, content_type)

        logger.info(f"Blend: {len(files)} images, dimensions={dimensions}")

        headers = {"Authorization": f"Bearer {self.api_token}"}
        url = f"{API_BASE_URL}/jobs/blend"

        try:
            response = requests.post(url, headers=headers, files=form_data, timeout=30)
            data = response.json()

            if response.status_code >= 400:
                logger.warning(f"Blend failed: {response.status_code} - {data.get('error')}")

            return response.status_code, data

        except json.JSONDecodeError as e:
            logger.error(f"Blend response JSON parse error: {e}")
            return 500, {"error": "Invalid JSON response"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Blend request failed: {sanitize_error_for_display(e)}")
            return 500, {"error": str(e)}

    def describe(self, file_bytes: bytes, filename: str, content_type: str,
                 channel: str = None, stream: bool = False) -> Tuple[int, Dict]:
        """
        Generate prompts from image using multipart/form-data.
        Ref: post-midjourney-jobs-describe.md

        CRITICAL: Uses imageBlob parameter name (not imageUrl).

        Args:
            file_bytes: Image file bytes
            filename: Original filename
            content_type: MIME type (e.g., 'image/png')
            channel: Optional specific channel ID
            stream: Enable streaming updates

        Returns:
            Tuple of (status_code, response_dict)
            Response contains 4 prompt suggestions in response.embeds[0].description
        """
        # Validate file size
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > 10:
            logger.error(f"Describe image exceeds 10MB: {size_mb:.2f}MB")
            return 400, {"error": f"Image exceeds 10MB limit ({size_mb:.2f}MB)"}

        form_data = {
            "imageBlob": (filename, file_bytes, content_type),
            "stream": (None, str(stream).lower())
        }

        if channel:
            form_data["channel"] = (None, channel)

        logger.info(f"Describe: {filename}")

        headers = {"Authorization": f"Bearer {self.api_token}"}
        url = f"{API_BASE_URL}/jobs/describe"

        try:
            response = requests.post(url, headers=headers, files=form_data, timeout=30)
            data = response.json()

            if response.status_code >= 400:
                logger.warning(f"Describe failed: {response.status_code} - {data.get('error')}")

            return response.status_code, data

        except json.JSONDecodeError as e:
            logger.error(f"Describe response JSON parse error: {e}")
            return 500, {"error": "Invalid JSON response"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Describe request failed: {sanitize_error_for_display(e)}")
            return 500, {"error": str(e)}

    def button(self, job_id: str, button: str, mask: str = None,
               prompt: str = None, stream: bool = False) -> Tuple[int, Dict]:
        """
        Execute button action on completed job.
        Ref: post-midjourney-jobs-button.md

        Args:
            job_id: Completed job ID
            button: Button name (U1-U4, V1-V4, Vary, Zoom, Pan, etc.)
            mask: Required for 'Vary (Region)' - base64 encoded mask
            prompt: Optional for Custom Zoom and variations (when Remix mode active)
            stream: Enable streaming updates

        Returns:
            Tuple of (status_code, response_dict)
        """
        payload = {
            "jobId": job_id,
            "button": button,
            "stream": stream
        }
        if mask:
            payload["mask"] = mask
        if prompt:
            payload["prompt"] = prompt

        logger.info(f"Button action: {button} on job {job_id[:20]}...")
        return self._request("POST", "/jobs/button", json=payload)

    def seed(self, job_id: str, stream: bool = False) -> Tuple[int, Dict]:
        """
        Extract seed from completed imagine/blend job.
        Ref: post-midjourney-jobs-seed.md

        Returns seed value and four separate upscaled images.
        Execute-once pattern: subsequent requests return cached result.
        """
        payload = {"jobId": job_id, "stream": stream}
        logger.info(f"Extracting seed from job {job_id[:20]}...")
        return self._request("POST", "/jobs/seed", json=payload)

    # -------------------------------------------------------------------------
    # Settings & Modes
    # -------------------------------------------------------------------------

    def get_settings(self, channel: str = None, stream: bool = False) -> Tuple[int, Dict]:
        """
        Get current Midjourney settings.
        Ref: post-midjourney-jobs-settings.md

        Returns: version, stylize, raw, personalization, public, remix,
                 variability, turbo, fast, relax, suffix
        """
        payload = {"stream": stream}
        if channel:
            payload["channel"] = channel
        return self._request("POST", "/jobs/settings", json=payload)

    def set_fast_mode(self, channel: str = None) -> Tuple[int, Dict]:
        """Toggle fast mode. Ref: post-midjourney-jobs-fast.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        logger.info("Toggling fast mode")
        return self._request("POST", "/jobs/fast", json=payload)

    def set_relax_mode(self, channel: str = None) -> Tuple[int, Dict]:
        """Toggle relax mode. Ref: post-midjourney-jobs-relax.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        logger.info("Toggling relax mode")
        return self._request("POST", "/jobs/relax", json=payload)

    def set_turbo_mode(self, channel: str = None) -> Tuple[int, Dict]:
        """Toggle turbo mode. Ref: post-midjourney-jobs-turbo.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        logger.info("Toggling turbo mode")
        return self._request("POST", "/jobs/turbo", json=payload)

    def toggle_remix(self, channel: str = None) -> Tuple[int, Dict]:
        """Toggle remix mode. Ref: post-midjourney-jobs-remix.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        logger.info("Toggling remix mode")
        return self._request("POST", "/jobs/remix", json=payload)

    def toggle_variability(self, channel: str = None) -> Tuple[int, Dict]:
        """Toggle variability (high/low). Ref: post-midjourney-jobs-variability.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        logger.info("Toggling variability")
        return self._request("POST", "/jobs/variability", json=payload)

    def get_info(self, channel: str = None) -> Tuple[int, Dict]:
        """Get account info. Ref: post-midjourney-jobs-info.md"""
        payload = {}
        if channel:
            payload["channel"] = channel
        return self._request("POST", "/jobs/info", json=payload)

    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    def get_job(self, job_id: str) -> Tuple[int, Dict]:
        """
        Get job status and details.
        Ref: get-midjourney-jobs-jobid.md

        Status values: created, started, progress, completed, failed, moderated
        Response includes: buttons, imageUx, attachments, progress_percent, etc.
        """
        return self._request("GET", f"/jobs/{job_id}")

    def list_running_jobs(self) -> Tuple[int, Dict]:
        """
        List all currently running jobs.
        Ref: get-midjourney-jobs.md

        Returns jobs with status: created, started, progress
        """
        return self._request("GET", "/jobs")

    def cancel_job(self, job_id: str) -> Tuple[int, Dict]:
        """
        Cancel a running job.
        Ref: delete-midjourney-jobs-jobid.md
        """
        logger.info(f"Cancelling job: {job_id}")
        return self._request("DELETE", f"/jobs/{job_id}")
