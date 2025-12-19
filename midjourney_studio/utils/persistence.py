
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

HISTORY_FILE = Path("job_history.json")

def load_job_history() -> List[Dict[str, Any]]:
    """Load job history from JSON file."""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        # Ensure it's a list
        if isinstance(data, list):
            logger.info(f"Loaded {len(data)} jobs from history")
            return data
        else:
            logger.warning("History file is not a list, resetting")
            return []
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []

def save_job_history(history: List[Dict[str, Any]]) -> bool:
    """Save job history to JSON file."""
    try:
        HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"Failed to save history: {e}")
        return False
