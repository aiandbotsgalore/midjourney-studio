"""
Job status polling utilities with blocking and non-blocking implementations.

CRITICAL FIX: Replaces the blocking poll_job_status() that freezes Streamlit UI.
"""

import time
import logging
import threading
from typing import Dict, Optional, Callable, Any
from queue import Queue, Empty
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx
except ImportError:
    add_script_run_ctx = lambda x: x

logger = logging.getLogger(__name__)

# Job polling configuration
POLL_INTERVAL = 3  # seconds between status checks
DEFAULT_TIMEOUT = 600  # 10 minutes max polling time


def poll_job_status(api, job_id: str, timeout: int = DEFAULT_TIMEOUT) -> Dict:
    """
    BLOCKING job status polling (legacy compatibility).

    WARNING: This blocks the entire Streamlit app during polling!
    Use poll_job_status_async() for non-blocking polling instead.

    Args:
        api: MidjourneyAPI instance
        job_id: Job ID to poll
        timeout: Maximum polling time in seconds

    Returns:
        Final job data when completed/failed/moderated
    """
    logger.warning("Using BLOCKING poll_job_status - UI will freeze during polling!")

    terminal_states = {"completed", "failed", "moderated"}
    start_time = time.time()

    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            logger.error(f"Poll timeout after {timeout}s for job {job_id}")
            return {
                "error": f"Job polling timeout after {timeout}s",
                "status": "timeout",
                "jobid": job_id
            }

        status_code, job_data = api.get_job(job_id)

        if status_code != 200:
            logger.error(f"Failed to get job status: {status_code} - {job_data}")
            return {"error": f"Failed to get job status: {job_data}", "jobid": job_id}

        status = job_data.get("status", "unknown")

        if status in terminal_states:
            logger.info(f"Job {job_id[:20]} completed with status: {status}")
            return job_data

        # Wait before next poll
        time.sleep(POLL_INTERVAL)


