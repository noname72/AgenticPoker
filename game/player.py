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

        Side Effects:
            - Creates a new empty Hand instance
            - Initializes player state (bet=0, folded=False)
        """
        self.name = name
        self.chips = chips
        self.bet = 0
        self.folded = False
        self.hand = Hand()

    def place_bet(self, amount: int) -> int:
        """
        Place a bet for the player, handling all-in situations automatically.

        If the requested bet amount exceeds the player's chips, the player goes
        all-in with their remaining chips instead.

        Args:
            amount (int): The amount of chips to bet

        Returns:
            int: The actual amount bet (may be less than requested if player goes all-in)

        Side Effects:
            - Reduces player's chip count
            - Increases player's current bet
            - Logs betting actions and all-in situations
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

    def __str__(self) -> str:
        """
        Create a string representation of the player's current state.

        Returns:
            str: A formatted string showing the player's name, chip count,
                 and whether they have folded
        """
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"
