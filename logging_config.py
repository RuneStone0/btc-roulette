import os
import logging
import sys
from env_utils import load_environment_variables

# Load environment variables
load_environment_variables()

# Parse LOG_LEVEL environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

# Configure logging with immediate flushing
class FlushingStreamHandler(logging.StreamHandler):
    """Stream handler that flushes immediately after each log."""
    def emit(self, record):
        super().emit(record)
        self.flush()

# Configure logging
handler = FlushingStreamHandler(sys.stdout)
handler.setLevel(numeric_level)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)

# Create a logger
log = logging.getLogger(__name__)
log.setLevel(numeric_level)
log.addHandler(handler)
# Prevent duplicate logs from root logger
log.propagate = False