import logging
from dotenv import load_dotenv, find_dotenv

def load_environment_variables():
    """
    Load environment variables from a .env file if it exists.
    If the .env file is not found, it will log a message and use existing environment variables.
    """
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        logging.info(".env file not found, loading from environment variables")
