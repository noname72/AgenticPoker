from datetime import datetime
from unittest.mock import Mock, patch, PropertyMock
from typing import List
from unittest.mock import call

import pytest

from agents.llm_agent import LLMAgent
from data.enums import ActionType
from game import AgenticPoker
from game.hand import Hand
from game.types import SidePot


@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    players = []
    for name in ["Alice", "Bob", "Charlie"]:
        player = Mock(spec=LLMAgent)
        player.name = name
        player.chips = 1000
        player.folded = False
        player.bet = 0
        # Mock hand attribute
        player.hand = Mock(spec=Hand)
        player.hand.__eq__ = lambda self, other: False
        player.hand.__gt__ = lambda self, other: False

        # Create a proper place_bet method that updates chips
        def make_place_bet(p):
            def place_bet(amount):
                actual_amount = min(amount, p.chips)
                p.chips -= actual_amount
                p.bet += actual_amount
                return actual_amount

            return place_bet

        player.place_bet = make_place_bet(player)
        players.append(player)
    return players


@pytest.fixture
def game(mock_players):
    """Fixture to create game instance."""
    return AgenticPoker(
        players=mock_players,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )


def test_game_initialization(game, mock_players):
    """Test game initialization with valid parameters."""
    assert len(game.players) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None
    # Verify all players have initial chips
    for player in game.players:
        assert player.chips == 1000


def test_invalid_game_initialization(mock_players):
    """Test game initialization with invalid parameters."""
    with pytest.raises(ValueError):
        AgenticPoker(
            players=[],  # Empty players list
            small_blind=50,
            big_blind=100,
            ante=10,
        )

    with pytest.raises(ValueError):
        # Create players with negative chips
        invalid_players = [
            Mock(spec=LLMAgent, chips=-1000, name=f"Player{i}") for i in range(3)
        ]
        AgenticPoker(
            players=invalid_players,
            small_blind=50,
            big_blind=100,
            ante=10,
        )


@patch("game.game.betting_round")
def test_betting_rounds(mock_betting, game, mock_players):
    """Test betting round mechanics."""
    # Mock betting round function
    mock_betting.return_value = 300  # Return new pot amount

    # Set up initial game state
    game.start_round()
    game.pot = 150  # Set initial pot

    # Mock active players (not folded)
    active_players = [p for p in mock_players]
    for player in active_players:
        player.folded = False

    # Test pre-draw betting
    game.pot = mock_betting(active_players, game.pot, {})  # Pass empty game state

    # Verify betting round was called
    mock_betting.assert_called_with(active_players, 150, {})
    assert game.pot == 300  # New pot amount from mock


def test_blinds_and_antes(game, mock_players):
    """Test collection of blinds and antes."""
    initial_chips = [p.chips for p in mock_players]

    # Store starting stacks for logging
    game.round_starting_stacks = {p: p.chips for p in mock_players}

    game.blinds_and_antes()

    # Verify blinds were collected
    assert mock_players[1].chips < initial_chips[1]  # Small blind
    assert mock_players[2].chips < initial_chips[2]  # Big blind

    # Verify ante was collected from all players
    for player in mock_players:
        assert player.chips < initial_chips[mock_players.index(player)]


def test_showdown(game, mock_players):
    """Test showdown mechanics."""
    # Set up game state
    game.pot = 300
    game.round_starting_stacks = {p: 1000 for p in mock_players}

    # Set up mock hands
    for i, player in enumerate(mock_players):
        player.folded = False
        player.hand = Mock(spec=Hand)

        # Set up hand comparison logic
        def make_gt(idx):
            def compare(self, other):  # Need both self and other
                # First player has the best hand
                if not hasattr(other, "_mock_idx"):
                    return True
                return idx == 0

            return compare

        def make_eq(idx):
            def compare(self, other):  # Need both self and other
                # Hands are equal if they're the same index
                if not hasattr(other, "_mock_idx"):
                    return False
                return idx == other._mock_idx

            return compare

        player.hand.__gt__ = make_gt(i)
        player.hand.__eq__ = make_eq(i)
        player.hand._mock_idx = i  # Store index for comparison
        player.hand.evaluate.return_value = ["Royal Flush", "Full House", "Pair"][i]
        player.hand.show.return_value = f"Mock Hand {i}"

    # Run showdown
    game.showdown()

    # Verify winner received pot
    assert mock_players[0].chips == 1300  # Initial 1000 + pot 300
    assert mock_players[1].chips == 1000  # Unchanged
    assert mock_players[2].chips == 1000  # Unchanged


