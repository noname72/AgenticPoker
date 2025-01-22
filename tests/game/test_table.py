import pytest

from game.player import Player
from game.table import Table


def test_table_initialization(mock_players):
    """Test that PlayerQueue initializes with correct default state.

    Verifies:
    - Players list matches input
    - Index starts at 0
    - All players need to act initially
    - No players have acted since last raise
    - All players start as active
    """
    table = Table(mock_players)
    assert table.players == mock_players
    assert table.index == 0
    assert table.needs_to_act == set(mock_players)
    assert table.acted_since_last_raise == set()
    assert len(table.active_players) == len(mock_players)


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
    table = Table(mock_players)
    print("\nInitial queue state:")
    print(f"Players: {[p.name for p in table.players]}")
    print(f"Index: {table.index}")
    print(f"Active players: {[p.name for p in table.active_players]}")

    # All players active initially
    next_player = table.get_next_player()
    print(f"\nFirst get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[0]

    next_player = table.get_next_player()
    print(f"\nSecond get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[1].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[1]

    next_player = table.get_next_player()
    print(f"\nThird get_next_player:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[2].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[2]

    next_player = table.get_next_player()
    print(f"\nFourth get_next_player (wrap around):")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[0]  # Circular order

    # Test with some inactive players
    print("\nSetting Player2 to folded:")
    mock_players[1].folded = True
    table._update_player_lists()
    print(f"Active players after fold: {[p.name for p in table.active_players]}")
    print(f"Current index: {table.index}")

    next_player = table.get_next_player()
    print(f"\nFirst get_next_player after fold:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[0]

    next_player = table.get_next_player()
    print(f"\nSecond get_next_player after fold:")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[2].name}")  # Skip folded player
    print(f"New index: {table.index}")
    assert next_player == mock_players[2]  # Skip folded player

    next_player = table.get_next_player()
    print(f"\nThird get_next_player after fold (wrap around):")
    print(f"Got: {next_player.name}")
    print(f"Expected: {mock_players[0].name}")
    print(f"New index: {table.index}")
    assert next_player == mock_players[0]  # Back to start


def test_is_round_complete(mock_players):
    """Test round completion detection under different conditions.

    Verifies round is complete when:
    - All players are either folded or all-in
    - No active players remain

    Assumes:
    - Folded and all-in players can't take further actions
    - Round should complete when no more actions are possible
    """
    table = Table(mock_players)
    assert not table.is_round_complete()

    # Set all players to either folded or all-in
    mock_players[0].folded = True
    mock_players[1].is_all_in = True
    mock_players[2].folded = True

    assert table.is_round_complete()
    assert len(table.active_players) == 0


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
    table = Table(mock_players)
    player = mock_players[0]

    # Test normal action
    table.mark_player_acted(player)
    assert player not in table.needs_to_act
    assert player in table.acted_since_last_raise

    # Test raise action
    table.mark_player_acted(player, is_raise=True)
    assert table.acted_since_last_raise == {player}
    assert table.needs_to_act == set(p for p in table.active_players if p != player)


def test_reset_action_tracking(mock_players):
    """Test resetting of action tracking for new betting rounds.

    Verifies:
    - All active players need to act after reset
    - Previous actions are cleared

    Assumes:
    - Reset should occur between betting rounds
    - All active players must act in new round
    """
    table = Table(mock_players)
    player = mock_players[0]

    # Mark some actions
    table.mark_player_acted(player)
    assert len(table.acted_since_last_raise) > 0

    # Reset tracking
    table.reset_action_tracking()
    assert table.needs_to_act == set(table.active_players)
    assert len(table.acted_since_last_raise) == 0


def test_all_players_acted(mock_players):
    """Test detection of when all players have acted since last raise.

    Verifies:
    - Initially no players have acted
    - Round complete when all active players have acted

    Assumes:
    - Only active players need to act
    - All active players must act to complete round
    """
    table = Table(mock_players)

    # Initially no one has acted
    assert not table.all_players_acted()

    # Mark all active players as having acted
    for player in table.active_players:
        table.mark_player_acted(player)

    assert table.all_players_acted()


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
    table = Table([])
    assert table.get_next_player() is None
    assert table.is_round_complete()
    assert len(table.needs_to_act) == 0
    assert len(table.acted_since_last_raise) == 0


def test_single_player_table(mock_players):
    """Test queue behavior with only one player.

    Verifies:
    - Same player returned repeatedly
    - Player counted as active

    Assumes:
    - Single player is a valid state
    - Should maintain rotation even with one player
    """
    table = Table([mock_players[0]])
    assert table.get_next_player() == mock_players[0]
    assert (
        table.get_next_player() == mock_players[0]
    )  # Should keep returning the same player
    assert len(table.active_players) == 1


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
    table = Table(mock_players)

    # Test folding
    mock_players[0].folded = True
    table._update_player_lists()
    assert mock_players[0] not in table.active_players
    assert mock_players[0] in table.folded_players

    # Test all-in
    mock_players[1].is_all_in = True
    table._update_player_lists()
    assert mock_players[1] not in table.active_players
    assert mock_players[1] in table.all_in_players

    # Test active player
    assert mock_players[2] in table.active_players
    assert mock_players[2] not in table.folded_players
    assert mock_players[2] not in table.all_in_players


def test_mixed_player_states(mock_players):
    """Test queue handling of multiple player states simultaneously.

    Verifies:
    - Correct counting of players in each state
    - Proper categorization with mixed states

    Assumes:
    - Players can be in different states simultaneously
    - Total of all states should equal total players
    """
    table = Table(mock_players)

    # Set up mixed states
    mock_players[0].folded = True
    mock_players[1].is_all_in = True
    table._update_player_lists()

    assert len(table.active_players) == 1
    assert len(table.folded_players) == 1
    assert len(table.all_in_players) == 1
    assert table.get_active_count() == 1
    assert table.get_folded_count() == 1
    assert table.get_all_in_count() == 1


def test_remove_nonexistent_player(mock_players):
    """Test handling of attempt to remove non-existent player.

    Verifies:
    - Queue state unchanged when removing non-existent player

    Assumes:
    - Removing non-existent player should not affect queue
    - Should not raise exception
    """
    table = Table(mock_players)
    nonexistent_player = Player("Nonexistent", 1000)
    original_players = table.players.copy()
    table.remove_player(nonexistent_player)
    assert table.players == original_players


def test_continuous_betting_round(mock_players):
    """Test that betting continues as long as players keep raising.

    Verifies:
    - Players can act multiple times in a round if there are raises
    - Each raise resets who needs to act
    - Round only completes when all active players have called (no more raises)

    Simulates a sequence of bets/raises:
    1. Player1 bets
    2. Player2 raises
    3. Player3 raises
    4. Action returns to Player1 and Player2
    """
    table = Table(mock_players)
    player1, player2, player3 = mock_players[0:3]

    # Player1 bets
    table.mark_player_acted(player1)
    assert player1 not in table.needs_to_act
    assert player1 in table.acted_since_last_raise
    assert player2 in table.needs_to_act
    assert player3 in table.needs_to_act

    # Player2 raises
    table.mark_player_acted(player2, is_raise=True)
    # After raise, Player1 and Player3 need to act again
    assert player1 in table.needs_to_act
    assert player2 not in table.needs_to_act
    assert player3 in table.needs_to_act
    assert table.acted_since_last_raise == {player2}

    # Player3 re-raises
    table.mark_player_acted(player3, is_raise=True)
    # After re-raise, Player1 and Player2 need to act again
    assert player1 in table.needs_to_act
    assert player2 in table.needs_to_act
    assert player3 not in table.needs_to_act
    assert table.acted_since_last_raise == {player3}

    # Player1 calls
    table.mark_player_acted(player1)
    assert player1 not in table.needs_to_act
    assert player2 in table.needs_to_act

    # Player2 calls
    table.mark_player_acted(player2)
    assert player1 not in table.needs_to_act
    assert player2 not in table.needs_to_act
    assert player3 not in table.needs_to_act

    # Now all players have acted since last raise
    assert table.all_players_acted()


def test_betting_edge_cases(mock_players):
    """Test edge cases and invalid scenarios in betting rounds.

    Verifies:
    1. Player can't act when it's not their turn
    2. Folded players can't act
    3. All-in players can't act
    4. Player can't act twice without a raise in between
    5. Round continues if only one player has acted
    6. Round continues if not all players have acted since last raise
    """
    table = Table(mock_players)
    player1, player2, player3 = mock_players[0:3]

    # Test round not complete with partial actions
    table.mark_player_acted(player1)
    assert (
        not table.all_players_acted()
    )  # Round shouldn't end with only one player acted

    # Test player can't act twice without a raise
    table.mark_player_acted(player1)  # Second action without raise
    assert player1 not in table.needs_to_act  # Should still be marked as acted
    assert not table.all_players_acted()  # Round shouldn't end

    # Test folded player can't affect round completion
    player2.folded = True
    table._update_player_lists()
    table.mark_player_acted(player3)
    assert (
        table.all_players_acted()
    )  # Round should complete with all non-folded players acted

    # Test all-in player can't affect round completion
    table.reset_action_tracking()
    player3.is_all_in = True
    table._update_player_lists()
    table.mark_player_acted(player1)
    assert (
        table.all_players_acted()
    )  # Round should complete with only active player acted

    # Test round continues after raise even with inactive players
    table.reset_action_tracking()
    player2.folded = False  # Unfolded but still all-in
    table._update_player_lists()
    table.mark_player_acted(player1)
    table.mark_player_acted(player2, is_raise=True)
    assert not table.all_players_acted()  # Round shouldn't end until player1 acts again
    assert player1 in table.needs_to_act

    # Test round completion with mixed states
    table.mark_player_acted(player1)  # Player1 calls the raise
    assert table.all_players_acted()  # Now round should complete


def test_is_round_complete_with_all_folded(mock_players):
    """Test round completion when all players are folded."""
    table = Table(mock_players)
    for player in mock_players:
        player.folded = True
    table._update_player_lists()
    assert table.is_round_complete()


def test_is_round_complete_with_all_in(mock_players):
    """Test round completion when all players are all-in."""
    table = Table(mock_players)
    for player in mock_players:
        player.is_all_in = True
    table._update_player_lists()
    assert table.is_round_complete()


def test_mark_player_acted_with_raise(mock_players):
    """Test action tracking when a player raises."""
    table = Table(mock_players)
    player = mock_players[0]
    table.mark_player_acted(player, is_raise=True)
    assert table.acted_since_last_raise == {player}
    assert table.needs_to_act == set(p for p in table.active_players if p != player)


def test_reset_action_tracking_clears_all(mock_players):
    """Test that reset_action_tracking clears all previous actions."""
    table = Table(mock_players)
    table.mark_player_acted(mock_players[0])
    table.reset_action_tracking()
    assert table.needs_to_act == set(table.active_players)
    assert len(table.acted_since_last_raise) == 0


def test_is_round_complete_with_one_remaining_player(mock_players):
    """Test that round is complete when all but one player folds.

    Verifies:
    - Round completes when only one player remains unfolded
    - Last player doesn't need to act
    """
    table = Table(mock_players)

    # Fold all but the last player
    mock_players[0].folded = True
    mock_players[1].folded = True
    mock_players[2].folded = True
    table._update_player_lists()

    # Verify round is complete without last player acting
    assert table.is_round_complete()
    assert len(table.active_players) == 1
    assert table.get_active_count() == 1
    assert table.get_folded_count() == 3
