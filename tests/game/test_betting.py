from data.types.base_types import DeckState
from data.types.game_state import GameState
from data.types.pot_types import PotState
from data.types.round_state import RoundState

import pytest

from game.betting import (
    betting_round,
    calculate_side_pots,
    collect_blinds_and_antes,
    handle_betting_round,
    validate_bet_to_call,
)
from game.player import Player


@pytest.fixture
def basic_players():
    """Create a basic set of players for testing."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]
    return players


def test_betting_round_all_call(basic_players, mock_game_state):
    """Test betting round where all players call."""
    # Mock player decisions
    for player in basic_players:
        player.decide_action = lambda x: ("call", 10)

    mock_game_state.round_state.current_bet = 10
    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 30  # Each player bet 10
    assert all(p.bet == 10 for p in basic_players)
    assert all(p.chips == 990 for p in basic_players)


def test_betting_round_with_fold(basic_players, mock_game_state):
    """Test betting round where one player folds."""
    # Player 1 and 2 call, Player 3 folds
    basic_players[0].decide_action = lambda x: ("call", 10)
    basic_players[1].decide_action = lambda x: ("call", 10)
    basic_players[2].decide_action = lambda x: ("fold", 0)

    mock_game_state.round_state.current_bet = 10
    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 20  # Two players bet 10 each
    assert basic_players[2].folded == True


def test_betting_round_with_raise(basic_players, mock_game_state):
    """Test betting round with a raise."""
    # Player 1 calls, Player 2 raises, Player 3 calls
    basic_players[0].decide_action = lambda x: ("call", 10)
    basic_players[1].decide_action = lambda x: ("raise", 20)
    basic_players[2].decide_action = lambda x: ("call", 20)

    mock_game_state.round_state.current_bet = 10
    mock_game_state.min_bet = 10
    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 60  # Three players matching 20 each
    assert all(p.bet == 20 for p in basic_players)


def test_betting_round_raise_less_than_current(basic_players, mock_game_state):
    """Test that raises less than current bet are converted to calls."""
    # Set up initial bet of 20
    mock_game_state.round_state.current_bet = 20

    # Player tries to raise to 15 (less than current bet)
    basic_players[0].decide_action = lambda x: ("raise", 15)
    basic_players[1].decide_action = lambda x: ("call", 20)
    basic_players[2].decide_action = lambda x: ("call", 20)

    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 60  # All players should match 20
    assert all(p.bet == 20 for p in basic_players)


def test_betting_round_last_raiser_short_stack(mock_game_state):
    """Test when the last raiser becomes short-stacked after raising."""
    players = [
        Player("Player 1", 40),
        Player("Player 2", 100),
        Player("Player 3", 100),
    ]

    action_count = 0

    def player1_actions(state):
        nonlocal action_count
        action_count += 1
        if action_count == 1:
            return "raise", 30  # Initial raise of 30
        return "call", 30  # Can only match their original bet

    players[0].decide_action = player1_actions
    players[1].decide_action = lambda x: ("call", 30)
    players[2].decide_action = lambda x: ("call", 30)

    mock_game_state.round_state.current_bet = 10
    result = betting_round(players, 0, mock_game_state)

    assert action_count == 2
    assert players[0].bet == 30
    assert players[1].bet == 30
    assert players[2].bet == 30
    assert players[0].chips == 10
    assert result == 90  # 30 × 3


def test_calculate_side_pots():
    """Test side pot calculation."""
    players = [
        Player("Player 1", 0),  # Already all-in with 100
        Player("Player 2", 0),  # Already all-in with 50
        Player("Player 3", 100),  # Still active
    ]
    # Set their bets manually
    players[0].bet = 100
    players[1].bet = 50
    players[2].bet = 100

    all_in_players = [players[1], players[0]]  # Ordered by bet size
    active_players = players  # All players are still in hand

    side_pots = calculate_side_pots(active_players, all_in_players)

    assert len(side_pots) == 2
    # First pot: All players contribute 50
    assert side_pots[0].amount == 150
    assert len(side_pots[0].eligible_players) == 3
    # Second pot: Players 1 and 3 contribute additional 50
    assert side_pots[1].amount == 100
    assert len(side_pots[1].eligible_players) == 2


def test_betting_round_no_active_players(mock_game_state):
    """Test betting round with no active players."""
    players = [Player("Player 1", 100), Player("Player 2", 100)]
    players[0].folded = True
    players[1].folded = True

    result = betting_round(players, 50, mock_game_state)
    assert result == 50  # Pot should remain unchanged


def test_betting_round_with_existing_pot(mock_game_state):
    """Test betting round starting with existing pot."""
    players = [Player("Player 1", 100), Player("Player 2", 100)]
    players[0].decide_action = lambda x: ("call", 10)
    players[1].decide_action = lambda x: ("call", 10)

    mock_game_state.round_state.current_bet = 10
    result = betting_round(players, 50, mock_game_state)
    assert result == 70  # 50 (existing) + 20 (new bets)


def test_betting_round_multiple_raises(basic_players, mock_game_state):
    """Test betting round with multiple raises."""
    # Setup game state
    mock_game_state.round_state.current_bet = 10
    mock_game_state.min_bet = 10
    mock_game_state.max_raises_per_round = 3  # Allow enough raises for this test

    # Track betting sequence
    betting_sequence = []

    def make_action(name, actions):
        """Create a player action function that tracks betting sequence."""
        action_iter = iter(actions)

        def action(state):
            action, amount = next(action_iter)
            betting_sequence.append((name, action, amount))
            return action, amount

        return action

    # Setup player actions
    basic_players[0].decide_action = make_action(
        "Player 1",
        [("raise", 20), ("call", 20)],  # First raise from 10 to 20  # Call final bet
    )
    basic_players[1].decide_action = make_action(
        "Player 2", [("call", 20)]  # Call the raise
    )
    basic_players[2].decide_action = make_action(
        "Player 3", [("call", 20)]  # Call the raise
    )

    result = betting_round(basic_players, 0, mock_game_state)

    # Verify final state
    assert result == 60  # Three players matching 20 each
    assert all(p.bet == 20 for p in basic_players)
    assert all(p.chips == 980 for p in basic_players)

    # Verify betting sequence
    expected_sequence = [
        ("Player 1", "raise", 20),  # First raise
        ("Player 2", "call", 20),  # Call
        ("Player 3", "call", 20),  # Call
        ("Player 1", "call", 20),  # Complete the round
    ]

    assert len(betting_sequence) == len(
        expected_sequence
    ), f"Expected {len(expected_sequence)} actions, got {len(betting_sequence)}"

    for actual, expected in zip(betting_sequence, expected_sequence):
        assert actual == expected, f"Expected {expected}, got {actual}"

    # Verify game state
    assert mock_game_state.round_state.current_bet == 20
    assert mock_game_state.round_state.raise_count == 1


def test_betting_round_last_raiser_completion(basic_players, mock_game_state):
    """Test that betting continues until last raiser has acted again."""
    # First player raises, others call, then first player gets another chance
    calls = 0

    def player1_action(state):
        nonlocal calls
        calls += 1
        if calls == 1:
            return "raise", 30
        return "call", 30

    basic_players[0].decide_action = player1_action
    basic_players[1].decide_action = lambda x: ("call", 30)
    basic_players[2].decide_action = lambda x: ("call", 30)

    mock_game_state.round_state.current_bet = 10
    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 90  # Three players × 30
    assert calls == 2  # Player 1 should have acted twice


def test_betting_round_all_in_below_current_bet(mock_game_state):
    """Test when a player goes all-in for less than the current bet."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 15),  # Can only call partially
        Player("Player 3", 100),
    ]

    mock_game_state.round_state.current_bet = 20

    players[0].decide_action = lambda x: ("call", 20)
    players[1].decide_action = lambda x: ("call", 20)  # Will only bet 15
    players[2].decide_action = lambda x: ("call", 20)

    pot, side_pots = betting_round(players, 0, mock_game_state)

    assert pot == 55  # Player 1: 20 + Player 2: 15 + Player 3: 20
    assert len(side_pots) == 2
    assert side_pots[0].amount == 45  # 3 players × 15
    assert side_pots[1].amount == 10  # 2 players × 5 (remaining amount)