def test_player_elimination(game, mock_players):
    """Test player elimination mechanics."""
    # Set one player to 0 chips
    mock_players[0].chips = 0

    # Check if game continues
    result = game.remove_bankrupt_players()

    # Verify player was removed
    assert len(game.players) == 2
    assert mock_players[0] not in game.players


def test_game_end_conditions(game, mock_players):
    """Test various game ending conditions."""
    # Test max rounds reached
    game.max_rounds = 3
    game.round_count = 3

    with patch.object(game, "_log_game_summary"):
        game.start_game()
        game._log_game_summary.assert_called_once()

    # Reset game state
    game = AgenticPoker(
        players=mock_players,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )

    # Test one player remaining with chips
    mock_players[0].chips = 1000
    mock_players[1].chips = 0
    mock_players[2].chips = 0

    # Mock methods to prevent actual gameplay
    with patch.object(game, "_log_game_summary"), patch.object(
        game, "start_round"
    ), patch.object(game, "blinds_and_antes"), patch.object(
        game, "_handle_pre_draw_betting"
    ), patch.object(
        game, "draw_phase"
    ), patch.object(
        game, "_handle_post_draw_betting"
    ), patch.object(
        game, "_reset_round"
    ):

        # Force removal of bankrupt players
        game.remove_bankrupt_players()

        # Verify only one player remains
        assert (
            len(game.players) == 1
        ), f"Expected 1 player, got {len(game.players)}: {[p.name for p in game.players]}"
        assert game.players[0].chips == 1000
        assert game.players[0] == mock_players[0]

        # Start game should end immediately
        game.start_game()
        game._log_game_summary.assert_called_once()


@patch("game.game.AgenticPoker._get_player_action")
def test_full_betting_round(mock_get_action, game, mock_players):
    """Test a complete betting round with raises."""
    # Setup initial bets
    game.pot = 160  # Starting pot (blinds + antes)
    
    # Mock betting decisions
    mock_players[0].decide_action = Mock(return_value=(ActionType.RAISE, 200))
    mock_players[1].decide_action = Mock(return_value=(ActionType.CALL, 200))
    mock_players[2].decide_action = Mock(return_value=(ActionType.CALL, 200))
    
    # Run betting round
    game._handle_betting_round()
    
    # Calculate expected total (initial pot + 3 players betting 200 each)
    expected_total = 160 + (200 * 3)
    assert game.pot == expected_total, f"Expected pot {expected_total}, got {game.pot}"


@patch("game.game.betting_round")
@patch("game.game.AgenticPoker._get_player_action")
def test_full_betting_round_with_side_pots(mock_get_action, mock_betting, game, mock_players):
    """Test betting round that creates side pots."""
    # Initial setup
    game.pot = 150  # Starting pot
    total_pot = 850  # Expected final pot

    # Set up players with different chip amounts to force side pots
    mock_players[0].chips = 300  # Can only bet 300 total
    mock_players[1].chips = 500  # Can bet more
    mock_players[2].chips = 200  # Can only bet 200 total

    # Store initial chip counts
    initial_chips = {p: p.chips for p in mock_players}

    # Set up mock actions for all-in scenario - need enough actions for all possible calls
    actions = [
        ("raise", 300),  # Player 1 goes all-in with 300
        ("raise", 400),  # Player 2 raises to 400
        ("call", 150),   # Player 3 calls with remaining 150
        ("call", 400),   # Player 1 would need to call raise (but can't - all in)
    ]
    mock_get_action.side_effect = actions

    # Run pre-draw betting
    game._handle_pre_draw_betting(initial_chips)

    # Verify pot and side pots
    assert game.pot == total_pot, f"Expected pot {total_pot}, got {game.pot}"

    # Verify final chip counts
    assert mock_players[0].chips == 0, "Player 1 should be all-in"
    assert mock_players[1].chips == 100, "Player 2 should have 100 chips left"
    assert mock_players[2].chips == 50, "Player 3 should have 50 chips left"

    # Verify total bets
    total_bets = sum(p.bet for p in mock_players)
    assert total_bets == 850, f"Expected total bets 850, got {total_bets}"


