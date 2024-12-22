import logging
from .hand import Hand


class Player:
    """
    Represents a poker player with chips, betting capability, and a hand of cards.

    Attributes:
        name (str): The player's name
        chips (int): The amount of chips the player has
        bet (int): The current bet amount for this round
        folded (bool): Whether the player has folded their hand
        hand (Hand): The player's current hand of cards
    """

    name: str
    chips: int
    bet: int
    folded: bool
    hand: Hand

    def __init__(self, name: str, chips: int = 1000) -> None:
        """
        Initialize a new player.

        Args:
            name (str): The player's name
            chips (int, optional): Starting amount of chips. Defaults to 1000.
        """
        self.name = name
        self.chips = chips
        self.bet = 0
        self.folded = False
        self.hand = Hand()

    def place_bet(self, amount: int) -> int:
        """
        Place a bet for the player, adjusting for all-in situations.

        Args:
            amount (int): The amount to bet

        Returns:
            int: The actual amount bet (may be less than requested if player goes all-in)
        """
        if amount > self.chips:
            logging.info(f"{self.name} is all in with {self.chips} chips!")
            amount = self.chips
        
        logging.debug(f"{self.name} betting {amount} chips (had {self.chips})")
        self.chips -= amount
        self.bet += amount
        logging.debug(f"{self.name} now has {self.chips} chips and bet {self.bet}")
        return amount

    def fold(self) -> None:
        """Mark the player as folded for the current hand."""
        logging.debug(f"{self.name} folded")
        self.folded = True

    def reset_bet(self) -> None:
        """Reset the player's current bet to zero."""
        previous_bet = self.bet
        self.bet = 0
        logging.debug(f"{self.name}'s bet reset from {previous_bet} to 0")

    def __str__(self) -> str:
        """
        Return a string representation of the player.

        Returns:
            str: Player's name, chip count, and fold status
        """
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"
