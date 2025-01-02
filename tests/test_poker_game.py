from datetime import datetime
from unittest.mock import Mock

import pytest

from agents.llm_agent import LLMAgent
from game import AgenticPoker
from game.hand import Hand
from game.card import Card


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


def test_dealer_rotation(game, mock_players):
    """Test dealer button rotation between rounds."""
    initial_dealer = game.dealer_index

    # Initialize round which rotates dealer
    game._initialize_round()

    # Verify dealer rotated
    expected_dealer = (initial_dealer + 1) % len(mock_players)
    assert game.dealer_index == expected_dealer


def test_round_initialization(game, mock_players):
    """Test initialization of a new round."""
    game._initialize_round()

    # Verify round state
    assert game.pot_manager.pot == 0
    assert all(player.bet == 0 for player in game.players)
    assert all(not player.folded for player in game.players)
    assert all(hasattr(player, "hand") for player in game.players)


def test_game_state_creation(game, mock_players):
    """Test creation of game state dictionary."""
    game_state = game._create_game_state()

    assert "pot" in game_state
    assert "players" in game_state
    assert "current_bet" in game_state
    assert "small_blind" in game_state
    assert "big_blind" in game_state
    assert "dealer_index" in game_state

    # Verify player info
    for player_info in game_state["players"]:
        assert "name" in player_info
        assert "chips" in player_info
        assert "bet" in player_info
        assert "folded" in player_info
        assert "position" in player_info


def test_hand_ranks_update_after_draw(game, mock_players):
    """Test that hand ranks are properly updated after the draw phase."""

    # Create real Hand objects instead of Mocks for proper card handling
    mock_players[0].hand = Hand(
        [  # Alice's hand
            Card("10", "♠"),
            Card("8", "♦"),
            Card("6", "♠"),
            Card("4", "♥"),
            Card("K", "♥"),
        ]
    )

    mock_players[1].hand = Hand(
        [  # Bob's hand
            Card("9", "♣"),
            Card("9", "♠"),
            Card("5", "♣"),
            Card("8", "♥"),
            Card("J", "♦"),
        ]
    )

    # Store the evaluate method so we can mock it after creating real hands
    real_evaluate = Hand.evaluate

    # Setup initial ranks and descriptions
    mock_players[0].hand.evaluate = Mock(
        return_value="High Card, K high [Rank: 10, Tiebreakers: [13, 10, 8, 6, 4]]"
    )
    mock_players[1].hand.evaluate = Mock(
        return_value="One Pair, 9s [Rank: 9, Tiebreakers: [9, 11, 8, 5]]"
    )

    # Verify initial evaluations
    initial_alice = mock_players[0].hand.evaluate()
    initial_bob = mock_players[1].hand.evaluate()
    assert "High Card" in initial_alice, f"Alice's initial hand wrong: {initial_alice}"
    assert "One Pair" in initial_bob, f"Bob's initial hand wrong: {initial_bob}"

    # Mock the draw decisions with actual lists instead of Mock objects
    def alice_decide_draw(game_state=None):
        return [1, 2, 3]  # Discard three cards

    mock_players[0].decide_draw = alice_decide_draw

    def bob_decide_draw(game_state=None):
        return [2]  # Discard one card

    mock_players[1].decide_draw = bob_decide_draw

    # Setup cards to be drawn
    new_cards_alice = [Card("K", "♣"), Card("Q", "♦"), Card("9", "♥")]
    new_cards_bob = [Card("K", "♠")]
    game.deck.deal = Mock(side_effect=[new_cards_alice, new_cards_bob])

    # Run draw phase using the imported function
    from game.draw_phase import handle_draw_phase

    handle_draw_phase(mock_players, game.deck)

    # Verify cards were properly discarded and drawn
    expected_alice_cards = {
        str(Card("10", "♠")),  # Kept
        str(Card("K", "♥")),  # Kept
        str(Card("K", "♣")),  # New
        str(Card("Q", "♦")),  # New
        str(Card("9", "♥")),  # New
    }
    actual_alice_cards = {str(card) for card in mock_players[0].hand.cards}
    assert len(mock_players[0].hand.cards) == 5, (
        f"Alice's hand has wrong size after draw: {len(mock_players[0].hand.cards)}\n"
        f"Cards: {[str(c) for c in mock_players[0].hand.cards]}"
    )
    assert expected_alice_cards == actual_alice_cards, (
        f"Alice's cards don't match expected:\n"
        f"Expected: {sorted(expected_alice_cards)}\n"
        f"Got: {sorted(actual_alice_cards)}"
    )

    # Update mock evaluations for new hands
    mock_players[0].hand.evaluate = Mock(
        return_value="One Pair, Ks [Rank: 9, Tiebreakers: [13, 12, 10, 9]]"
    )
    mock_players[1].hand.evaluate = Mock(
        return_value="High Card, K high [Rank: 10, Tiebreakers: [13, 11, 9, 9, 8]]"
    )

    # Verify hands were properly updated
    alice_eval = mock_players[0].hand.evaluate()
    bob_eval = mock_players[1].hand.evaluate()

    # Check that ranks reflect the new hands with detailed error messages
    assert "One Pair, Ks" in alice_eval, (
        f"Alice's hand didn't improve to pair of Kings.\n"
        f"Expected: One Pair, Ks\n"
        f"Got: {alice_eval}\n"
        f"Cards: {[str(c) for c in mock_players[0].hand.cards]}"
    )
    assert "High Card, K" in bob_eval, (
        f"Bob's pair wasn't broken to high card.\n"
        f"Expected: High Card, K\n"
        f"Got: {bob_eval}\n"
        f"Cards: {[str(c) for c in mock_players[1].hand.cards]}"
    )

    # Verify the evaluation was called with updated cards
    try:
        mock_players[0].hand.evaluate.assert_called_once()
        mock_players[1].hand.evaluate.assert_called_once()
    except AssertionError as e:
        print(f"\nEvaluation call counts wrong:")
        print(
            f"Alice's evaluate() called {mock_players[0].hand.evaluate.call_count} times"
        )
        print(
            f"Bob's evaluate() called {mock_players[1].hand.evaluate.call_count} times"
        )
        raise e