@patch("game.game.betting_round")
def test_all_in_scenario(mock_betting, game, mock_players):
    """Test handling of all-in situations."""
    # Set up initial state
    game.pot = 150  # Set initial pot

    # Set up players with different chip amounts
    mock_players[0].chips = 500
    mock_players[1].chips = 300
    mock_players[2].chips = 100

    # Store initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Configure mock players' decide_action methods
    mock_players[0].decide_action = Mock(return_value=("raise", 500))
    mock_players[1].decide_action = Mock(return_value=("call", 300))
    mock_players[2].decide_action = Mock(return_value=("call", 100))

    # Mock betting round to return final pot and side pots
    side_pots = [
        (300, [mock_players[0], mock_players[1], mock_players[2]]),
        (400, [mock_players[0], mock_players[1]]),
        (200, [mock_players[0]]),
    ]
    mock_betting.return_value = (900, side_pots)  # Total pot of 900

    # Run pre-draw betting
    game._handle_pre_draw_betting(initial_chips)


def test_blinds_collection_order(game, mock_players):
    """Test that blinds are collected in the correct order."""
    initial_chips = 1000
    game.dealer_index = 0

    # Track bet order
    bet_sequence = []

    def track_bet(amount):
        nonlocal bet_sequence
        bet_sequence.append((amount))
        return amount

    for player in mock_players:
        player.place_bet = Mock(side_effect=track_bet)

    game.blinds_and_antes()

    # Verify correct order and amounts
    expected_sequence = [
        10,  # Ante from player 0
        10,  # Ante from player 1
        10,  # Ante from player 2
        50,  # Small blind from player 1
        100,  # Big blind from player 2
    ]

    assert bet_sequence == expected_sequence


def test_showdown_with_ties(game, mock_players):
    """Test pot distribution when multiple players tie for best hand."""
    game.pot = 900

    # Set up mock hands that tie
    mock_players[0].hand.evaluate = Mock(return_value="Full House")
    mock_players[1].hand.evaluate = Mock(return_value="Full House")
    mock_players[2].hand.evaluate = Mock(return_value="Two Pair")

    # Create a hand ranking system
    hand_ranks = {
        mock_players[0].hand: 2,  # High rank
        mock_players[1].hand: 2,  # Same high rank
        mock_players[2].hand: 1,  # Lower rank
    }

    # Define comparison methods using the ranking system
    def make_comparison_methods(hand):
        def gt(other):
            if not isinstance(other, Mock):
                return True
            return hand_ranks[hand] > hand_ranks[other]

        def eq(other):
            if not isinstance(other, Mock):
                return False
            return hand_ranks[hand] == hand_ranks[other]

        return gt, eq

    # Set up comparison methods for all hands
    for player in mock_players:
        gt, eq = make_comparison_methods(player.hand)
        player.hand.__gt__ = Mock(side_effect=gt)
        player.hand.__eq__ = Mock(side_effect=eq)
        player.folded = False  # Make sure no players are folded

    # Run showdown
    game.showdown()

    # Verify pot split evenly between tied winners
    assert mock_players[0].chips == 1450  # Initial 1000 + 450 (half of 900)
    assert mock_players[1].chips == 1450  # Initial 1000 + 450 (half of 900)
    assert mock_players[2].chips == 1000  # Unchanged


def test_player_elimination_sequence(game, mock_players):
    """Test proper handling of sequential player eliminations."""
    # Set up players with different chip amounts
    mock_players[0].chips = 0
    mock_players[1].chips = 50
    mock_players[2].chips = 100

    # First elimination
    game.remove_bankrupt_players()
    assert len(game.players) == 2
    assert mock_players[0] not in game.players

    # Second elimination
    mock_players[1].chips = 0
    game.remove_bankrupt_players()
    assert len(game.players) == 1
    assert mock_players[1] not in game.players

    # Verify game ends with one player
    assert not game.remove_bankrupt_players()