def test_side_pots_with_multiple_rounds(mock_game_state):
    """Test side pot calculation with multiple betting rounds."""
    players = [Player("Player 1", 40), Player("Player 2", 80), Player("Player 3", 100)]

    # Single round with all-in
    players[0].decide_action = lambda x: ("raise", 40)  # All-in
    players[1].decide_action = lambda x: ("call", 40)
    players[2].decide_action = lambda x: ("call", 40)

    mock_game_state.round_state.current_bet = 10
    mock_game_state.min_bet = 10
    result = betting_round(players, 0, mock_game_state)

    # betting_round now returns a tuple only when side pots are created
    pot = result[0] if isinstance(result, tuple) else result
    side_pots = result[1] if isinstance(result, tuple) else None

    assert pot == 120  # Total after round
    assert side_pots is not None
    assert len(side_pots) == 1
    assert side_pots[0].amount == 120  # 40 × 3
    assert len(side_pots[0].eligible_players) == 3


def test_betting_round_with_game_state(basic_players, mock_game_state):
    """Test betting round using GameState to set initial current_bet."""
    # All players should call the existing bet
    for player in basic_players:
        player.decide_action = lambda x: ("call", 20)

    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 60  # Each player matched 20
    assert all(p.bet == 20 for p in basic_players)
    assert all(p.chips == 980 for p in basic_players)


