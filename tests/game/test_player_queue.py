import pytest
from game.player_queue import PlayerQueue
from game.player import Player


@pytest.fixture
def players():
    return [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]


def test_player_queue_initialization(players):
    queue = PlayerQueue(players)
    assert queue.players == players
    assert queue.index == 0


def test_get_next_player(players):
    queue = PlayerQueue(players)
    assert queue.get_next_player() == players[0]
    assert queue.get_next_player() == players[1]
    assert queue.get_next_player() == players[2]
    assert queue.get_next_player() == players[0]  # Circular order


def test_remove_player(players):
    queue = PlayerQueue(players)
    player_to_remove = players[1]  # Player 2
    player1 = players[0]  # Store reference to Player 1
    player3 = players[2]  # Store reference to Player 3
    
    print("\nDebug - Before removal:")
    print(f"Players in queue: {[(p.name, id(p)) for p in queue.players]}")
    print(f"Trying to remove: {player_to_remove.name} (id: {id(player_to_remove)})")
    
    queue.remove_player(player_to_remove)
    
    print("\nDebug - After removal:")
    print(f"Players in queue: {[(p.name, id(p)) for p in queue.players]}")
    print(f"Looking for removed player: {player_to_remove.name} (id: {id(player_to_remove)})")
    
    assert player_to_remove not in queue.players
    assert queue.get_next_player() == player1
    assert queue.get_next_player() == player3
    assert queue.get_next_player() == player1  # Circular order


def test_reset_queue(players):
    queue = PlayerQueue(players)
    queue.get_next_player()
    queue.get_next_player()
    queue.reset_queue()
    assert queue.index == 0
    assert queue.get_next_player() == players[0]


def test_is_round_complete(players):
    queue = PlayerQueue(players)
    assert not queue.is_round_complete()
    
    # Set all players to either folded or all-in
    players[0].folded = True
    players[1].is_all_in = True
    players[2].folded = True
    
    assert queue.is_round_complete()


def test_empty_queue():
    queue = PlayerQueue([])
    assert queue.get_next_player() is None
    assert queue.is_round_complete() is True  # Empty queue should be considered complete
    

def test_single_player_queue(players):
    queue = PlayerQueue([players[0]])
    assert queue.get_next_player() == players[0]
    assert queue.get_next_player() == players[0]  # Should keep returning the same player
    

def test_remove_last_player(players):
    queue = PlayerQueue([players[0]])
    queue.remove_player(players[0])
    assert len(queue.players) == 0
    assert queue.get_next_player() is None
    

def test_remove_player_at_current_index(players):
    queue = PlayerQueue(players)
    # Store references to players we'll check against
    player1 = players[0]
    player3 = players[2]
    
    print("\nDebug - Initial state:")
    print(f"Players in queue: {[(p.name, id(p)) for p in queue.players]}")
    print(f"Current index: {queue.index}")
    
    # Get first player (moves index to 1)
    first_player = queue.get_next_player()
    print("\nDebug - After getting first player:")
    print(f"First player: {first_player.name}")
    print(f"Current index: {queue.index}")
    assert first_player == player1
    
    # Remove current player (at index 1)
    print("\nDebug - Before removing player[1]:")
    print(f"Removing player: {players[1].name}")
    print(f"Current index: {queue.index}")
    queue.remove_player(players[1])
    
    print("\nDebug - After removal:")
    print(f"Players in queue: {[(p.name, id(p)) for p in queue.players]}")
    print(f"Current index: {queue.index}")
    
    # Next player should be Player 3, since Player 2 was removed
    next_player = queue.get_next_player()
    print("\nDebug - After getting next player:")
    print(f"Next player: {next_player.name}")
    print(f"Current index: {queue.index}")
    assert next_player == player3
    
    # Should continue rotation back to Player 1
    next_player = queue.get_next_player()
    print("\nDebug - After completing rotation:")
    print(f"Next player: {next_player.name}")
    print(f"Current index: {queue.index}")
    assert next_player == player1


def test_remove_nonexistent_player(players):
    queue = PlayerQueue(players)
    nonexistent_player = Player("Nonexistent", 1000)
    original_players = queue.players.copy()
    queue.remove_player(nonexistent_player)
    assert queue.players == original_players  # Queue should remain unchanged


def test_is_round_complete_mixed_states(players):
    queue = PlayerQueue(players)
    
    # Test various combinations
    players[0].folded = True
    players[1].is_all_in = False
    players[2].folded = False
    assert not queue.is_round_complete()
    
    players[1].is_all_in = True
    players[2].folded = False
    assert not queue.is_round_complete()
    
    players[2].is_all_in = True
    assert queue.is_round_complete()
