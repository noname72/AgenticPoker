# import os
# import shutil
# import tempfile
# import time

# import pytest

# from data.memory import ChromaMemoryStore, MemoryStore


# @pytest.fixture(autouse=True)
# def setup_test_env():
#     """Setup test environment for all tests."""
#     os.environ["PYTEST_RUNNING"] = "1"
#     yield
#     os.environ.pop("PYTEST_RUNNING", None)


# @pytest.fixture
# def memory_store():
#     """Fixture to create and cleanup a ChromaMemoryStore instance."""
#     # Set up test environment
#     temp_dir = tempfile.gettempdir()
#     test_db_path = os.path.join(temp_dir, "chroma_test_db")

#     # Clean up any existing test database
#     try:
#         if os.path.exists(test_db_path):
#             shutil.rmtree(test_db_path)
#             time.sleep(0.2)  # Give OS time to release handles
#     except PermissionError:
#         # If we can't remove the directory, try to clean its contents
#         try:
#             for item in os.listdir(test_db_path):
#                 path = os.path.join(test_db_path, item)
#                 if os.path.isfile(path):
#                     os.unlink(path)
#                 elif os.path.isdir(path):
#                     shutil.rmtree(path)
#         except Exception as e:
#             print(f"Warning: Could not clean test directory: {e}")

#     store = ChromaMemoryStore("test_collection")
#     yield store

#     # Cleanup after test
#     try:
#         store.clear()
#         store.close()
#         time.sleep(0.2)  # Wait for cleanup

#         if os.path.exists(test_db_path):
#             try:
#                 shutil.rmtree(test_db_path)
#             except PermissionError:
#                 # If we can't remove the directory, try to clean its contents
#                 for item in os.listdir(test_db_path):
#                     try:
#                         path = os.path.join(test_db_path, item)
#                         if os.path.isfile(path):
#                             os.unlink(path)
#                         elif os.path.isdir(path):
#                             shutil.rmtree(path)
#                     except Exception:
#                         pass
#     except Exception as e:
#         print(f"Cleanup warning: {e}")


# def test_add_and_retrieve_memory(memory_store):
#     """Test adding and retrieving a memory with retries."""
#     test_text = "Player Alice raised to $100"
#     test_metadata = {"round": 1, "player": "Alice", "action": "raise"}

#     # Add memory with retry
#     max_retries = 3
#     for attempt in range(max_retries):
#         try:
#             memory_store.add_memory(test_text, test_metadata)
#             time.sleep(0.2)  # Wait for processing

#             # Verify memory was added
#             memories = memory_store.get_relevant_memories("Alice raise", k=1)
#             assert len(memories) == 1
#             assert memories[0]["text"] == test_text
#             assert all(
#                 test_metadata[k] == memories[0]["metadata"][k] for k in test_metadata
#             )
#             break
#         except Exception as e:
#             if attempt == max_retries - 1:
#                 raise
#             time.sleep(0.5)


# def test_multiple_memories_retrieval(memory_store):
#     """Test retrieving multiple relevant memories."""
#     # Add multiple memories
#     memories = [
#         (
#             "Player Alice raised to $100",
#             {"round": 1, "player": "Alice", "action": "raise"},
#         ),
#         ("Player Bob called $100", {"round": 1, "player": "Bob", "action": "call"}),
#         ("Player Charlie folded", {"round": 1, "player": "Charlie", "action": "fold"}),
#     ]

#     for text, metadata in memories:
#         memory_store.add_memory(text, metadata)

#     # Retrieve memories
#     results = memory_store.get_relevant_memories("Player actions", k=3)

#     assert len(results) == 3
#     assert all("text" in memory and "metadata" in memory for memory in results)


# def test_clear_memories(memory_store):
#     """Test clearing all memories."""
#     # Add a memory
#     memory_store.add_memory("Test memory", {"round": 1, "action": "test"})

#     # Clear memories
#     memory_store.clear()

#     # Verify no memories are returned
#     results = memory_store.get_relevant_memories("Test", k=1)
#     assert len(results) == 0


# def test_game_state_query(memory_store):
#     """Test querying with a game state dictionary."""
#     # Add some test memories
#     memory_store.add_memory(
#         "Alice raised when she had a strong hand",
#         {"round": 1, "player": "Alice", "action": "raise"},
#     )

#     # Create a game state query
#     game_state = {
#         "pot": 150,
#         "current_bet": 50,
#         "players": [
#             {"name": "Alice", "chips": 1000, "bet": 50},
#             {"name": "Bob", "chips": 900, "bet": 0},
#         ],
#     }

#     # Query with game state
#     results = memory_store.get_relevant_memories(game_state, k=1)
#     assert len(results) > 0


# def test_invalid_collection_recovery(memory_store):
#     """Test recovery from invalid collection state."""
#     # Add initial memory
#     memory_store.add_memory("Initial memory", {"round": 1})
#     time.sleep(0.2)  # Wait for processing

#     # Get initial results to verify memory was added
#     initial_results = memory_store.get_relevant_memories("memory", k=1)
#     assert len(initial_results) > 0, "Initial memory was not added"

#     # Force collection to be recreated
#     memory_store.collection = None

#     # Try to add new memory - this should trigger recovery
#     memory_store.add_memory("New memory", {"round": 2})
#     time.sleep(0.2)  # Wait for processing

#     # Query should work after recovery and return both memories
#     results = memory_store.get_relevant_memories("memory", k=2)
#     assert len(results) > 0, "No memories found after recovery"
#     assert len(results) == 2, "Not all memories were recovered"

#     # Verify both memories are present
#     memory_texts = [m["text"] for m in results]
#     assert "Initial memory" in memory_texts, "Initial memory was lost"
#     assert "New memory" in memory_texts, "New memory was not added"


# @pytest.mark.skip_cleanup
# def test_memory_persistence():
#     """Test that memories persist across store instances."""
#     collection_name = "persistence_test"
#     test_text = "Persistent memory test"

#     # Ensure clean state
#     results_dir = os.path.join(os.getcwd(), "results")
#     if os.path.exists(results_dir):
#         try:
#             shutil.rmtree(results_dir)
#         except PermissionError:
#             pass
#         time.sleep(0.2)

#     try:
#         # First instance
#         store1 = ChromaMemoryStore(collection_name)
#         store1.add_memory(test_text, {"test": True})
#         time.sleep(0.2)  # Wait for processing

#         # Verify data was added
#         results1 = store1.get_relevant_memories(test_text, k=1)
#         assert len(results1) == 1, "Failed to add memory in first instance"

#         # Properly close first instance
#         store1.collection = None  # Release collection first
#         store1.close()
#         time.sleep(0.2)  # Wait for cleanup

#         # Create new instance
#         store2 = ChromaMemoryStore(collection_name)
#         time.sleep(0.2)  # Wait for initialization

#         # Query for the same text
#         results2 = store2.get_relevant_memories(test_text, k=1)

#         # Debug output
#         print(f"First instance results: {results1}")
#         print(f"Second instance results: {results2}")

#         # Verify persistence
#         assert len(results2) == 1, "Failed to retrieve memory in second instance"
#         assert results2[0]["text"] == test_text

#     finally:
#         # Cleanup
#         try:
#             if "store2" in locals():
#                 store2.collection = None  # Release collection first
#                 store2.close()
#             time.sleep(0.2)

#             if os.path.exists(results_dir):
#                 shutil.rmtree(results_dir)
#         except Exception as e:
#             print(f"Cleanup error: {e}")