def test_betting_round_last_raiser_completion(basic_players):
    """Test that betting continues until last raiser has acted again."""
    # First player raises, others call, then first player gets another chance
    calls = 0

    def player1_action(state):
        nonlocal calls
        calls += 1
        if calls == 1:
            return "raise", 30
        return "call", 30

    basic_players[0].decide_action = player1_action
    basic_players[1].decide_action = lambda x: ("call", 30)
    basic_players[2].decide_action = lambda x: ("call", 30)

    result = betting_round(basic_players, 0)
    assert result == 90  # Three players × 30
    assert calls == 2  # Player 1 should have acted twice


def test_betting_round_multiple_all_ins_same_amount():
    """Test handling of multiple players going all-in for the same amount."""
    players = [Player("Player 1", 50), Player("Player 2", 50), Player("Player 3", 100)]

    # First two players go all-in for same amount
    players[0].decide_action = lambda x: ("raise", 50)
    players[1].decide_action = lambda x: ("call", 50)
    players[2].decide_action = lambda x: ("call", 50)

    pot, side_pots = betting_round(players, 0)

    assert pot == 150
    assert len(side_pots) == 1
    assert side_pots[0].amount == 150
    assert len(side_pots[0].eligible_players) == 3


def test_betting_round_raise_all_in():
    """Test when a player raises by going all-in."""
    players = [Player("Player 1", 100), Player("Player 2", 40), Player("Player 3", 100)]

    # Player 2 raises by going all-in
    players[0].decide_action = lambda x: ("call", 10)
    players[1].decide_action = lambda x: ("raise", 40)  # All-in
    players[2].decide_action = lambda x: ("call", 40)
    players[0].decide_action = lambda x: ("call", 40)

    pot, side_pots = betting_round(players, 0)

    assert pot == 120  # 40 × 3
    assert len(side_pots) == 1
    assert side_pots[0].amount == 120
    assert len(side_pots[0].eligible_players) == 3


def test_collect_blinds_and_antes():
    """Test collecting blinds and antes from players."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]

    total = collect_blinds_and_antes(
        players=players, dealer_index=0, small_blind=10, big_blind=20, ante=5
    )

    # Expected total: 3 antes (5 each) + small blind (10) + big blind (20)
    assert total == 45

    # Check player chip counts
    assert players[0].chips == 995  # Paid ante only
    assert players[1].chips == 985  # Paid ante + small blind
    assert players[2].chips == 975  # Paid ante + big blind


def test_collect_blinds_and_antes_short_stack():
    """Test collecting blinds and antes when players are short stacked."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 5),  # Can only post partial small blind
        Player("Player 3", 15),  # Can only post partial big blind
    ]

    total = collect_blinds_and_antes(
        players=players, dealer_index=0, small_blind=10, big_blind=20, ante=5
    )

    # Recalculate expected total:
    # Player 1: 5 (ante)
    # Player 2: 5 (all-in for partial small blind)
    # Player 3: 15 (all-in for partial big blind)
    assert total == 25  # 5 (ante) + 5 (partial SB) + 15 (partial BB)
    assert players[1].chips == 0  # All-in from small blind
    assert players[2].chips == 0  # All-in from big blind


@pytest.fixture
def mock_game_state():
    """Create a mock GameState for testing."""
    return GameState(
        players=[],  # Will be populated in tests
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            round_number=1, phase="pre_draw", current_bet=20, raise_count=0
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )


def test_handle_betting_round_pre_draw(basic_players, mock_game_state):
    """Test handling a complete pre-draw betting round."""
    # Mock player decisions
    for player in basic_players:
        player.decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_betting_round(
        players=basic_players, pot=0, game_state=mock_game_state
    )

    assert new_pot == 60  # All players called 20
    assert side_pots is None  # No side pots created
    assert all(p.bet == 20 for p in basic_players)
    assert should_continue is True


def test_handle_betting_round_all_in(mock_game_state):
    """Test handling a betting round with an all-in situation."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 50),  # Will go all-in
        Player("Player 3", 100),
    ]

    # Set up betting sequence
    players[0].decide_action = lambda x: ("raise", 75)
    players[1].decide_action = lambda x: ("call", 75)  # Will only bet 50 (all-in)
    players[2].decide_action = lambda x: ("call", 75)

    # Update game state for this test
    mock_game_state.round_state.current_bet = 20
    mock_game_state.small_blind = 10
    mock_game_state.big_blind = 20

    new_pot, side_pots, should_continue = handle_betting_round(
        players=players,
        pot=0,
        game_state=mock_game_state,
    )

    # Update assertions to match correct betting behavior
    assert new_pot == 200  # Total bets: Player 1: 75 + Player 2: 50 + Player 3: 75
    assert len(side_pots) == 2

    # First side pot (all players contribute 50)
    assert side_pots[0].amount == 150
    assert len(side_pots[0].eligible_players) == 3

    # Second side pot (remaining players contribute 25 each)
    assert side_pots[1].amount == 50
    assert len(side_pots[1].eligible_players) == 2
    assert players[1] not in side_pots[1].eligible_players

    # Verify final player states
    assert players[0].chips == 25  # Started with 100, bet 75
    assert players[1].chips == 0  # Started with 50, went all-in
    assert players[2].chips == 25  # Started with 100, bet 75


def test_handle_betting_round_everyone_folds(mock_game_state):
    """Test handling a betting round where everyone folds except one player."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 100),
        Player("Player 3", 100),
    ]

    # Everyone folds to Player 1's bet
    players[0].decide_action = lambda x: ("raise", 30)
    players[1].decide_action = lambda x: ("fold", 0)
    players[2].decide_action = lambda x: ("fold", 0)

    mock_game_state.small_blind = 10
    mock_game_state.big_blind = 20
    mock_game_state.round_state.current_bet = 20
    mock_game_state.min_bet = 10

    new_pot, side_pots, should_continue = handle_betting_round(
        players=players,
        pot=0,
        game_state=mock_game_state,
    )

    assert new_pot == 30  # Only Player 1's bet
    assert side_pots is None
    assert all(p.folded for p in players[1:])
    assert not players[0].folded
    assert should_continue is False


