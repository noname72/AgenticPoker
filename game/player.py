import logging
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
    """

    name: str
    chips: int
    bet: int
    folded: bool
    hand: Hand

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

        amount = min(amount, self.chips)  # Can't bet more than you have
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
        logging.debug(f"{self.name}'s state reset for new round")

    def __str__(self) -> str:
        """
        Create a string representation of the player's current state.

        Returns:
            str: A formatted string showing the player's name, chip count,
                 and whether they have folded
        """
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"

    def decide_action(self, game_state: str) -> str:
        """Decide what action to take based on current game state."""
        # Get hand evaluation before making decision
        hand_eval = self.hand.evaluate() if self.hand else None

        if self.strategy_planner:
            # Pass hand evaluation info to strategy planner
            return self.strategy_planner.execute_action(game_state, hand_eval)

        # Fallback to basic decision making if no strategy planner
        return self._basic_decision(game_state)
