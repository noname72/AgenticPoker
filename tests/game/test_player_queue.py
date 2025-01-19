import pytest

from game.player import Player
from game.player_queue import PlayerQueue


def test_player_queue_initialization(mock_players):
    """Test that PlayerQueue initializes with correct default state.

    Verifies:
    - Players list matches input
    - Index starts at 0
    - All players need to act initially
    - No players have acted since last raise
    - All players start as active
    """
    queue = PlayerQueue(mock_players)
    assert queue.players == mock_players
    assert queue.index == 0
    assert queue.needs_to_act == set(mock_players)
    assert queue.acted_since_last_raise == set()
    assert len(queue.active_players) == len(mock_players)


def test_get_next_player(mock_players):
    """Test player rotation and handling of inactive players.

    Verifies:
    1. Basic rotation with all active players:
       - Returns players in order
       - Wraps around to start after last player

    2. Rotation with inactive players:
       - Skips folded players
       - Maintains correct order
       - Still wraps around correctly
    """
    queue = PlayerQueue(mock_players)
    print("\nInitial queue state:")
    print(f"Players: {[p.name for p in queue.players]}")
    print(f"Index: {queue.index}")
    print(f"Active players: {[p.name for p in queue.active_players]}")

    # All players active initially
    next_player = queue.get_next_player()
    print(f"\nFirst get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[0]

    next_player = queue.get_next_player()
    print(f"\nSecond get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[1].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[1]

    next_player = queue.get_next_player()
    print(f"\nThird get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[2].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[2]

    next_player = queue.get_next_player()
    print(f"\nFourth get_next_player (wrap around):")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[0]  # Circular order

    # Test with some inactive players
    print("\nSetting Player2 to folded:")
    mock_players[1].folded = True
    queue._update_player_lists()
    print(f"Active players after fold: {[p.name for p in queue.active_players]}")
    print(f"Current index: {queue.index}")

    next_player = queue.get_next_player()
    print(f"\nFirst get_next_player after fold:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[0]

    next_player = queue.get_next_player()
    print(f"\nSecond get_next_player after fold:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[2].name}")  # Skip folded player
    print(f"New index: {queue.index}")
    assert next_player == mock_players[2]  # Skip folded player

    next_player = queue.get_next_player()
    print(f"\nThird get_next_player after fold (wrap around):")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {queue.index}")
    assert next_player == mock_players[0]  # Back to start


def test_remove_player(mock_players):
    """Test player removal and its effects on queue state.

    Verifies:
    - Player is removed from all tracking sets/lists
    - Remaining players maintain correct rotation
    - Queue state remains consistent after removal

    Assumes:
    - Player removal is permanent
    - Removed player should not appear in any queue state
    """
    queue = PlayerQueue(mock_players)
    player_to_remove = mock_players[1]  # Player 2
    player1 = mock_players[0]  # Store reference to Player 1
    player3 = mock_players[2]  # Store reference to Player 3

    queue.remove_player(player_to_remove)

    assert player_to_remove not in queue.players
    assert player_to_remove not in queue.needs_to_act
    assert player_to_remove not in queue.acted_since_last_raise
    assert player_to_remove not in queue.active_players

    assert queue.get_next_player() == player1
    assert queue.get_next_player() == player3
    assert queue.get_next_player() == player1  # Circular order


def test_is_round_complete(mock_players):
    """Test round completion detection under different conditions.

    Verifies round is complete when:
    - All players are either folded or all-in
    - No active players remain

    Assumes:
    - Folded and all-in players can't take further actions
    - Round should complete when no more actions are possible
    """
    queue = PlayerQueue(mock_players)
    assert not queue.is_round_complete()

    # Set all players to either folded or all-in
    mock_players[0].folded = True
    mock_players[1].is_all_in = True
    mock_players[2].folded = True
    queue._update_player_lists()

    assert queue.is_round_complete()
    assert len(queue.active_players) == 0


def test_mark_player_acted(mock_players):
    """Test tracking of player actions during betting rounds.

    Verifies:
    1. Normal action:
       - Player removed from needs_to_act
       - Player added to acted_since_last_raise

    2. Raise action:
       - Resets acted_since_last_raise to only raiser
       - All other active players need to act again

    Assumes:
    - Players can't act twice without a raise in between
    - Raise requires everyone else to act again
    """
    queue = PlayerQueue(mock_players)
    player = mock_players[0]

    # Test normal action
    queue.mark_player_acted(player)
    assert player not in queue.needs_to_act
    assert player in queue.acted_since_last_raise

    # Test raise action
    queue.mark_player_acted(player, is_raise=True)
    assert queue.acted_since_last_raise == {player}
    assert queue.needs_to_act == set(p for p in queue.active_players if p != player)


def test_reset_action_tracking(mock_players):
    """Test resetting of action tracking for new betting rounds.

    Verifies:
    - All active players need to act after reset
    - Previous actions are cleared

    Assumes:
    - Reset should occur between betting rounds
    - All active players must act in new round
    """
    queue = PlayerQueue(mock_players)
    player = mock_players[0]

    # Mark some actions
    queue.mark_player_acted(player)
    assert len(queue.acted_since_last_raise) > 0

    # Reset tracking
    queue.reset_action_tracking()
    assert queue.needs_to_act == set(queue.active_players)
    assert len(queue.acted_since_last_raise) == 0


def test_all_players_acted(mock_players):
    """Test detection of when all players have acted since last raise.

    Verifies:
    - Initially no players have acted
    - Round complete when all active players have acted

    Assumes:
    - Only active players need to act
    - All active players must act to complete round
    """
    queue = PlayerQueue(mock_players)

    # Initially no one has acted
    assert not queue.all_players_acted()

    # Mark all active players as having acted
    for player in queue.active_players:
        queue.mark_player_acted(player)

    assert queue.all_players_acted()


def test_empty_queue():
    """Test behavior of queue with no players.

    Verifies:
    - No next player available
    - Round is considered complete
    - No players in tracking sets

    Assumes:
    - Empty queue is a valid state
    - Empty queue means round should end
    """
    queue = PlayerQueue([])
    assert queue.get_next_player() is None
    assert queue.is_round_complete()
    assert len(queue.needs_to_act) == 0
    assert len(queue.acted_since_last_raise) == 0


def test_single_player_queue(mock_players):
    """Test queue behavior with only one player.

    Verifies:
    - Same player returned repeatedly
    - Player counted as active

    Assumes:
    - Single player is a valid state
    - Should maintain rotation even with one player
    """
    queue = PlayerQueue([mock_players[0]])
    assert queue.get_next_player() == mock_players[0]
    assert (
        queue.get_next_player() == mock_players[0]
    )  # Should keep returning the same player
    assert len(queue.active_players) == 1


def test_player_state_updates(mock_players):
    """Test tracking of player state changes.

    Verifies:
    - Folded players removed from active list
    - All-in players removed from active list
    - Players correctly categorized in respective lists

    Assumes:
    - Players can only be in one state (active, folded, or all-in)
    - State changes require _update_player_lists call
    """
    queue = PlayerQueue(mock_players)

    # Test folding
    mock_players[0].folded = True
    queue._update_player_lists()
    assert mock_players[0] not in queue.active_players
    assert mock_players[0] in queue.folded_players

    # Test all-in
    mock_players[1].is_all_in = True
    queue._update_player_lists()
    assert mock_players[1] not in queue.active_players
    assert mock_players[1] in queue.all_in_players

    # Test active player
    assert mock_players[2] in queue.active_players
    assert mock_players[2] not in queue.folded_players
    assert mock_players[2] not in queue.all_in_players


def test_mixed_player_states(mock_players):
    """Test queue handling of multiple player states simultaneously.

    Verifies:
    - Correct counting of players in each state
    - Proper categorization with mixed states

    Assumes:
    - Players can be in different states simultaneously
    - Total of all states should equal total players
    """
    queue = PlayerQueue(mock_players)

    # Set up mixed states
    mock_players[0].folded = True
    mock_players[1].is_all_in = True
    queue._update_player_lists()

    assert len(queue.active_players) == 1
    assert len(queue.folded_players) == 1
    assert len(queue.all_in_players) == 1
    assert queue.get_active_count() == 1
    assert queue.get_folded_count() == 1
    assert queue.get_all_in_count() == 1


def test_remove_nonexistent_player(mock_players):
    """Test handling of attempt to remove non-existent player.

    Verifies:
    - Queue state unchanged when removing non-existent player

    Assumes:
    - Removing non-existent player should not affect queue
    - Should not raise exception
    """
    queue = PlayerQueue(mock_players)
    nonexistent_player = Player("Nonexistent", 1000)
    original_players = queue.players.copy()
    queue.remove_player(nonexistent_player)
    assert queue.players == original_players