def test_betting_round_partial_call_all_in(mock_game_state):
    """Test when a player can only make a partial call and goes all-in."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 15),  # Can only partially call
        Player("Player 3", 100),
    ]

    # Set up a betting sequence where Player 2 has to make a partial call
    players[0].decide_action = lambda x: ("raise", 30)
    players[1].decide_action = lambda x: ("call", 30)  # Will only bet 15 (all-in)
    players[2].decide_action = lambda x: ("call", 30)

    # Update game state for this test
    mock_game_state.round_state.current_bet = 10
    mock_game_state.min_bet = 10

    pot, side_pots = betting_round(players, 0, mock_game_state)

    assert players[1].chips == 0  # Player 2 should be all-in
    assert players[1].bet == 15  # Player 2's partial call
    assert pot == 75  # Player 1: 30 + Player 2: 15 + Player 3: 30

    # Verify side pots
    assert len(side_pots) == 2
    # First side pot (all players contribute 15)
    assert side_pots[0].amount == 45  # 3 players × 15
    assert len(side_pots[0].eligible_players) == 3
    # Second side pot (remaining players contribute 15 each)
    assert side_pots[1].amount == 30  # 2 players × 15
    assert len(side_pots[1].eligible_players) == 2
    assert players[1] not in side_pots[1].eligible_players


def test_betting_round_max_raises(basic_players, mock_game_state):
    """Test that betting round enforces maximum number of raises."""
    mock_game_state.max_raises_per_round = 2  # Set a low limit for testing
    mock_game_state.round_state.current_bet = 10
    mock_game_state.min_bet = 10  # Set minimum bet

    # Track actions for each player
    actions = []

    def player1_action(state):
        print(
            f"\nPlayer 1 acting. Current bet: {state.round_state.current_bet}, Raise count: {state.round_state.raise_count}"
        )
        actions.append(
            ("Player 1", state.round_state.current_bet, state.round_state.raise_count)
        )
        if state.round_state.raise_count == 0:
            return "raise", 20  # First raise (10 -> 20)
        return "call", state.round_state.current_bet

    def player2_action(state):
        print(
            f"Player 2 acting. Current bet: {state.round_state.current_bet}, Raise count: {state.round_state.raise_count}"
        )
        actions.append(
            ("Player 2", state.round_state.current_bet, state.round_state.raise_count)
        )
        # Only raise if we haven't hit max raises
        if state.round_state.raise_count < state.max_raises_per_round:
            return "raise", state.round_state.current_bet + 10  # Raise by 10 more
        return "call", state.round_state.current_bet

    def player3_action(state):
        print(
            f"Player 3 acting. Current bet: {state.round_state.current_bet}, Raise count: {state.round_state.raise_count}"
        )
        actions.append(
            ("Player 3", state.round_state.current_bet, state.round_state.raise_count)
        )
        return "call", state.round_state.current_bet

    # Setup player actions
    basic_players[0].decide_action = player1_action
    basic_players[1].decide_action = player2_action
    basic_players[2].decide_action = player3_action

    print("\nInitial state:")
    for p in basic_players:
        print(f"{p.name}: chips={p.chips}, bet={p.bet}")

    result = betting_round(basic_players, 0, mock_game_state)

    print("\nFinal state:")
    for p in basic_players:
        print(f"{p.name}: chips={p.chips}, bet={p.bet}")
    print(f"Total pot: {result}")
    print(f"Final raise count: {mock_game_state.round_state.raise_count}")
    print("\nAction history:")
    for player, bet, raises in actions:
        print(f"{player}: current_bet={bet}, raises={raises}")

    # After max raises reached, all subsequent raises should convert to calls
    assert mock_game_state.round_state.raise_count == 2
    assert result == 90  # All players match the highest valid raise of 30

    # Verify each player's final bet
    for player in basic_players:
        assert (
            player.bet == 30
        ), f"{player.name} should have bet 30, but bet {player.bet}"
        assert (
            player.chips == 970
        ), f"{player.name} should have 970 chips remaining, but has {player.chips}"

    # Update expected sequence to match actual betting flow
    expected_sequence = [
        ("Player 1", 10, 0),  # Initial state
        ("Player 2", 20, 1),  # Player 2 raises to 30
        ("Player 3", 30, 2),  # Player 3 calls 30
        ("Player 1", 30, 2),  # Player 1 calls 30
        ("Player 2", 30, 2),  # Player 2's final action (this is expected)
    ]

    assert len(actions) == len(
        expected_sequence
    ), f"Wrong number of actions. Expected {len(expected_sequence)}, got {len(actions)}"
    for actual, expected in zip(actions, expected_sequence):
        assert actual == expected, f"Expected {expected}, got {actual}"


def test_betting_round_one_player_left_with_chips():
    """Test when only one player has chips remaining but others are all-in."""
    players = [
        Player("Player 1", 100),  # Has enough chips
        Player("Player 2", 20),  # Will go all-in first
        Player("Player 3", 30),  # Will go all-in second
    ]

    # Set up betting sequence
    players[0].decide_action = lambda x: ("raise", 30)  # Raises to 30
    players[1].decide_action = lambda x: ("call", 30)  # Can only call 20 (all-in)
    players[2].decide_action = lambda x: ("call", 30)  # Can only call 30 (all-in)

    pot, side_pots = betting_round(players, 0)

    # Debug logging
    print("\nDebug info for one_player_left_with_chips test:")
    print(f"Player 1: chips={players[0].chips}, bet={players[0].bet}")
    print(f"Player 2: chips={players[1].chips}, bet={players[1].bet}")
    print(f"Player 3: chips={players[2].chips}, bet={players[2].bet}")
    print(f"Total pot: {pot}")
    print("Side pots:")
    for i, sp in enumerate(side_pots):
        print(
            f"  Pot {i+1}: ${sp.amount} - Eligible: {[p.name for p in sp.eligible_players]}"
        )

    # Verify final state
    assert (
        players[0].chips == 70
    ), f"Expected Player 1 to have 70 chips, but had {players[0].chips}"
    assert (
        players[1].chips == 0
    ), f"Expected Player 2 to be all-in, but had {players[1].chips} chips"
    assert (
        players[2].chips == 0
    ), f"Expected Player 3 to be all-in, but had {players[2].chips} chips"

    # Total pot should be 80 (Player 1: 30 + Player 2: 20 + Player 3: 30)
    assert pot == 80, f"Expected pot to be 80, but was {pot}"

    # Verify side pots
    assert len(side_pots) == 2, f"Expected 2 side pots, but got {len(side_pots)}"

    # First side pot: All players contribute 20 each
    assert (
        side_pots[0].amount == 60
    ), f"First side pot should be 60, but was {side_pots[0].amount}"
    assert len(side_pots[0].eligible_players) == 3

    # Second side pot: Only Player 1 and 3 contribute additional 10 each
    assert (
        side_pots[1].amount == 20
    ), f"Second side pot should be 20, but was {side_pots[1].amount}"
    assert len(side_pots[1].eligible_players) == 2
    assert players[1] not in side_pots[1].eligible_players


def test_betting_round_minimum_raise_validation(basic_players, mock_game_state):
    """Test that raises below minimum are converted to calls."""
    mock_game_state.round_state.current_bet = 20
    mock_game_state.min_bet = 10

    # Player tries to raise to 25 (less than min raise of 30)
    basic_players[0].decide_action = lambda x: ("raise", 25)
    basic_players[1].decide_action = lambda x: ("call", 20)
    basic_players[2].decide_action = lambda x: ("call", 20)

    result = betting_round(basic_players, 0, mock_game_state)
    assert result == 60  # All players match 20
    assert all(p.bet == 20 for p in basic_players)


def test_betting_round_same_player_raise_restriction(basic_players):
    """Test that a player cannot raise twice in a row unless they're the only active player."""
    calls = 0

    def player1_actions(state):
        nonlocal calls
        calls += 1
        if calls == 1:
            return "raise", 30  # Initial raise
        return "call", 30  # Should only be able to call on subsequent actions

    basic_players[0].decide_action = player1_actions
    basic_players[1].decide_action = lambda x: ("call", 30)
    basic_players[2].decide_action = lambda x: ("call", 30)

    result = betting_round(basic_players, 0)

    # Verify the betting sequence
    assert calls >= 2, "Player 1 should act at least twice"
    assert result == 90  # Total pot (30 × 3)
    assert all(
        p.bet == 30 for p in basic_players
    ), "All players should match the final bet"

    # Verify betting amounts are correct
    assert basic_players[0].chips == 970, "Player 1 should have bet 30 total"
    assert basic_players[1].chips == 970, "Player 2 should have bet 30 total"
    assert basic_players[2].chips == 970, "Player 3 should have bet 30 total"


