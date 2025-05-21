import pytest
from game.game import AgenticPoker
from game.player import Player
from game.config import GameConfig
from agents.random_agent import RandomAgent
from game.card import Card
from data.types.hand_rank import HandRank
from data.enums import ActionType
from data.types.action_decision import ActionDecision
from game import showdown # For test_texas_holdem_hand_evaluation_royal_flush
from game.hand import Hand # For test_texas_holdem_hand_evaluation_royal_flush

@pytest.fixture
def texas_holdem_config_6max():
    """Returns a GameConfig for a 6-Max No-Limit Texas Hold'em game."""
    return GameConfig(
        game_type="TEXAS_HOLDEM",
        max_players=6,
        starting_chips=1000,
        small_blind=5,
        big_blind=10,
        ante=0,
        max_raise_multiplier=None,  # Should be None for NLHE
        max_raises_per_round=None, # Should be None for NLHE
    )

@pytest.fixture
def random_agents_texas_holdem(request, texas_holdem_config_6max):
    """Creates a list of RandomAgent players for Texas Hold'em."""
    num_players = request.param if hasattr(request, 'param') else texas_holdem_config_6max.max_players
    agents = []
    for i in range(num_players):
        # Pass the game_instance to Table within AgenticPoker if Table's __init__ expects it
        # For now, assuming RandomAgent doesn't need game_instance directly at init for config
        agent = RandomAgent(name=f"Player {i+1}", chips=texas_holdem_config_6max.starting_chips)
        agents.append(agent)
    return agents

# Test case for game setup
def test_game_setup_texas_holdem_6max(texas_holdem_config_6max, random_agents_texas_holdem):
    game = AgenticPoker(
        players=random_agents_texas_holdem, 
        config=texas_holdem_config_6max
    )
    assert game.game_type == "TEXAS_HOLDEM"
    assert game.max_players == 6
    assert len(game.table.players) == 6
    assert game.config.max_raise_multiplier is None
    assert game.config.max_raises_per_round is None
    assert game.config.small_blind == 5
    assert game.config.big_blind == 10

# Test case for initial deal
@pytest.mark.parametrize("random_agents_texas_holdem", [3], indirect=True)
def test_initial_deal_texas_holdem(texas_holdem_config_6max, random_agents_texas_holdem):
    num_players = len(random_agents_texas_holdem)
    game = AgenticPoker(
        players=random_agents_texas_holdem,
        config=texas_holdem_config_6max
    )
    game._start_new_round() # This calls _initialize_round and _deal_cards

    for player in game.table.players:
        assert player.hand is not None
        assert len(player.hand.cards) == 2
    
    assert len(game.community_cards) == 0
    assert game.deck.remaining_cards() == 52 - (num_players * 2)

# Test case for community card dealing
@pytest.mark.parametrize("random_agents_texas_holdem", [3], indirect=True)
def test_community_card_dealing(texas_holdem_config_6max, random_agents_texas_holdem):
    num_players = len(random_agents_texas_holdem)
    game = AgenticPoker(
        players=random_agents_texas_holdem,
        config=texas_holdem_config_6max
    )
    game._start_new_round()
    initial_deck_count = 52 - (num_players * 2)

    game._deal_flop()
    assert len(game.community_cards) == 3
    assert game.deck.remaining_cards() == initial_deck_count - 3
    # Ensure community cards are actual Card objects (simple check)
    assert all(isinstance(card, Card) for card in game.community_cards)


    game._deal_turn()
    assert len(game.community_cards) == 4
    assert game.deck.remaining_cards() == initial_deck_count - 3 - 1
    assert isinstance(game.community_cards[-1], Card)


    game._deal_river()
    assert len(game.community_cards) == 5
    assert game.deck.remaining_cards() == initial_deck_count - 3 - 1 - 1
    assert isinstance(game.community_cards[-1], Card)

# Helper Agent for simple game flow test
class CheckCallAgent(RandomAgent):
    def decide_action(self, game: "AgenticPoker") -> ActionDecision: # Type hint for game
        amount_to_call = game.current_bet - self.bet
        if amount_to_call <= 0:
            # Check if current_bet is 0 (pre-flop, no one has bet yet, or everyone checked around)
            # OR if current_bet > 0 but player has already matched it.
            return ActionDecision(action_type=ActionType.CHECK)
        
        # If there's a bet to call
        if self.chips >= amount_to_call: # Check if player can afford to call
             # The 'amount' for CALL should be the additional amount needed.
             # Player.execute will handle the actual deduction and all-in logic.
            return ActionDecision(action_type=ActionType.CALL, amount=amount_to_call)
        
        # If cannot afford full call, but has some chips, should be an all-in call.
        # Player.execute handles all-in logic based on amount_to_call.
        # If chips are less than amount_to_call but > 0, it's an all-in call.
        if self.chips > 0:
            return ActionDecision(action_type=ActionType.CALL, amount=self.chips)

        return ActionDecision(action_type=ActionType.FOLD) # Should only FOLD if chips are 0 and facing a bet.

