import pytest

from game.player import Player
from game.table import Table


def test_round_complete_when_all_players_acted():
    """Test that round is complete when all active players have acted.
    
    Assumptions:
    - All players start with chips and are active
    - No raises occur during the round
    - Players act in sequence without folding or going all-in
    """
    # Setup players
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Simulate all players acting (without raises)
    for player in players:
        table.mark_player_acted(player)

    assert table.is_round_complete()


def test_round_incomplete_when_not_all_acted():
    """Test that round is incomplete when some players haven't acted.
    
    Assumptions:
    - All players start active and with chips
    - Round is incomplete until all active players act
    - No raises occur during the round
    - Player order doesn't affect completion status
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Only first player acts
    table.mark_player_acted(players[0])

    assert not table.is_round_complete()


def test_round_complete_after_raise_and_calls():
    """Test round completion after a raise and subsequent calls.
    
    Assumptions:
    - All players start active and with chips
    - A raise requires all other players to act again
    - Calling players don't reset action
    - Round completes when all players have acted on the raise
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Player 1 raises
    table.mark_player_acted(players[0], is_raise=True)

    # Other players call
    table.mark_player_acted(players[1])
    table.mark_player_acted(players[2])

    assert table.is_round_complete()


def test_round_complete_with_folded_players():
    """Test round completion when some players have folded.
    
    Assumptions:
    - Folded players are immediately inactive
    - Folded players don't need to act for round completion
    - Folding doesn't reset action for other players
    - Players can fold at any time during the round
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Player 2 folds
    players[1].folded = True

    # Remaining players act
    table.mark_player_acted(players[0])
    table.mark_player_acted(players[2])

    assert table.is_round_complete()


def test_round_complete_with_all_in_players():
    """Test round completion when some players are all-in.
    
    Assumptions:
    - All-in players are immediately inactive
    - All-in players don't need to act for round completion
    - Going all-in doesn't reset action for other players
    - All-in players must have 0 chips remaining
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Player 2 goes all-in
    players[1].is_all_in = True
    players[1].chips = 0

    # Remaining players act
    table.mark_player_acted(players[0])
    table.mark_player_acted(players[2])

    assert table.is_round_complete()


def test_round_complete_with_one_active_player():
    """Test round completion when only one active player remains.
    
    Assumptions:
    - Round can complete with a single active player
    - Folded players are immediately inactive
    - Last active player must still act for round completion
    - Order of folding doesn't affect completion
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Two players fold
    players[1].folded = True
    players[2].folded = True

    # Last player acts
    table.mark_player_acted(players[0])

    assert table.is_round_complete()


def test_round_reset_after_raise():
    """Test that action tracking resets properly after a raise.
    
    Assumptions:
    - A raise requires all other active players to act again
    - The raising player doesn't need to act again
    - Previous actions are ignored after a raise
    - Round is incomplete until all players act on the raise
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # First round of betting
    table.mark_player_acted(players[0])
    table.mark_player_acted(players[1])

    # Player 3 raises
    table.mark_player_acted(players[2], is_raise=True)

    # Check that others need to act again
    assert players[0] in table.needs_to_act
    assert players[1] in table.needs_to_act
    assert players[2] not in table.needs_to_act
    assert not table.is_round_complete()