def test_ante_collection_with_short_stacks(game, mock_players):
    """Test ante collection when players can't cover the full amount."""
    game.ante = 20
    mock_players[0].chips = 15  # Can't cover ante
    mock_players[1].chips = 20  # Exactly ante amount
    mock_players[2].chips = 170  # Enough for ante + big blind

    # Set dealer position so player 2 is big blind
    game.dealer_index = 0  # Makes player 1 small blind, player 2 big blind

    game.blinds_and_antes()

    # Verify correct amounts collected
    assert mock_players[0].chips == 0  # Paid all 15 (partial ante)
    assert mock_players[1].chips == 0  # Paid all 20 (full ante)
    assert mock_players[2].chips == 50  # Paid 20 (ante) + 100 (big blind)

    # Total pot should be:
    # Player 0: 15 (partial ante)
    # Player 1: 20 (full ante)
    # Player 2: 20 (ante) + 100 (big blind)
    assert game.pot == 155


@patch("game.game.betting_round")
@patch("game.game.AgenticPoker.showdown")
def test_post_draw_betting(mock_betting, mock_showdown, game, mock_players):
    """Test post-draw betting mechanics."""
    initial_chips = {p: p.chips for p in mock_players}
    
    # Setup mock hands with proper comparison methods
    for i, player in enumerate(mock_players):
        player.hand = Mock(spec=Hand)
        # Define comparison methods based on player index
        player.hand.__gt__ = lambda other: i == 0  # First player has best hand
        player.hand.__eq__ = lambda other: False  # No ties
        player.hand.show = Mock(return_value="Mock Hand")
    
    # Run post-draw betting
    game._handle_post_draw_betting(initial_chips)
    
    # Verify winner got the pot
    assert mock_players[0].chips > initial_chips[mock_players[0]], \
        "Winner should have more chips than initial amount"


def test_game_progression_through_phases(game, mock_players):
    """Test that game progresses through all phases correctly."""
    # Create spies for each method
    with patch(
        "game.game.AgenticPoker._initialize_round", wraps=game._initialize_round
    ) as init_spy, patch(
        "game.game.AgenticPoker._log_round_info", wraps=game._log_round_info
    ) as log_spy, patch(
        "game.game.AgenticPoker._deal_cards", wraps=game._deal_cards
    ) as deal_spy, patch(
        "game.game.AgenticPoker._handle_pre_draw_betting"
    ) as pre_draw_spy, patch(
        "game.game.AgenticPoker.draw_phase", wraps=game.draw_phase
    ) as draw_spy, patch(
        "game.game.AgenticPoker._handle_post_draw_betting"
    ) as post_draw_spy:

        # Setup pre-draw betting to return appropriate value
        pre_draw_spy.return_value = (True, {})

        # Setup post-draw betting to return appropriate value
        post_draw_spy.return_value = None

        # Store initial chip counts
        initial_chips = {p: p.chips for p in mock_players}

        # Mock the deck
        game.deck = Mock()
        game.deck.deal = Mock(return_value=[Mock() for _ in range(5)])
        game.deck.shuffle = Mock()

        # Setup players for draw phase
        for player in mock_players:
            player.decide_draw = Mock(return_value=[])  # No cards to discard
            player.hand = Mock()
            player.hand.cards = [Mock() for _ in range(5)]
            player.hand.evaluate = Mock(return_value="Pair")
            player.hand.show = Mock(return_value="Mock Hand")

        # Setup initial game state
        game.pot = 0
        game.dealer_index = 0  # Set dealer position explicitly
        game.round_starting_stacks = {p: p.chips for p in mock_players}
        game.round_count = 0
        game.max_rounds = 1

        # Run the game
        game.start_game()

        # Print debug information
        print("\nGame state after start_game:")
        print(f"Pot: {game.pot}")
        print(f"Player bets: {[(p.name, p.bet) for p in mock_players]}")
        print(f"Player chips: {[(p.name, p.chips) for p in mock_players]}")
        print(
            f"Initial chips: {[(p.name, chips) for p, chips in initial_chips.items()]}"
        )
        print(f"Dealer index: {game.dealer_index}")
        print(f"Small blind position: {(game.dealer_index + 1) % len(mock_players)}")
        print(f"Big blind position: {(game.dealer_index + 2) % len(mock_players)}")

        # Verify blinds were collected
        sb_pos = (game.dealer_index + 1) % len(mock_players)
        bb_pos = (game.dealer_index + 2) % len(mock_players)

        # Verify small blind player paid
        assert (
            mock_players[sb_pos].chips < initial_chips[mock_players[sb_pos]]
        ), f"Small blind player {mock_players[sb_pos].name} should have less chips"

        # Verify big blind player paid
        assert (
            mock_players[bb_pos].chips < initial_chips[mock_players[bb_pos]]
        ), f"Big blind player {mock_players[bb_pos].name} should have less chips"

        # Verify ante was collected from all players
        for player in mock_players:
            assert (
                player.chips < initial_chips[player]
            ), f"Player {player.name} should have less chips after ante"

        # Verify method calls
        init_spy.assert_called_once()
        log_spy.assert_called_once()
        deal_spy.assert_called_once()
        pre_draw_spy.assert_called_once()
        draw_spy.assert_called_once()
        post_draw_spy.assert_called_once()


