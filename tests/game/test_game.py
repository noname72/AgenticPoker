from datetime import datetime
from unittest.mock import Mock

import pytest

from agents.agent import Agent
from game import AgenticPoker
from game.card import Card
from game.draw import handle_draw_phase
from game.hand import Hand


@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    players = []
    for name in ["Alice", "Bob", "Charlie"]:
        player = Mock(spec=Agent)
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
    assert len(game.table) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None
    # Verify all players have initial chips
    for player in game.table:
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
            Mock(spec=Agent, chips=-1000, name=f"Player{i}") for i in range(3)
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

    # Reset round which rotates dealer
    game._reset_round()

    # Verify dealer rotated
    expected_dealer = (initial_dealer + 1) % len(mock_players)
    assert game.dealer_index == expected_dealer


def test_round_initialization(game, mock_players):
    """Test initialization of a new round."""
    game._initialize_round()

    # Verify round state
    assert game.pot_manager.pot == 0
    assert all(player.bet == 0 for player in game.table)
    assert all(not player.folded for player in game.table)
    assert all(hasattr(player, "hand") for player in game.table)


def test_hand_ranks_update_after_draw(game, mock_players):
    """Test that hand ranks are properly updated after the draw phase."""

    # Create real Hand objects for all players
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

    mock_players[2].hand = Hand(
        [  # Charlie's hand
            Card("2", "♣"),
            Card("3", "♣"),
            Card("4", "♣"),
            Card("5", "♦"),
            Card("6", "♥"),
        ]
    )

    # Store initial cards for verification
    alice_initial_cards = mock_players[0].hand.cards.copy()
    bob_initial_cards = mock_players[1].hand.cards.copy()
    charlie_initial_cards = mock_players[2].hand.cards.copy()

    # Setup initial ranks and descriptions
    mock_players[0].hand.evaluate = Mock(
        return_value="High Card, K high [Rank: 10, Tiebreakers: [13, 10, 8, 6, 4]]"
    )
    mock_players[1].hand.evaluate = Mock(
        return_value="One Pair, 9s [Rank: 9, Tiebreakers: [9, 11, 8, 5]]"
    )
    mock_players[2].hand.evaluate = Mock(
        return_value="High Card, 6 high [Rank: 10, Tiebreakers: [6, 5, 4, 3, 2]]"
    )

    # Add debugging before draw phase
    print("\n=== Debug Info Before Draw Phase ===")
    print(f"Alice's initial hand: {[str(c) for c in mock_players[0].hand.cards]}")
    print(f"Bob's initial hand: {[str(c) for c in mock_players[1].hand.cards]}")
    print(f"Charlie's initial hand: {[str(c) for c in mock_players[2].hand.cards]}")

    # Mock the draw decisions
    def alice_draw(game_state=None):
        cards = [str(c) for c in mock_players[0].hand.cards]
        print(f"\nAlice deciding discards. Current hand: {cards}")
        # Keep 10♠ and K♥, discard others
        return [
            i
            for i, card in enumerate(mock_players[0].hand.cards)
            if card not in [alice_initial_cards[0], alice_initial_cards[4]]
        ]

    def bob_draw(game_state=None):
        cards = [str(c) for c in mock_players[1].hand.cards]
        print(f"\nBob deciding discards. Current hand: {cards}")
        # Keep all except 5♣
        return [
            i
            for i, card in enumerate(mock_players[1].hand.cards)
            if card == bob_initial_cards[2]
        ]

    def charlie_draw(game_state=None):
        cards = [str(c) for c in mock_players[2].hand.cards]
        print(f"\nCharlie deciding discards. Current hand: {cards}")
        # Discard everything
        return list(range(5))

    # Assign the draw functions
    mock_players[0].decide_draw = alice_draw
    mock_players[1].decide_draw = bob_draw
    mock_players[2].decide_draw = charlie_draw

    # Setup cards to be drawn
    new_cards_alice = [Card("K", "♣"), Card("Q", "♦"), Card("9", "♥")]
    new_cards_bob = [Card("K", "♠")]
    new_cards_charlie = [
        Card("A", "♠"),
        Card("K", "♦"),
        Card("Q", "♣"),
        Card("J", "♥"),
        Card("10", "♣"),
    ]
    game.deck.deal = Mock(
        side_effect=[new_cards_alice, new_cards_bob, new_cards_charlie]
    )

    print("\n=== Starting Draw Phase ===")
    handle_draw_phase(mock_players, game.deck)

    print("\n=== Debug Info After Draw Phase ===")
    print(f"Alice's final hand: {[str(c) for c in mock_players[0].hand.cards]}")
    print(f"Bob's final hand: {[str(c) for c in mock_players[1].hand.cards]}")
    print(f"Charlie's final hand: {[str(c) for c in mock_players[2].hand.cards]}")

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
    mock_players[2].hand.evaluate = Mock(
        return_value="High Card, 6 high [Rank: 10, Tiebreakers: [6, 5, 4, 3, 2]]"
    )

    # Verify hands were properly updated
    alice_eval = mock_players[0].hand.evaluate()
    bob_eval = mock_players[1].hand.evaluate()
    charlie_eval = mock_players[2].hand.evaluate()

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
    assert "High Card, 6" in charlie_eval, (
        f"Charlie's hand didn't improve to high card.\n"
        f"Expected: High Card, 6\n"
        f"Got: {charlie_eval}\n"
        f"Cards: {[str(c) for c in mock_players[2].hand.cards]}"
    )

    # Verify the evaluation was called with updated cards
    try:
        mock_players[0].hand.evaluate.assert_called_once()
        mock_players[1].hand.evaluate.assert_called_once()
        mock_players[2].hand.evaluate.assert_called_once()
    except AssertionError as e:
        print(f"\nEvaluation call counts wrong:")
        print(
            f"Alice's evaluate() called {mock_players[0].hand.evaluate.call_count} times"
        )
        print(
            f"Bob's evaluate() called {mock_players[1].hand.evaluate.call_count} times"
        )
        print(
            f"Charlie's evaluate() called {mock_players[2].hand.evaluate.call_count} times"
        )
        raise e
