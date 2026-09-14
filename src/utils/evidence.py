import os
import re
from datetime import datetime

def generate_screenshot_path(prefix: str) -> str:
    """
    Generates a standardized timestamped screenshot path in the src/evidence directory.
    prefix: e.g., 'discovery_timeout' or 'replay_failure_mock_bank_tx'
    """
    evidence_dir = os.path.join("src", "evidence")
    if not os.path.exists(evidence_dir):
        os.makedirs(evidence_dir)
        
    safe_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', prefix).lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(evidence_dir, f"{safe_prefix}_{timestamp}.png")