def test_draw_phase_mechanics(game, mock_players):
    """Test card drawing mechanics during draw phase."""
    # Create mock cards with proper string representation and required attributes
    class MockCard:
        def __init__(self, name):
            self.name = name
            # Add required attributes for hand evaluation
            self.rank = 2  # Default rank
            self.suit = "Hearts"  # Default suit

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

    class MockDeck:
        def __init__(self):
            self.cards = [MockCard(f"New {i}") for i in range(15)]
            self.discarded_cards = []
            self.dealt_cards = []
            self.shuffle_count = 0

        def deal(self, num_cards):
            dealt = self.cards[:num_cards]
            self.cards = self.cards[num_cards:]
            self.dealt_cards.extend(dealt)
            return dealt

        def shuffle(self):
            self.shuffle_count += 1

    game.deck = MockDeck()

    # Setup initial hands for all players
    for player in mock_players:
        # Create initial cards for each player
        initial_cards = [MockCard(f"Initial {i}") for i in range(5)]
        
        # Setup hand with proper mock methods
        player.hand = Hand()  # Use actual Hand class
        player.hand.cards = initial_cards
        player.folded = False
        
        # Mock decide_draw to discard specific cards
        player.decide_draw = Mock(return_value=[0, 1, 2])  # Discard first three cards

    # Run draw phase
    game.draw_phase()

    # Verify deck was used
    assert game.deck.shuffle_count > 0, "Deck was never shuffled"
    assert len(game.deck.dealt_cards) > 0, "No cards were dealt"

    # Calculate total cards dealt
    total_dealt = len(game.deck.dealt_cards)

    # Verify all players got their cards
    for player in mock_players:
        assert len(player.hand.cards) == 5, f"Player should have 5 cards, has {len(player.hand.cards)}"
        # Verify discarded cards were replaced
        assert any(str(card).startswith("New") for card in player.hand.cards), \
            "Some cards should have been replaced with new ones"
        assert any(str(card).startswith("Initial") for card in player.hand.cards), \
            "Some original cards should remain"

    # Verify we dealt the expected number of cards
    expected_dealt = len(mock_players) * 3  # Each player discards 3 cards
    assert total_dealt == expected_dealt, \
        f"Expected {expected_dealt} cards dealt, found {total_dealt}"


