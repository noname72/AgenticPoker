import logging
import os
import shutil
import sys
from datetime import datetime
import time

logger = logging.getLogger(__name__)


def setup_logging(session_id=0):
    """
    Configure logging with UTF-8 encoding support and session management.

    Sets up a logging system that outputs to both console and file, with UTF-8 encoding.
    Creates a new log file for each session and configures the root logger with
    appropriate formatting.

    Args:
        session_id (int | str, optional): Unique identifier for this game session.
            If 0 or falsy, generates timestamp-based ID. Defaults to 0.

    Returns:
        None

    Side Effects:
        - Clears existing logging handlers
        - Creates new log file named 'poker_game.log'
        - Configures console and file output with UTF-8 encoding
        - Sets httpx logging level to WARNING
        - Logs session start information with timestamp
    """
    # Clear any existing handlers
    logging.getLogger().handlers = []

    # Generate session ID if not provided
    if not session_id:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create log filename with session ID
    log_filename = f"poker_game.log"

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
            # File handler with UTF-8 encoding and session-specific file
            logging.FileHandler(log_filename, encoding="utf-8", mode="w"),
        ],
    )

    # Silence httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log session start with clear separator
    logging.info(f"\n{'='*70}")
    logging.info(f"New Poker Game Session Started - ID: {session_id}")
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"{'='*70}\n")


def clear_results_directory() -> None:
    """
    Clear the results directory containing ChromaDB data.

    Performs a thorough cleanup of the ChromaDB directory by:
    1. Attempting to properly reset ChromaDB collections
    2. Closing any open file handles
    3. Removing the directory and its contents
    4. Creating a fresh empty directory

    Returns:
        None

    Raises:
        No exceptions are raised, but warnings are logged for:
        - Failed ChromaDB reset attempts
        - Unable to remove directory or files
        - Failed file handle closures

    Side Effects:
        - Deletes all ChromaDB collections
        - Removes and recreates the 'results/chroma_db' directory
        - Logs various status messages and warnings
    """
    results_dir = os.path.join(os.getcwd(), "results")
    chroma_dir = os.path.join(results_dir, "chroma_db")

    try:
        # First check if directory exists
        if not os.path.exists(chroma_dir):
            os.makedirs(chroma_dir, exist_ok=True)
            logger.info("Created fresh ChromaDB directory")
            return

        # Try to reset ChromaDB using its own methods
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=chroma_dir,
                settings=Settings(
                    allow_reset=True, anonymized_telemetry=False, is_persistent=True
                ),
            )

            # Get all collection names and delete them
            collections = client.list_collections()
            for collection in collections:
                client.delete_collection(collection.name)
                logger.info(f"Deleted collection: {collection.name}")

            # Reset and close the client properly
            client.reset()
            del client

            logger.info("Reset ChromaDB successfully")

        except Exception as e:
            logger.warning(f"Failed to reset ChromaDB cleanly: {str(e)}")

        # Wait for resources to be released
        time.sleep(1.0)

        # Try to remove the directory if it exists
        if os.path.exists(chroma_dir):
            try:
                import psutil

                proc = psutil.Process()
                for handler in proc.open_files():
                    if chroma_dir in handler.path:
                        logger.warning(f"Closing file handle: {handler.path}")
                        try:
                            os.close(handler.fd)
                        except:
                            pass

                shutil.rmtree(chroma_dir)
                logger.info("Removed ChromaDB directory")
            except Exception as e:
                logger.warning(f"Could not remove ChromaDB directory: {str(e)}")
                # If we can't remove it, try to clean its contents
                try:
                    for item in os.listdir(chroma_dir):
                        item_path = os.path.join(chroma_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception as e:
                            logger.warning(f"Could not remove {item_path}: {str(e)}")
                except Exception as e:
                    logger.warning(
                        f"Could not clean ChromaDB directory contents: {str(e)}"
                    )

        # Recreate empty directory
        os.makedirs(chroma_dir, exist_ok=True)
        logger.info("Created fresh ChromaDB directory")

    except Exception as e:
        logger.error(f"Failed to clear results directory: {str(e)}")