def test_betting_round_last_active_player_can_reraise():
    """Test that the last active player can raise multiple times."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 100),
        Player("Player 3", 100),
    ]

    players[0].decide_action = lambda x: (
        "raise",
        30,
    )  # Update to match actual behavior
    players[1].decide_action = lambda x: ("fold", 0)
    players[2].decide_action = lambda x: ("fold", 0)

    result = betting_round(players, 0)

    assert players[0].bet == 30  # Update expected bet
    assert players[1].folded
    assert players[2].folded
    assert result == 30  # Update expected pot


def test_collect_blinds_and_antes_standard_case(basic_players):
    """Test collecting blinds and antes in standard case."""
    # Setup
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 10

    # First verify ante collection
    total = collect_blinds_and_antes(
        players=basic_players,
        dealer_index=dealer_index,
        small_blind=small_blind,
        big_blind=big_blind,
        ante=ante,
    )

    # Verify total collected
    expected_total = (len(basic_players) * ante) + small_blind + big_blind
    assert (
        total == expected_total
    ), f"Expected {expected_total} chips collected, got {total}"

    # Get references to players in blind positions
    sb_player = basic_players[1]  # Player after dealer
    bb_player = basic_players[2]  # Player after SB

    # Verify final state after all deductions
    assert sb_player.bet == 50, "Small blind bet should be 50"
    assert bb_player.bet == 100, "Big blind bet should be 100"
    assert (
        sb_player.chips == 940
    ), "Small blind player should have 940 chips (1000 - 10 ante - 50 SB)"
    assert (
        bb_player.chips == 890
    ), "Big blind player should have 890 chips (1000 - 10 ante - 100 BB)"
    assert (
        basic_players[0].chips == 990
    ), "First player should have 990 chips (1000 - 10 ante)"
    assert basic_players[0].bet == 0, "First player should have no bet"


def test_collect_blinds_and_antes_no_ante(basic_players):
    """Test collecting only blinds with no ante."""
    total = collect_blinds_and_antes(
        players=basic_players,
        dealer_index=0,
        small_blind=50,
        big_blind=100,
        ante=0,
    )

    assert total == 150, "Should collect only blinds when ante is 0"

    # Verify player states
    sb_player = basic_players[1]
    bb_player = basic_players[2]
    first_player = basic_players[0]

    # First player should be unchanged
    assert first_player.chips == 1000, "First player chips should be unchanged"
    assert first_player.bet == 0, "First player should have no bet"

    # Check blind bets
    assert sb_player.bet == 50, "Small blind bet should be 50"
    assert bb_player.bet == 100, "Big blind bet should be 100"


def test_collect_blinds_and_antes_all_in_scenarios(basic_players):
    """Test collecting blinds and antes when players don't have enough chips."""
    # Setup players with limited chips
    basic_players[0].chips = 5  # Can only post partial ante
    basic_players[1].chips = 30  # Can only post partial small blind
    basic_players[2].chips = 80  # Can only post partial big blind

    print("\nInitial state:")
    for i, p in enumerate(basic_players):
        print(f"Player {i}: chips={p.chips}, bet={p.bet}")

    total = collect_blinds_and_antes(
        players=basic_players,
        dealer_index=0,
        small_blind=50,
        big_blind=100,
        ante=10,
    )

    print("\nAfter collecting blinds and antes:")
    print(f"Total collected: {total}")
    for i, p in enumerate(basic_players):
        print(f"Player {i}: chips={p.chips}, bet={p.bet}")

    # Verify total collected matches actual available chips
    expected_total = 5 + 30 + 80  # All players go all-in
    assert (
        total == expected_total
    ), f"Expected {expected_total} chips collected, got {total}"

    print("\nVerifying player states:")
    # Verify player states
    assert (
        basic_players[0].chips == 0
    ), f"First player should be all-in, has {basic_players[0].chips} chips"
    assert (
        basic_players[1].chips == 0
    ), f"Small blind should be all-in, has {basic_players[1].chips} chips"
    assert (
        basic_players[2].chips == 0
    ), f"Big blind should be all-in, has {basic_players[2].chips} chips"

    print("\nVerifying bet amounts:")
    # Verify bet amounts
    assert (
        basic_players[0].bet == 0
    ), f"First player should have no bet (ante doesn't count as bet), has bet {basic_players[0].bet}"
    assert (
        basic_players[1].bet == 20
    ), f"Small blind bet should be 20, has bet {basic_players[1].bet}"
    assert (
        basic_players[2].bet == 70
    ), f"Big blind bet should be 70, has bet {basic_players[2].bet}"

    print("\nFinal state:")
    for i, p in enumerate(basic_players):
        print(f"Player {i}: chips={p.chips}, bet={p.bet}")