# Test case for a simple game flow with players mostly checking/calling
def test_simple_texas_holdem_game_flow_all_check_call(texas_holdem_config_6max):
    # Create 3 CheckCallAgent players
    players = [
        CheckCallAgent(name="Agent 1", chips=texas_holdem_config_6max.starting_chips),
        CheckCallAgent(name="Agent 2", chips=texas_holdem_config_6max.starting_chips),
        CheckCallAgent(name="Agent 3", chips=texas_holdem_config_6max.starting_chips),
    ]
    game = AgenticPoker(players=players, config=texas_holdem_config_6max)

    # Manually set dealer for predictability if needed, or let it default
    game.dealer_index = 0 

    # --- Round 1 ---
    game._start_new_round() # Deals cards, collects blinds
    
    # Pre-flop betting
    # Blinds are posted, game.current_bet is big_blind
    # Player after BB acts first.
    # With CheckCallAgent, they should call if facing a bet, or check if not.
    # The small blind will complete, big blind might check if no raise.
    game._handle_pre_flop_betting() 
    assert game.pot.get_total_pot() > 0 # Pot should have blinds

    # Flop
    game._handle_flop_dealing_and_betting() # Deals flop, then betting round
    assert len(game.community_cards) == 3

    # Turn
    game._handle_turn_dealing_and_betting() # Deals turn, then betting round
    assert len(game.community_cards) == 4

    # River
    game._handle_river_dealing_and_betting() # Deals river, then betting round
    assert len(game.community_cards) == 5
    
    # Showdown
    # Store chips before showdown for comparison
    chips_before_showdown = {p.name: p.chips for p in game.table.players}
    pot_before_showdown = game.pot.get_total_pot()

    game._handle_showdown()

    # Assertions after showdown
    for player in game.table.players:
        if not player.folded: # Folded players won't have best_hand_evaluation from showdown processing
            assert player.best_hand_evaluation is not None
    
    # Check if pot was distributed - sum of chips should be same, or one player has more.
    # This is a simple check; a more robust check would track specific winner and pot amount.
    assert game.pot.get_total_pot() == 0 or sum(p.chips for p in game.table.players) == sum(chips_before_showdown.values()) + pot_before_showdown

# Test case for Royal Flush evaluation
def test_texas_holdem_hand_evaluation_royal_flush(texas_holdem_config_6max):
    player1 = RandomAgent(name="Player 1", chips=texas_holdem_config_6max.starting_chips)
    player2 = RandomAgent(name="Player 2", chips=texas_holdem_config_6max.starting_chips) # Dummy player
    
    game = AgenticPoker(players=[player1, player2], config=texas_holdem_config_6max)
    game._start_new_round() # To initialize player hands, deck etc.

    # Manually set player 1's hole cards
    player1.hand = Hand() # Clear any dealt cards
    player1.hand.add_cards([Card("S", "A"), Card("S", "K")])

    # Manually set community cards
    game.community_cards = [
        Card("S", "Q"), Card("S", "J"), Card("S", "T"),
        Card("H", "2"), Card("D", "3") 
    ]
    
    # Call showdown logic (which includes hand evaluation for Texas Hold'em)
    # For this specific test, we are focusing on player1's hand evaluation part of showdown.
    # We directly invoke parts of the showdown logic or a helper if available.
    # The full _handle_showdown also does pot distribution, etc.
    # For simplicity, let's assume _handle_showdown will correctly set best_hand_evaluation.
    
    # To make showdown.handle_showdown work, we need to ensure players are on the table
    # and other game states are minimally set up.
    game.table.players = [player1, player2] # Ensure players are on the table for showdown
    game.initial_chips = {p: p.chips for p in game.table.players} # Required by showdown
    
    # Simulate that betting has occurred and community cards are final
    # The actual betting doesn't matter for this hand evaluation test
    
    showdown.handle_showdown(game) # This will evaluate hands

    assert player1.best_hand_evaluation is not None
    assert player1.best_hand_evaluation.rank == HandRank.ROYAL_FLUSH
    assert player1.best_hand_evaluation.description == "Royal Flush of Spades"

# TODO: Add more tests for betting scenarios (min-raises, all-ins, side pots)
# TODO: Add tests for edge cases in game flow and player actions.