class AsyncJobPoller:
    """
    Non-blocking async job poller using threading.

    Polls job status in background thread and provides callbacks for UI updates.
    """

    def __init__(self, api, job_id: str,
                 on_update: Optional[Callable[[Dict], None]] = None,
                 on_complete: Optional[Callable[[Dict], None]] = None,
                 timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize async job poller.

        Args:
            api: MidjourneyAPI instance
            job_id: Job ID to poll
            on_update: Callback function called on each status update
            on_complete: Callback function called when job completes
            timeout: Maximum polling time in seconds
        """
        self.api = api
        self.job_id = job_id
        self.on_update = on_update
        self.on_complete = on_complete
        self.timeout = timeout

        self.result_queue = Queue()
        self.stop_flag = threading.Event()
        self.thread = None
        self.final_result = None

    def _poll_loop(self):
        """Background polling loop."""
        terminal_states = {"completed", "failed", "moderated"}
        start_time = time.time()

        logger.info(f"Starting async poll for job {self.job_id[:20]}")

        try:
            while not self.stop_flag.is_set():
                # Check timeout
                if time.time() - start_time > self.timeout:
                    logger.error(f"Async poll timeout for job {self.job_id}")
                    error_result = {
                        "error": f"Job polling timeout after {self.timeout}s",
                        "status": "timeout",
                        "jobid": self.job_id
                    }
                    self.result_queue.put(error_result)
                    if self.on_complete:
                        self.on_complete(error_result)
                    break

                # Poll job status
                status_code, job_data = self.api.get_job(self.job_id)

                if status_code != 200:
                    logger.error(f"Failed to poll job: {status_code}")
                    # Don't fail immediately - keep retrying
                    time.sleep(POLL_INTERVAL)
                    continue

                # Update callback
                if self.on_update:
                    try:
                        self.on_update(job_data)
                    except Exception as e:
                        logger.error(f"Error in on_update callback: {e}")

                # Check if terminal state
                status = job_data.get("status", "unknown")
                if status in terminal_states:
                    logger.info(f"Job {self.job_id[:20]} reached terminal state: {status}")
                    self.result_queue.put(job_data)
                    if self.on_complete:
                        try:
                            self.on_complete(job_data)
                        except Exception as e:
                            logger.error(f"Error in on_complete callback: {e}")
                    break

                # Wait before next poll
                time.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.exception(f"Exception in async poll loop: {e}")
            error_result = {"error": str(e), "status": "error", "jobid": self.job_id}
            self.result_queue.put(error_result)

    def start(self):
        """Start async polling in background thread."""
        if self.thread is not None and self.thread.is_alive():
            logger.warning("Poller already running")
            return

        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        add_script_run_ctx(self.thread)
        self.thread.start()
        logger.info(f"Async poller started for job {self.job_id[:20]}")

    def stop(self):
        """Stop async polling."""
        logger.info(f"Stopping async poller for job {self.job_id[:20]}")
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=5)

    def get_result(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Dict]:
        """
        Get final result from polling.

        Args:
            block: Whether to block until result available
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            Final job data or None if not ready
        """
        if self.final_result:
            return self.final_result

        try:
            self.final_result = self.result_queue.get(block=block, timeout=timeout)
            return self.final_result
        except Empty:
            return None

    def is_running(self) -> bool:
        """Check if poller is still running."""
        return self.thread is not None and self.thread.is_alive()


def poll_job_status_async(api, job_id: str,
                          on_update: Optional[Callable[[Dict], None]] = None,
                          on_complete: Optional[Callable[[Dict], None]] = None,
                          timeout: int = DEFAULT_TIMEOUT) -> AsyncJobPoller:
    """
    NON-BLOCKING job status polling using background thread.

    This is the RECOMMENDED way to poll jobs in Streamlit to avoid UI freezes.

    Example usage in Streamlit:
        ```python
        def update_ui(job_data):
            st.session_state.job_status = job_data.get('status')
            st.session_state.progress = job_data.get('response', {}).get('progress_percent', 0)

        def on_done(job_data):
            st.session_state.completed_jobs.append(job_data)
            st.rerun()

        poller = poll_job_status_async(api, job_id, on_update=update_ui, on_complete=on_done)
        poller.start()

        # Store poller in session state for later access
        st.session_state.active_pollers[job_id] = poller
        ```

    Args:
        api: MidjourneyAPI instance
        job_id: Job ID to poll
        on_update: Callback for status updates (called every POLL_INTERVAL)
        on_complete: Callback when job reaches terminal state
        timeout: Maximum polling time in seconds

    Returns:
        AsyncJobPoller instance (call .start() to begin polling)
    """
    return AsyncJobPoller(
        api=api,
        job_id=job_id,
        on_update=on_update,
        on_complete=on_complete,
        timeout=timeout
    )


def poll_multiple_jobs(api, job_ids: list,
                       on_update: Optional[Callable[[str, Dict], None]] = None,
                       on_complete: Optional[Callable[[str, Dict], None]] = None,
                       timeout: int = DEFAULT_TIMEOUT) -> Dict[str, AsyncJobPoller]:
    """
    Poll multiple jobs concurrently using async pollers.

    Args:
        api: MidjourneyAPI instance
        job_ids: List of job IDs to poll
        on_update: Callback(job_id, job_data) for updates
        on_complete: Callback(job_id, job_data) when job completes
        timeout: Maximum polling time per job

    Returns:
        Dictionary mapping job_id -> AsyncJobPoller
    """
    pollers = {}

    for job_id in job_ids:
        # Wrap callbacks to include job_id
        update_cb = (lambda jid: lambda data: on_update(jid, data))(job_id) if on_update else None
        complete_cb = (lambda jid: lambda data: on_complete(jid, data))(job_id) if on_complete else None

        poller = AsyncJobPoller(
            api=api,
            job_id=job_id,
            on_update=update_cb,
            on_complete=complete_cb,
            timeout=timeout
        )
        poller.start()
        pollers[job_id] = poller

    logger.info(f"Started polling {len(pollers)} jobs concurrently")
    return pollers