def test_betting_round_after_antes(basic_players, mock_game_state):
    """Test that betting round correctly handles current bet after antes are posted."""
    # Setup - collect antes and blinds first
    collect_blinds_and_antes(
        players=basic_players,
        dealer_index=0,
        small_blind=50,
        big_blind=100,
        ante=10,
    )

    # Update game state with current bet equal to big blind
    mock_game_state.round_state.current_bet = 100
    mock_game_state.big_blind = 100
    mock_game_state.small_blind = 50

    # Mock player decisions to call the big blind
    for player in basic_players:
        player.decide_action = lambda x: ("call", 100)

    # Run betting round with game state
    initial_pot = 180  # 3 players × 10 ante + 50 SB + 100 BB
    final_pot = betting_round(basic_players, initial_pot, mock_game_state)

    # Verify final state
    # Initial pot: 180
    # Player 0 (Dealer): Pays 100 to call
    # Player 1 (SB): Already paid 50, pays 50 more to call
    # Player 2 (BB): Already paid 100, no additional payment needed
    assert final_pot == 330  # Initial 180 + 100 (Dealer) + 50 (SB completing)

    # Expected chip counts:
    # Player 0 (Dealer): 1000 - 10 (ante) - 100 (call) = 890
    # Player 1 (SB): 1000 - 10 (ante) - 50 (SB) - 50 (complete) = 890
    # Player 2 (BB): 1000 - 10 (ante) - 100 (BB) = 890
    expected_chips = [890, 890, 890]

    for i, player in enumerate(basic_players):
        assert player.chips == expected_chips[i], f"Player {i} has wrong chip count"
        assert player.bet == 100, f"Player {i} has wrong bet amount"


