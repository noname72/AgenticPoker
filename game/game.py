from typing import List, Tuple

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player


class PokerGame:
    """
    Manages a poker game with multiple players, handling betting rounds and game flow.

    Attributes:
        deck (Deck): The deck of cards used in the game
        players (List[Player]): List of players in the game
        pot (int): Current pot amount
        small_blind (int): Small blind amount
        big_blind (int): Big blind amount
        dealer_index (int): Current dealer position
    """

    def __init__(
        self,
        player_names: List[str],
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
    ) -> None:
        """
        Initialize a new poker game.

        Args:
            player_names: List of player names to create players
            starting_chips: Initial chip amount for each player
            small_blind: Small blind bet amount
            big_blind: Big blind bet amount
        """
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.dealer_index = 0

    def blinds_and_antes(self) -> None:
        """
        Collect blinds and antes from players.
        Updates the pot and player chip counts accordingly.
        """
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        for player in self.players:
            if player.chips > 0:
                player.place_bet(1)
                self.pot += 1

        sb_player = self.players[sb_index]
        sb_player.place_bet(min(self.small_blind, sb_player.chips))
        self.pot += min(self.small_blind, sb_player.chips)

        bb_player = self.players[bb_index]
        bb_player.place_bet(min(self.big_blind, bb_player.chips))
        self.pot += min(self.big_blind, bb_player.chips)

        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def handle_side_pots(self) -> List[Tuple[int, List[Player]]]:
        """
        Calculate side pots when players are all-in with different amounts.

        Returns:
            List of tuples containing (pot_amount, eligible_players)
        """
        active_players = [p for p in self.players if p.bet > 0]
        active_players.sort(key=lambda p: p.bet)

        pots = []
        while active_players:
            min_bet = active_players[0].bet
            pot_total = 0
            for player in active_players:
                pot_total += min_bet
                player.bet -= min_bet
            pots.append((pot_total, [p for p in active_players]))
            active_players = [p for p in active_players if p.bet > 0]
        return pots

    def showdown(self) -> None:
        """
        Determine the winner(s) of the hand and distribute the pot(s).
        Handles multiple winners and side pots.
        """
        pots = self.handle_side_pots()
        for pot, eligible_players in pots:
            active_players = [p for p in eligible_players if not p.folded]

            if not active_players:
                continue

            winner, best_hand = max(
                ((player, player.hand) for player in active_players), key=lambda x: x[1]
            )
            print(f"\n{winner.name} wins {pot} chips!")
            winner.chips += pot

    def remove_bankrupt_players(self) -> bool:
        """
        Remove players who have run out of chips.

        Returns:
            bool: True if game should continue, False if game should end
        """
        self.players = [p for p in self.players if p.chips > 0]
        if len(self.players) == 1:
            print(
                f"\nGame Over! {self.players[0].name} wins with {self.players[0].chips} chips!"
            )
            return False
        elif len(self.players) < 1:
            print("\nGame Over! No players remaining!")
            return False
        return True

    def start_game(self) -> None:
        """
        Start and manage the main game loop.
        Handles dealing, betting rounds, and showdown until game completion.
        """
        while self.remove_bankrupt_players():
            self.deck = Deck()
            self.deck.shuffle()
            self.blinds_and_antes()

            for player in self.players:
                player.hand = Hand()
                player.hand.add_cards(self.deck.deal(5))

            print("\n--- Pre-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            print("\n--- Post-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            self.showdown()