def test_round_complete_after_multiple_raises():
    """Test round completion after multiple raises and calls.
    
    Assumptions:
    - Each raise resets action for all other players
    - Players who have already acted must act again after a raise
    - The last raiser doesn't need to act again
    - Round completes when all players have acted on the last raise
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # First player raises
    table.mark_player_acted(players[0], is_raise=True)

    # Second player re-raises
    table.mark_player_acted(players[1], is_raise=True)

    # Others call the re-raise
    table.mark_player_acted(players[2])
    table.mark_player_acted(players[0])

    assert table.is_round_complete()


def test_get_next_player_skips_inactive():
    """Test that get_next_player skips folded and all-in players.
    
    Assumptions:
    - Folded and all-in players are skipped in turn order
    - Active players are returned in table position order
    - Player states (folded, all-in) don't change during iteration
    - Table position wraps around after last player
    """
    players = [
        Player("Alice", 1000),
        Player("Bob", 1000),
        Player("Charlie", 1000),
        Player("David", 1000),
    ]
    table = Table(players)

    # Set up some inactive players
    players[1].folded = True  # Bob folds
    players[2].is_all_in = True  # Charlie all-in

    # First active player should be Alice
    next_player = table.get_next_player()
    assert next_player == players[0]

    # Next active player should be David (skipping Bob and Charlie)
    table.mark_player_acted(players[0])
    next_player = table.get_next_player()
    assert next_player == players[3]


def test_round_complete_mixed_scenario():
    """Test round completion with a mix of folded, all-in, and active players.
    
    Assumptions:
    - Folded and all-in players are inactive
    - Only active players need to act for round completion
    - Player states can be set at any time
    - Round completion only considers active players
    - All-in players must have 0 chips
    """
    players = [
        Player("Alice", 1000),
        Player("Bob", 1000),
        Player("Charlie", 1000),
        Player("David", 1000),
        Player("Eve", 1000),
    ]
    table = Table(players)

    # Set up mixed player states
    players[1].folded = True  # Bob folds
    players[2].is_all_in = True  # Charlie all-in
    players[2].chips = 0

    # Active players act
    table.mark_player_acted(players[0])  # Alice acts
    table.mark_player_acted(players[3])  # David acts
    table.mark_player_acted(players[4])  # Eve acts

    assert table.is_round_complete()


def test_round_complete_when_all_but_one_all_in():
    """Test round completion when all but one player is all-in.
    
    Assumptions:
    - All-in players are inactive and don't need to act
    - The last active player must act for round completion
    - All-in players have 0 chips
    - Round can complete with only one active player
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Two players go all-in
    players[0].is_all_in = True
    players[0].chips = 0
    players[1].is_all_in = True
    players[1].chips = 0

    # Last player acts
    table.mark_player_acted(players[2])

    assert table.is_round_complete()


def test_round_complete_with_zero_chip_players():
    """Test round completion when some players have zero chips but aren't all-in.
    
    Assumptions:
    - Players with 0 chips are considered inactive
    - Players with 0 chips are not marked as all-in
    - Only players with chips > 0 need to act for round completion
    """
    players = [Player("Alice", 0), Player("Bob", 1000), Player("Charlie", 0)]
    table = Table(players)

    # Only Bob should be active since others have no chips
    table.mark_player_acted(players[1])

    assert table.is_round_complete()


def test_round_complete_with_single_chip_players():
    """Test round completion with players having minimal chips.
    
    Assumptions:
    - Players with 1 chip are considered active
    - All players can still act regardless of chip count
    - Chip count doesn't affect round completion logic
    - No raises occur (which would require more chips)
    """
    players = [Player("Alice", 1), Player("Bob", 1), Player("Charlie", 1000)]
    table = Table(players)

    # All players act
    for player in players:
        table.mark_player_acted(player)

    assert table.is_round_complete()


def test_get_next_player_with_all_inactive():
    """Test get_next_player when all players are inactive.
    
    Assumptions:
    - Folded players are inactive
    - All-in players are inactive
    - Players with 0 chips are inactive
    - get_next_player returns None when no active players exist
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Make all players inactive
    for player in players:
        player.folded = True

    assert table.get_next_player() is None


def test_round_complete_after_raise_then_all_fold():
    """Test round completion when everyone folds after a raise.
    
    Assumptions:
    - Round completes immediately when all but one player folds
    - Folded players don't need to act on a raise
    - The raising player doesn't need to act again
    - Player states (folded) can change during the round
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # First player raises
    table.mark_player_acted(players[0], is_raise=True)

    # Others fold
    players[1].folded = True
    players[2].folded = True

    assert table.is_round_complete()


