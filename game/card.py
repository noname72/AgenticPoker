class Card:
    """
    Represents a single playing card with rank and suit.
    
    A card is immutable after creation and provides a string
    representation for display and logging purposes.
    
    Attributes:
        rank (str): The card's rank ('2'-'10', 'J', 'Q', 'K', 'A')
        suit (str): The card's suit ('Clubs', 'Diamonds', 'Hearts', 'Spades')
    """
    
    def __init__(self, rank: str, suit: str):
        """
        Initialize a new card with specified rank and suit.
        
        Args:
            rank (str): The card's rank value
            suit (str): The card's suit name
        """
        self.rank = rank
        self.suit = suit
    
    def __repr__(self) -> str:
        """
        Returns string representation of the card.
        
        Returns:
            str: Card in format "rank of suit"
        """
        return f"{self.rank} of {self.suit}"