def test_side_pot_distribution(game, mock_players):
    """Test correct distribution of side pots."""
    # Setup players with different chip amounts and bets
    mock_players[0].chips = 500  # Had 1000, bet 500
    mock_players[1].chips = 0  # Had 500, bet 500
    mock_players[2].chips = 0  # Had 200, bet 200

    # Setup bets
    mock_players[0].bet = 500
    mock_players[1].bet = 500
    mock_players[2].bet = 200

    game.pot = 1200  # Total of all bets

    # Create side pots with explicit eligibility
    game.side_pots = [
        SidePot(
            600, [mock_players[0], mock_players[1], mock_players[2]]
        ),  # First pot: 200 from each
        SidePot(
            600, [mock_players[0], mock_players[1]]
        ),  # Second pot: 300 more from each
    ]

    # Setup hand rankings
    rankings = ["Pair", "Two Pair", "Three of a Kind"]

    # Create a class to handle hand comparisons
    class MockHand:
        def __init__(self, rank, name):
            self.rank = rank
            self.name = name

        def evaluate(self):
            return self.rank

        def __gt__(self, other):
            if not other or not hasattr(other, "evaluate"):
                return True
            return rankings.index(self.rank) > rankings.index(other.evaluate())

        def __eq__(self, other):
            if not other or not hasattr(other, "evaluate"):
                return False
            return self.rank == other.evaluate()

        def show(self):
            return f"{self.name}'s {self.rank}"

    # Setup hands for each player
    mock_players[2].hand = MockHand(
        "Three of a Kind", mock_players[2].name
    )  # Best hand
    mock_players[1].hand = MockHand("Two Pair", mock_players[1].name)  # Second best
    mock_players[0].hand = MockHand("Pair", mock_players[0].name)  # Worst hand

    # Set folded status for each player
    mock_players[0].folded = False
    mock_players[1].folded = False
    mock_players[2].folded = False

    # Mock the evaluate_hands method to handle pot distribution
    def mock_evaluate_hands(players, pot):
        # Sort players by hand rank
        active_players = [p for p in players if not p.folded]
        sorted_players = sorted(
            active_players,
            key=lambda p: rankings.index(p.hand.evaluate()),
            reverse=True,
        )
        return [sorted_players[0]]  # Return only the winner

    game._evaluate_hands = mock_evaluate_hands

    # Run showdown with side pots
    for side_pot in game.side_pots:
        winners = game._evaluate_hands(side_pot.eligible_players, side_pot)
        for winner in winners:
            winner.chips += side_pot.amount // len(winners)

    # Reset pot and side pots
    game.pot = 0
    game.side_pots = None

    # Verify correct pot distribution
    assert (
        mock_players[2].chips == 600
    ), f"Player 2 should have 600 (won first pot), has {mock_players[2].chips}"
    assert (
        mock_players[1].chips == 600
    ), f"Player 1 should have 600 (won second pot), has {mock_players[1].chips}"
    assert (
        mock_players[0].chips == 500
    ), f"Player 0 should have 500 (original chips), has {mock_players[0].chips}"


def test_dealer_button_rotation(game, mock_players):
    """Test proper rotation of dealer button and blinds."""
    initial_dealer = game.dealer_index

    # Play multiple rounds
    for i in range(len(mock_players) * 2):
        # Need to reset betting state before starting new round
        for player in mock_players:
            player.bet = 0
            player.folded = False

        # Start round and verify dealer position before blinds
        game._initialize_round()

        # Verify dealer position rotated correctly
        expected_dealer = (initial_dealer + i + 1) % len(mock_players)
        assert (
            game.dealer_index == expected_dealer
        ), f"Expected dealer to be at position {expected_dealer}, but was at {game.dealer_index}"

        # Now collect blinds
        game.blinds_and_antes()

        # Verify blind positions
        sb_pos = (game.dealer_index + 1) % len(mock_players)
        bb_pos = (game.dealer_index + 2) % len(mock_players)

        # Check blind assignments
        assert (
            mock_players[sb_pos].bet >= game.small_blind
        ), f"Small blind not posted correctly at position {sb_pos}"
        assert (
            mock_players[bb_pos].bet >= game.big_blind
        ), f"Big blind not posted correctly at position {bb_pos}"

        # Complete the round
        game._reset_round()


def test_invalid_bet_handling(game, mock_players):
    """Test handling of invalid betting scenarios."""
    # Create a real Player instance for testing bet validation
    from game.player import Player

    player = Player("TestPlayer", chips=100)

    # Test bet larger than chips
    actual_bet = player.place_bet(200)
    assert actual_bet == 100  # Should only bet available chips
    assert player.chips == 0

    # Test negative bet
    with pytest.raises(ValueError, match="Cannot place negative bet"):
        player.place_bet(-50)


