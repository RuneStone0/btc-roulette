import os
import logging
from env_utils import load_environment_variables

# Load environment variables
load_environment_variables()

# Parse LOG_LEVEL environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(level=numeric_level, format='%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Create a logger
log = logging.getLogger(__name__)
