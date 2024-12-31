import pytest
from data.memory import ChromaMemoryStore, MemoryStore
import os
import shutil
import time


@pytest.fixture
def memory_store():
    """Fixture to create and cleanup a ChromaMemoryStore instance."""
    # Clean up any existing test database first
    results_dir = os.path.join(os.getcwd(), "results")
    if os.path.exists(results_dir):
        try:
            shutil.rmtree(results_dir)
        except PermissionError:
            pass  # Ignore if files are locked
        time.sleep(0.1)  # Give OS time to release file handles
    
    store = ChromaMemoryStore("test_collection")
    yield store
    
    # Cleanup
    store.clear()
    store.close()
    
    # Give ChromaDB time to release file handles
    time.sleep(0.1)
    
    # Try cleanup with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.path.exists(results_dir):
                shutil.rmtree(results_dir)
            break
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.5)  # Wait before retry
            else:
                print(f"Warning: Could not remove {results_dir}")


def test_add_and_retrieve_memory(memory_store):
    """Test adding and retrieving a memory."""
    # Add a test memory
    test_text = "Player Alice raised to $100"
    test_metadata = {"round": 1, "player": "Alice", "action": "raise"}
    memory_store.add_memory(test_text, test_metadata)

    # Give ChromaDB time to process
    time.sleep(0.1)

    # Retrieve the memory
    memories = memory_store.get_relevant_memories("Alice raise", k=1)

    assert len(memories) == 1
    assert memories[0]["text"] == test_text
    assert memories[0]["metadata"] == test_metadata


def test_multiple_memories_retrieval(memory_store):
    """Test retrieving multiple relevant memories."""
    # Add multiple memories
    memories = [
        ("Player Alice raised to $100", {"round": 1, "player": "Alice", "action": "raise"}),
        ("Player Bob called $100", {"round": 1, "player": "Bob", "action": "call"}),
        ("Player Charlie folded", {"round": 1, "player": "Charlie", "action": "fold"})
    ]
    
    for text, metadata in memories:
        memory_store.add_memory(text, metadata)

    # Retrieve memories
    results = memory_store.get_relevant_memories("Player actions", k=3)
    
    assert len(results) == 3
    assert all("text" in memory and "metadata" in memory for memory in results)


def test_clear_memories(memory_store):
    """Test clearing all memories."""
    # Add a memory
    memory_store.add_memory(
        "Test memory", 
        {"round": 1, "action": "test"}
    )
    
    # Clear memories
    memory_store.clear()
    
    # Verify no memories are returned
    results = memory_store.get_relevant_memories("Test", k=1)
    assert len(results) == 0


def test_game_state_query(memory_store):
    """Test querying with a game state dictionary."""
    # Add some test memories
    memory_store.add_memory(
        "Alice raised when she had a strong hand", 
        {"round": 1, "player": "Alice", "action": "raise"}
    )

    # Create a game state query
    game_state = {
        "pot": 150,
        "current_bet": 50,
        "players": [
            {"name": "Alice", "chips": 1000, "bet": 50},
            {"name": "Bob", "chips": 900, "bet": 0}
        ]
    }

    # Query with game state
    results = memory_store.get_relevant_memories(game_state, k=1)
    assert len(results) > 0


def test_invalid_collection_recovery(memory_store):
    """Test recovery from invalid collection state."""
    # Add initial memory
    memory_store.add_memory("Initial memory", {"round": 1})
    time.sleep(0.2)  # Increase wait time
    
    # Force collection to be recreated
    memory_store.collection = None
    memory_store.add_memory("New memory", {"round": 2})
    time.sleep(0.2)  # Increase wait time
    
    # Query should work after recovery
    query = "memory"
    results = memory_store.get_relevant_memories(query, k=2)
    
    # Debug output
    print(f"Query results for '{query}': {results}")
    assert len(results) > 0


@pytest.mark.skip_cleanup
def test_memory_persistence():
    """Test that memories persist across store instances."""
    collection_name = "persistence_test"
    test_text = "Persistent memory test"
    
    # Ensure clean state
    results_dir = os.path.join(os.getcwd(), "results")
    if os.path.exists(results_dir):
        try:
            shutil.rmtree(results_dir)
        except PermissionError:
            pass
        time.sleep(0.2)
    
    try:
        # First instance
        store1 = ChromaMemoryStore(collection_name)
        store1.add_memory(test_text, {"test": True})
        time.sleep(0.2)  # Wait for processing
        
        # Verify data was added
        results1 = store1.get_relevant_memories(test_text, k=1)
        assert len(results1) == 1, "Failed to add memory in first instance"
        
        # Properly close first instance
        store1.collection = None  # Release collection first
        store1.close()
        time.sleep(0.2)  # Wait for cleanup
        
        # Create new instance
        store2 = ChromaMemoryStore(collection_name)
        time.sleep(0.2)  # Wait for initialization
        
        # Query for the same text
        results2 = store2.get_relevant_memories(test_text, k=1)
        
        # Debug output
        print(f"First instance results: {results1}")
        print(f"Second instance results: {results2}")
        
        # Verify persistence
        assert len(results2) == 1, "Failed to retrieve memory in second instance"
        assert results2[0]["text"] == test_text
        
    finally:
        # Cleanup
        try:
            if 'store2' in locals():
                store2.collection = None  # Release collection first
                store2.close()
            time.sleep(0.2)
            
            if os.path.exists(results_dir):
                shutil.rmtree(results_dir)
        except Exception as e:
            print(f"Cleanup error: {e}") 