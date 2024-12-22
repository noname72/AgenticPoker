import random
from .card import Card

class Deck:
    ranks = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"]
    suits = ["Clubs", "Diamonds", "Hearts", "Spades"]
    
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]
    
    def shuffle(self):
        random.shuffle(self.cards)
    
    def deal(self, num=1):
        dealt_cards = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt_cards