def test_round_reset_with_mixed_states():
    """Test reset_action_tracking with mixed player states.
    
    Assumptions:
    - Folded players should not be in needs_to_act after reset
    - All-in players should not be in needs_to_act after reset
    - Only active players (not folded, not all-in, has chips) should need to act
    - Reset doesn't change player states (folded, all-in, etc.)
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Set up mixed states
    players[0].folded = True
    players[1].is_all_in = True
    players[1].chips = 0

    # Reset tracking
    table.reset_action_tracking()

    # Verify only active players need to act
    assert players[0] not in table.needs_to_act  # Folded
    assert players[1] not in table.needs_to_act  # All-in
    assert players[2] in table.needs_to_act  # Active


def test_round_complete_with_alternating_raises():
    """Test round completion with players taking turns raising.
    
    Assumptions:
    - Each raise resets the action for all other active players
    - Players can raise multiple times in a round
    - Round completes only when all players act on the final raise
    - No players fold or go all-in during the sequence
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Sequence of raises
    table.mark_player_acted(players[0], is_raise=True)  # Alice raises
    table.mark_player_acted(players[1], is_raise=True)  # Bob re-raises
    table.mark_player_acted(players[2], is_raise=True)  # Charlie re-raises
    table.mark_player_acted(players[0], is_raise=True)  # Alice re-raises again

    # Others call final raise
    table.mark_player_acted(players[1])
    table.mark_player_acted(players[2])

    assert table.is_round_complete()


def test_get_next_player_circular():
    """Test that get_next_player properly wraps around the table.
    
    Assumptions:
    - Table position wraps from last player back to first
    - All players remain active throughout the test
    - Player order remains constant
    - mark_player_acted doesn't affect the circular progression
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Move through all players twice to verify circular behavior
    expected_sequence = players * 2
    actual_sequence = []

    for _ in range(6):  # Two full circles
        next_player = table.get_next_player()
        actual_sequence.append(next_player)
        table.mark_player_acted(next_player)

    assert actual_sequence == expected_sequence[:6]


def test_reset_action_tracking_during_active_round():
    """Test resetting action tracking in the middle of a betting round.
    
    Assumptions:
    - Reset should clear all previous actions
    - Only active players should be added to needs_to_act
    - Previous actions since last raise should be cleared
    - Player states should not be affected by reset
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Start a round and have some actions
    table.mark_player_acted(players[0], is_raise=True)
    table.mark_player_acted(players[1])

    # Reset in middle of round
    table.reset_action_tracking()

    # Verify state
    assert players[0] in table.needs_to_act  # Active player should need to act
    assert len(table.acted_since_last_raise) == 0  # Previous actions should be cleared
    assert table.get_next_player() == players[0]  # Should start from beginning


def test_reset_action_tracking_with_zero_active_players():
    """Test resetting action tracking when no players are active.
    
    Assumptions:
    - Reset should work even with no active players
    - needs_to_act should be empty when no active players exist
    - acted_since_last_raise should be cleared
    """
    players = [Player("Alice", 1000), Player("Bob", 1000), Player("Charlie", 1000)]
    table = Table(players)

    # Make all players inactive
    for player in players:
        player.folded = True

    table.reset_action_tracking()

    assert len(table.needs_to_act) == 0
    assert len(table.acted_since_last_raise) == 0


def test_reset_action_tracking_preserves_player_states():
    """Test that reset_action_tracking doesn't modify player states.
    
    Assumptions:
    - Player states (folded, all-in, chips) should not change
    - Only tracking sets should be affected
    - Previous player states should be preserved exactly
    """
    players = [
        Player("Alice", 1000),  # Normal player
        Player("Bob", 0),       # Zero chips
        Player("Charlie", 500)  # Will be all-in
    ]
    table = Table(players)

    # Set up some player states
    players[2].is_all_in = True
    players[2].chips = 0

    # Store initial states
    initial_states = [(p.folded, p.is_all_in, p.chips) for p in players]

    table.reset_action_tracking()

    # Verify states unchanged
    final_states = [(p.folded, p.is_all_in, p.chips) for p in players]
    assert initial_states == final_states