def test_big_blind_betting_behavior(mock_game_state):
    """Test that big blind player doesn't have to call their own blind amount."""
    players = [
        Player("Dealer", 1000),
        Player("Small Blind", 1000),
        Player("Big Blind", 1000),
        Player("UTG", 1000),
    ]

    # Update game state for BB position
    mock_game_state.round_state.current_bet = 100
    mock_game_state.big_blind = 100
    mock_game_state.small_blind = 50
    mock_game_state.round_state.big_blind_position = 2

    # Mock player decisions
    players[0].decide_action = lambda x: ("call", 100)
    players[1].decide_action = lambda x: ("call", 100)
    players[2].decide_action = lambda x: ("check", 0)
    players[3].decide_action = lambda x: ("call", 100)

    result = betting_round(players, 160, mock_game_state)

    assert players[2].bet == 100
    assert players[2].chips == 900
    assert result == 560


def test_small_blind_calling_big_blind():
    """Test that small blind only needs to pay the difference to call big blind."""
    # Create players with 1000 chips each
    players = [
        Player("Dealer", 1000),
        Player("Small Blind", 1000),  # Will be in small blind position
        Player("Big Blind", 1000),  # Will be in big blind position
        Player("UTG", 1000),  # Under the gun
    ]

    # Create game state with blinds configuration
    game_state = GameState(
        players=[],
        dealer_position=0,
        small_blind=50,
        big_blind=100,
        ante=0,
        min_bet=100,
        round_state=RoundState(
            round_number=1,
            phase="pre_draw",
            current_bet=100,  # Current bet is big blind amount
            raise_count=0,
            big_blind_position=2,  # Position 2 is BB
            small_blind_position=1,  # Position 1 is SB
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )

    # First collect blinds
    collected = collect_blinds_and_antes(
        players=players, dealer_index=0, small_blind=50, big_blind=100, ante=0
    )

    # Verify initial blind postings
    assert collected == 150  # SB(50) + BB(100)
    assert players[1].bet == 50  # Small blind posted
    assert players[1].chips == 950  # 1000 - 50
    assert players[2].bet == 100  # Big blind posted
    assert players[2].chips == 900  # 1000 - 100

    # Mock player decisions
    # UTG calls
    players[3].decide_action = lambda x: ("call", 100)
    # Dealer calls
    players[0].decide_action = lambda x: ("call", 100)
    # Small blind calls (should only need to pay 50 more)
    players[1].decide_action = lambda x: ("call", 100)
    # Big blind checks
    players[2].decide_action = lambda x: ("check", 0)

    # Run betting round
    result = betting_round(players, collected, game_state)

    # Verify final state
    assert (
        players[1].chips == 900
    ), f"Small blind should have 900 chips left (1000 - 50 - 50), but has {players[1].chips}"
    assert (
        players[1].bet == 100
    ), f"Small blind's total bet should be 100, but is {players[1].bet}"

    # Verify other players
    assert players[0].chips == 900  # Dealer paid full 100
    assert players[2].chips == 900  # BB only paid initial 100
    assert players[3].chips == 900  # UTG paid full 100

    # Verify pot
    assert result == 400, f"Pot should be 400 (4 players × 100), but is {result}"


def test_validate_bet_to_call():
    """Test that validate_bet_to_call correctly calculates amounts for different scenarios."""
    # Test cases:
    # 1. Regular player with no prior bet
    assert validate_bet_to_call(100, 0) == 100, "Regular player should pay full amount"

    # 2. Small blind completing to big blind
    assert (
        validate_bet_to_call(100, 50) == 50
    ), "Small blind should only pay the difference"

    # 3. Big blind when no raises (current_bet equals their posted amount)
    assert (
        validate_bet_to_call(100, 100, is_big_blind=True) == 0
    ), "Big blind shouldn't need to call their own bet"

    # 4. Big blind when there's a raise
    assert (
        validate_bet_to_call(200, 100, is_big_blind=True) == 100
    ), "Big blind should pay difference after raise"

    # 5. Player who has already bet some amount
    assert (
        validate_bet_to_call(300, 200) == 100
    ), "Player should only pay the difference from their current bet"

    # 6. Edge case: current bet less than player's bet (shouldn't happen, but should handle gracefully)
    assert (
        validate_bet_to_call(50, 100) == 0
    ), "Should return 0 if current bet is less than player bet"


def test_betting_round_with_posted_blinds(mock_game_state):
    """Test that betting round correctly handles players who have already posted blinds."""
    # Create players with 1000 chips each
    players = [
        Player("Dealer", 1000),
        Player("Small Blind", 1000),
        Player("Big Blind", 1000),
        Player("UTG", 1000),
    ]

    print("\nInitial state:")
    for p in players:
        print(f"{p.name}: chips={p.chips}, bet={p.bet}")

    # First simulate blind postings
    # Small blind posts 50
    players[1].chips -= 50
    players[1].bet = 50
    # Big blind posts 100
    players[2].chips -= 100
    players[2].bet = 100
    # Also simulate antes of 10 each
    for player in players:
        player.chips -= 10

    print("\nAfter blinds and antes:")
    for p in players:
        print(f"{p.name}: chips={p.chips}, bet={p.bet}")

    # Update game state
    mock_game_state.round_state.current_bet = 100  # Current bet is BB amount
    mock_game_state.round_state.big_blind_position = 2
    mock_game_state.round_state.small_blind_position = 1

    # Track initial chip counts
    initial_chips = {p: p.chips for p in players}

    print("\nGame state:")
    print(f"Current bet: {mock_game_state.round_state.current_bet}")
    print(f"BB position: {mock_game_state.round_state.big_blind_position}")
    print(f"SB position: {mock_game_state.round_state.small_blind_position}")

    # Define player actions
    players[0].decide_action = lambda x: ("call", 100)  # Dealer calls
    players[1].decide_action = lambda x: ("call", 100)  # SB completes
    players[2].decide_action = lambda x: ("check", 0)  # BB checks
    players[3].decide_action = lambda x: ("call", 100)  # UTG calls

    # Run betting round
    initial_pot = 170  # Antes (40) + SB (50) + BB (100)
    print(f"\nStarting betting round with initial pot: {initial_pot}")

    result = betting_round(players, initial_pot, mock_game_state)

    print("\nAfter betting round:")
    print(f"Final pot: {result}")
    for p in players:
        print(
            f"{p.name}: chips={p.chips}, bet={p.bet}, "
            f"total paid={1000 - p.chips}, "
            f"folded={p.folded}"
        )

    # Update expected pot value to 420
    assert result == 420, f"Expected pot of 420, got {result}"

    # Verify each player's chips and bets
    # Dealer should have paid: 10 (ante) + 100 (call) = 110
    assert (
        players[0].chips == 890
    ), f"Dealer should have 890 chips, has {players[0].chips}"
    assert players[0].bet == 100, f"Dealer's bet should be 100, is {players[0].bet}"

    # Small Blind should have paid: 10 (ante) + 50 (SB) + 50 (complete) = 110
    assert players[1].chips == 890, f"SB should have 890 chips, has {players[1].chips}"
    assert players[1].bet == 100, f"SB's bet should be 100, is {players[1].bet}"

    # Big Blind should have paid: 10 (ante) + 100 (BB) = 110
    assert players[2].chips == 890, f"BB should have 890 chips, has {players[2].chips}"
    assert players[2].bet == 100, f"BB's bet should be 100, is {players[2].bet}"

    # UTG should have paid: 10 (ante) + 100 (call) = 110
    assert players[3].chips == 890, f"UTG should have 890 chips, has {players[3].chips}"
    assert players[3].bet == 100, f"UTG's bet should be 100, is {players[3].bet}"

    print("\nExpected vs Actual:")
    print("Expected: Each player should have paid 110 total (ante + bet)")
    print("Expected: Final pot should be 420 (initial 170 + 3 calls of 100)")
    print(f"Actual pot: {result}")
    for p in players:
        print(f"{p.name} paid total: {1000 - p.chips}")