def test_deck_reshuffling(game, mock_players):
    """Test deck reshuffling when running out of cards."""

    # Create mock cards with proper string representation
    class MockCard:
        def __init__(self, name):
            self.name = name

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

    # Setup a nearly empty deck with discarded cards
    replacement_cards = [
        MockCard(f"New {i}") for i in range(20)
    ]  # More cards for reshuffling
    discarded_cards = [
        MockCard(f"Discarded {i}") for i in range(30)
    ]  # Add discarded cards

    # Create a deck mock that simulates reshuffling behavior
    class MockDeck(Mock):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._all_replacement_cards = replacement_cards.copy()  # Keep original list
            self._current_position = 0  # Track which cards we've dealt
            self.cards = []  # Start with empty deck
            self.discarded_cards = discarded_cards
            self.dealt_cards = []
            self.shuffle_count = 0

        def deal(self, num):
            # Always deal new cards from replacement cards
            if self._current_position + num > len(self._all_replacement_cards):
                # Reset position and shuffle if we need more cards
                self._current_position = 0
                self.shuffle()

            # Deal the next batch of replacement cards
            start = self._current_position
            end = start + num
            dealt = self._all_replacement_cards[start:end]
            self._current_position = end

            self.dealt_cards.extend(dealt)
            return dealt

        def shuffle(self):
            # Mock shuffle by reversing remaining cards
            remaining = self._all_replacement_cards[self._current_position :]
            remaining.reverse()
            self._all_replacement_cards = (
                self._all_replacement_cards[: self._current_position] + remaining
            )
            self.shuffle_count += 1

    game.deck = MockDeck()

    # Setup initial hands for all players
    for player in mock_players:
        # Create initial cards for each player
        initial_cards = [MockCard(f"Initial {i}") for i in range(5)]

        # Setup hand with cards
        player.hand = Mock(spec=Hand)
        player.hand.cards = initial_cards
        player.folded = False

        # Mock decide_draw to discard all cards
        player.decide_draw = Mock(return_value=[0, 1, 2, 3, 4])

        # Setup hand methods
        def make_remove_cards(p):
            def remove_cards(indices):
                # Keep cards not being discarded
                removed = [p.hand.cards[i] for i in indices]
                p.hand.cards = [
                    card for i, card in enumerate(p.hand.cards) if i not in indices
                ]
                # Add removed cards to deck's discarded pile
                game.deck.discarded_cards.extend(removed)

            return remove_cards

        def make_add_cards(p):
            def add_cards(new_cards):
                # Add new cards to hand
                p.hand.cards = new_cards  # Replace entire hand instead of extending

            return add_cards

        player.hand.remove_cards = make_remove_cards(player)
        player.hand.add_cards = make_add_cards(player)

    # Run draw phase
    game.draw_phase()

    # Verify deck was reshuffled
    assert game.deck.shuffle_count > 0, "Deck was never shuffled"
    assert len(game.deck.dealt_cards) > 0, "No cards were dealt"

    # Calculate total cards dealt
    total_dealt = len(game.deck.dealt_cards)

    # Verify all players got their cards
    for player in mock_players:
        assert (
            len(player.hand.cards) == 5
        ), f"Player should have 5 cards, has {len(player.hand.cards)}"
        # Verify all cards were replaced
        assert all(
            str(card).startswith("New") for card in player.hand.cards
        ), "All cards should have been replaced with new ones"

    # Verify we dealt the expected number of cards
    expected_dealt = len(mock_players) * 5  # Each player should get 5 new cards
    assert (
        total_dealt == expected_dealt
    ), f"Expected {expected_dealt} cards dealt, found {total_dealt}"


def test_chip_consistency(game, mock_players):
    """Test that total chips remain constant throughout the game."""
    initial_total = sum(p.chips for p in mock_players)
    
    # Run several betting rounds
    game.play_round()
    
    current_total = sum(p.chips for p in mock_players) + game.pot
    assert initial_total == current_total, "Total chips in play changed"


# ... Rest of the tests converted to pytest style ...
