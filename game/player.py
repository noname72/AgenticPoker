import logging

from data.states.player_state import PlayerState
from data.types.action_decision import ActionDecision, ActionType
from data.types.player_types import PlayerPosition
from typing import Optional # Add this import
from loggers.player_logger import PlayerLogger

from .hand import Hand
from .evaluator import HandEvaluation # Add this import


class Player:
    """
    Represents a poker player with chips, betting capability, and a hand of cards.

    This class manages a player's state during a poker game, including their chips,
    current bet, hand of cards, and fold status. It handles all betting operations
    and ensures proper tracking of player resources.

    Attributes:
        name (str): The player's display name
        chips (int): The current amount of chips the player possesses
        bet (int): The amount of chips bet in the current betting round
        folded (bool): Whether the player has folded in the current hand
        hand (Hand): The player's current hand of cards
        position (PlayerPosition): The player's current position in the game
    """

    name: str
    chips: int  #! change to stack???
    bet: int
    folded: bool
    hand: Hand
    position: PlayerPosition
    is_all_in: bool
    checked: bool
    called: bool
    _logged_all_in: bool  # New flag to track if all-in was logged
    best_hand_evaluation: Optional[HandEvaluation] = None

    def __init__(self, name: str, chips: int = 1000) -> None:
        """
        Initialize a new player with a name and starting chips.

        Args:
            name (str): The player's display name
            chips (int, optional): Starting amount of chips. Defaults to 1000.

        Raises:
            ValueError: If name is empty or chips is negative
        """
        if not name or name.isspace():
            raise ValueError("Player name cannot be empty or whitespace")
        if not isinstance(chips, int):
            raise ValueError("Chips must be an integer value")
        if chips < 0:
            raise ValueError("Cannot initialize player with negative chips")

        self.name = name
        self.chips = chips
        self.bet = 0
        self.hand = Hand()
        self.position = PlayerPosition.OTHER
        self.folded = False
        self.is_all_in = False
        self.checked = False
        self.called = False
        self._logged_all_in = False  # Initialize flag

        PlayerLogger.log_player_creation(name, chips)

    def place_bet(self, amount: int, game) -> int:
        """Place a bet, ensuring it doesn't exceed available chips."""
        if amount < 0:
            PlayerLogger.log_invalid_bet(self.name, "Cannot place negative bet")
            raise ValueError("Cannot place negative bet")

        # If player doesn't have enough chips, they go all-in
        if amount >= self.chips:
            amount = self.chips
            self.is_all_in = True
            # Only log all-in status once
            if not self._logged_all_in:
                PlayerLogger.log_all_in(self.name, amount)
                self._logged_all_in = True

        self.chips -= amount
        self.bet += amount
        game.pot.add_to_pot(amount)

        PlayerLogger.log_bet_placement(
            self.name, amount, self.bet, self.chips, game.pot.pot
        )
        return amount

    def execute(self, action_decision: ActionDecision, game):
        try:
            PlayerLogger.log_action_execution(
                self.name, action_decision.action_type.name
            )
            if action_decision.action_type == ActionType.BET:
                self._bet(action_decision.amount, game) # amount is bet_amount
            elif action_decision.action_type == ActionType.RAISE:
                self._raise(action_decision.amount, game) # amount is raise_amount (additional)
            elif action_decision.action_type == ActionType.CALL:
                self._call(game.current_bet, game)
            elif action_decision.action_type == ActionType.CHECK:
                self._check()
            elif action_decision.action_type == ActionType.FOLD:
                self._fold()
        except Exception as e:
            PlayerLogger.log_action_error(
                self.name, action_decision.action_type.name, e
            )
            raise

    def _bet(self, bet_amount: int, game) -> None:
        """Handle a bet action (opening bet)."""
        if game.game_type == "TEXAS_HOLDEM":
            # No-Limit: bet_amount must be at least big_blind, or player's stack if less
            min_bet_val = game.big_blind
            
            if bet_amount < min_bet_val and bet_amount < self.chips:
                PlayerLogger.log_invalid_bet(self.name, f"Bet ${bet_amount} is less than minimum ${min_bet_val}. Adjusting to minimum or all-in.")
                bet_amount = min_bet_val
            
            actual_bet_amount = self.place_bet(bet_amount, game) # place_bet handles all-in
            game.current_bet = self.bet # self.bet is cumulative for the round
            game.last_raiser = self # An opening bet acts like a raise in terms of who needs to act next
            game.table.min_raise_amount = actual_bet_amount # The next raise must be at least this much more

        else: # FIVE_CARD_DRAW (Limit)
            # In limit, an opening bet is typically fixed, e.g., to big_blind
            # This logic assumes a fixed bet size for limit, adjust if using multipliers for bets too.
            fixed_bet_amount = game.big_blind # Or game.config.min_bet
            actual_bet_amount = self.place_bet(fixed_bet_amount, game)
            game.current_bet = self.bet
            game.last_raiser = self
            if game.round_state: # Limit games track raise counts
                game.round_state.raise_count +=1 # Opening bet counts as the first "raise" in some structures
                game.round_state.last_raiser = self.name
        PlayerLogger.log_player_action(self.name, "BET", actual_bet_amount)


    def _raise(self, raise_by_amount: int, game) -> None:
        """Handle raise action."""
        if game.game_type == "TEXAS_HOLDEM":
            # raise_by_amount is the additional amount to raise
            # Min raise is either big blind (if first raise) or the previous raise amount
            min_raise_val = max(game.table.min_raise_amount, game.big_blind)

            if raise_by_amount < min_raise_val and (self.bet + raise_by_amount) < self.chips: # Not an all-in that's less
                PlayerLogger.log_invalid_bet(self.name, f"Raise amount ${raise_by_amount} is less than minimum raise ${min_raise_val}. Adjusting.")
                raise_by_amount = min_raise_val
            
            amount_to_call = game.current_bet - self.bet
            if amount_to_call < 0: amount_to_call = 0 # If current_bet is less due to all-in, don't need to call negative

            total_bet_this_action = amount_to_call + raise_by_amount
            
            actual_bet_placed = self.place_bet(total_bet_this_action, game) # Handles all-in logic

            # The actual amount raised "by" might be different if player went all-in
            actual_raised_by = actual_bet_placed - amount_to_call
            
            game.current_bet = self.bet # self.bet is cumulative total for player this round
            game.last_raiser = self
            if actual_raised_by > 0 : # Only update min_raise_amount if it was a valid raise part
                 game.table.min_raise_amount = actual_raised_by

        else: # FIVE_CARD_DRAW (Limit)
            # Get current raise count and minimum bet for limit
            raise_count = game.round_state.raise_count if game.round_state else 0
            # max_raises_per_round from config, e.g. game.config.max_raises_per_round
            if game.config.max_raises_per_round is not None and raise_count >= game.config.max_raises_per_round:
                PlayerLogger.log_message(f"{self.name} cannot raise. Max raises reached for the round. Calling instead.")
                self._call(game.current_bet, game)
                return

            # In limit, raise_by_amount is typically fixed (e.g., big_blind size)
            # For simplicity, assume raise_by_amount passed is the fixed amount for limit.
            # If variable limit raises, this needs more complex validation.
            fixed_raise_amount = game.big_blind # Or other configured limit raise size

            amount_to_call = game.current_bet - self.bet
            total_bet_this_action = amount_to_call + fixed_raise_amount
            
            self.place_bet(total_bet_this_action, game) # Handles all-in
            game.current_bet = self.bet
            game.last_raiser = self
            if game.round_state:
                game.round_state.raise_count += 1
                game.round_state.last_raiser = self.name
        PlayerLogger.log_player_action(self.name, "RAISE", raise_by_amount)


    def _call(self, current_total_bet_to_match: int, game) -> None:
        """Handle call action."""
        amount_to_call = current_total_bet_to_match - self.bet
        if amount_to_call <= 0: # Already matched or exceeded (e.g. posted blind)
            PlayerLogger.log_player_action(self.name, "CALL", 0, " (already matched or exceeded current bet)")
            self.checked = True # Effectively a check if no more amount needed
            return

        self.place_bet(amount_to_call, game) # place_bet handles all-in
        self.called = True
        PlayerLogger.log_player_action(self.name, "CALL", amount_to_call)


    def _check(self) -> None:
        """
        Mark the player as checked for the current hand.
        """
        if self.bet < game.current_bet: # Cannot check if there's a bet to call
             PlayerLogger.log_message(f"{self.name} cannot check, current bet is {game.current_bet} and player bet is {self.bet}. Folding instead or error.")
             # This should ideally be caught by agent's decide_action or betting_round logic
             # For now, let's assume valid checks. If not, an error or fold might occur.
             # Consider raising ValueError here if agent makes invalid check.
             # For robustness, if an agent *does* try to check here, and it's invalid,
             # it implies a logic error in the agent or the available actions given to it.
             # A simple fallback might be to fold, or re-prompt.
             # For now, just log and proceed, assuming agent.decide_action prevents this.
             PlayerLogger.log_player_action(self.name, "CHECK", 0, " (Invalid check attempt - bet pending)")
             # self._fold() # Or raise error
             return

        self.checked = True
        PlayerLogger.log_player_action(self.name, "CHECK", 0)


    def _fold(self) -> None:
        """
        Mark the player as folded for the current hand.

        Side Effects:
            - Sets player's folded status to True
            - Logs the fold action
        """
        self.folded = True
        PlayerLogger.log_player_action(self.name, "FOLD", 0)


    def reset_bet(self) -> None:
        """
        Reset the player's current bet to zero for the next betting round.

        Side Effects:
            - Resets bet amount to 0
            - Logs the previous bet amount and reset
        """
        previous_bet = self.bet
        self.bet = 0
        PlayerLogger.log_state_reset(self.name, previous_bet, "bet reset")

    def reset_for_new_round(self) -> None:
        """Reset player state for a new round."""
        self.bet = 0
        self.folded = False
        self.is_all_in = False
        self.checked = False
        self.called = False
        self._logged_all_in = False  # Reset the logging flag

        if hasattr(self, "hand"): # Check if hand exists before trying to access it
            self.hand = None
        self.best_hand_evaluation = None # Reset best hand evaluation

        PlayerLogger.log_state_reset(self.name, context="new round")

    @property
    def position(self) -> PlayerPosition:
        """Get the player's current position at the table."""
        return self._position

    @position.setter
    def position(self, value: PlayerPosition):
        """Set the player's position at the table."""
        old_position = getattr(self, "_position", None)
        self._position = value
        PlayerLogger.log_position_change(
            self.name, value.name, old_position.name if old_position else None
        )

    def get_state(self) -> PlayerState:
        """Get the current state of this player."""
        return PlayerState.from_player(self)

    def __str__(self) -> str:
        """
        Create a string representation of the player's current state.

        Returns:
            str: A formatted string showing the player's name, chip count,
                 and whether they have folded
        """
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"

    def __eq__(self, other):
        """Compare two players for equality.

        Players are considered equal if they have the same name.
        """
        if not isinstance(other, Player):
            return False
        return self.name == other.name

    def __hash__(self):
        """Hash function for Player objects.

        This is required when implementing __eq__ to maintain hashability.
        """
        return hash(self.name)
