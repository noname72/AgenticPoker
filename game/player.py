import logging
from typing import TYPE_CHECKING

from data.states.player_state import PlayerState
from data.types.player_types import PlayerPosition

from .hand import Hand


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
    chips: int
    bet: int
    folded: bool
    hand: Hand
    position: PlayerPosition

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
        self.folded = False
        self.hand = Hand()
        self.position = PlayerPosition.OTHER
        self.is_all_in = False

    def place_bet(self, amount: int) -> int:
        """
        Place a bet, ensuring it doesn't exceed available chips.

        Args:
            amount (int): Amount to bet

        Returns:
            int: Actual amount bet (may be less than requested if limited by chips)

        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError("Cannot place negative bet")

        # Ensure we don't bet more than available chips
        amount = min(amount, self.chips)

        # If this is a raise, ensure it's at least double the current bet
        #! is this needed???
        if hasattr(self, "current_bet") and amount <= self.current_bet:
            logging.debug(
                f"Raise amount {amount} too small compared to current bet {self.current_bet}"
            )
            amount = self.current_bet * 2
            amount = min(
                amount, self.chips
            )  # Still ensure we don't exceed available chips

        self.chips -= amount
        self.bet += amount
        logging.debug(
            f"{self.name} bets ${amount} (total bet: ${self.bet}, chips left: ${self.chips})"
        )
        return amount

    def fold(self) -> None:
        """
        Mark the player as folded for the current hand.

        Side Effects:
            - Sets player's folded status to True
            - Logs the fold action
        """
        logging.debug(f"{self.name} folded")
        self.folded = True

    def reset_bet(self) -> None:
        """
        Reset the player's current bet to zero for the next betting round.

        Side Effects:
            - Resets bet amount to 0
            - Logs the previous bet amount and reset
        """
        previous_bet = self.bet
        self.bet = 0
        logging.debug(f"{self.name}'s bet reset from {previous_bet} to 0")

    def reset_for_new_round(self) -> None:
        """Reset player state for a new round."""
        self.bet = 0
        self.folded = False
        self.total_bet_this_round = 0
        self.last_action = None
        self.last_raise_amount = None
        self.is_all_in = False
        self.is_dealer = False
        self.is_small_blind = False
        self.is_big_blind = False
        self.chips_at_start_of_hand = self.chips
        logging.debug(f"{self.name}'s state reset for new round")

    def __str__(self) -> str:
        """
        Create a string representation of the player's current state.

        Returns:
            str: A formatted string showing the player's name, chip count,
                 and whether they have folded
        """
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"

    def get_state(self) -> PlayerState:
        """Get the current state of this player."""
        return PlayerState.from_player(self)

    def update_from_state(self, state: PlayerState) -> None:
        #! do I really need this???
        """Update this player's attributes from a PlayerState."""
        self.name = state.name
        self.chips = state.chips
        self.bet = state.bet
        self.folded = state.folded

        # Update position and role attributes
        self.seat_number = state.seat_number
        self.is_dealer = state.is_dealer
        self.is_small_blind = state.is_small_blind
        self.is_big_blind = state.is_big_blind

        # Update betting state
        self.total_bet_this_round = state.total_bet_this_round
        self.last_action = state.last_action
        self.last_raise_amount = state.last_raise_amount

        # Update game status
        self.is_all_in = state.is_all_in
        self.chips_at_start_of_hand = state.chips_at_start_of_hand

        # Update historical stats
        self.hands_played = state.hands_played
        self.hands_won = state.hands_won
        self.total_winnings = state.total_winnings
        self.biggest_pot_won = state.biggest_pot_won
