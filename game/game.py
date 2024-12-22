import logging
from typing import List, Tuple

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player


class PokerGame:
    """
    Manages a poker game with multiple players, handling betting rounds and game flow.

    This class implements a complete poker game, managing the deck, players, betting rounds,
    and game progression. It supports multiple players, handles side pots, and manages
    player eliminations.

    Attributes:
        deck (Deck): The deck of cards used in the game.
        players (List[Player]): List of active players in the game.
        pot (int): Current pot amount in chips.
        small_blind (int): Small blind amount in chips.
        big_blind (int): Big blind amount in chips.
        dealer_index (int): Current dealer position (rotates clockwise each hand).
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
        Collect blinds and antes from players at the start of each hand.

        This method:
        1. Collects a 1-chip ante from each player with chips
        2. Collects the small blind from the player left of the dealer
        3. Collects the big blind from the player two positions left of the dealer
        4. Rotates the dealer position clockwise

        Side Effects:
            - Updates player chip counts
            - Updates the pot
            - Moves the dealer position
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

        Creates separate pots when players are all-in for different amounts, ensuring
        fair distribution of chips based on the amount each player contributed.

        Returns:
            List[Tuple[int, List[Player]]]: List of tuples where each tuple contains:
                - int: The amount in this pot
                - List[Player]: Players eligible to win this pot
        """
        # Get only players who contributed to the pot
        active_players = [p for p in self.players if p.bet > 0]
        if not active_players:
            return [(self.pot, self.players)]

        active_players.sort(key=lambda p: p.bet)

        pots = []
        remaining_pot = self.pot
        previous_bet = 0

        while active_players:
            current_bet = active_players[0].bet
            bet_difference = current_bet - previous_bet
            pot_contribution = bet_difference * len(active_players)

            if pot_contribution > 0:
                pots.append((pot_contribution, active_players[:]))
                remaining_pot -= pot_contribution

            previous_bet = current_bet
            active_players = active_players[1:]

        # If there's any remaining pot amount (from antes or odd chips), add it to the first pot
        if remaining_pot > 0 and pots:
            pots[0] = (pots[0][0] + remaining_pot, pots[0][1])

        return pots

    def showdown(self) -> None:
        """
        Determine the winner(s) of the hand and distribute the pot(s).

        This method:
        1. Identifies active (non-folded) players
        2. Handles single winner scenarios
        3. Compares hands for multiple active players
        4. Splits pots evenly among tied winners
        5. Distributes any remainder chips
        6. Resets betting state for next hand

        Side Effects:
            - Updates player chip counts
            - Resets player bets to 0
            - Resets the pot to 0
            - Logs winning hands and chip distributions
        """
        # Only consider non-folded players
        active_players = [p for p in self.players if not p.folded]

        if len(active_players) == 1:
            # If only one player remains, they win the whole pot
            winner = active_players[0]
            logging.info(f"Pot size before distribution: ${self.pot}")
            logging.info(f"{winner.name}'s chips before winning: ${winner.chips}")
            winner.chips += self.pot
            logging.info(f"{winner.name} wins ${self.pot} chips!")
            logging.info(f"{winner.name}'s final chips: ${winner.chips}")
        else:
            # Find the best hand among active players
            best_hand = max(p.hand for p in active_players)
            winners = [p for p in active_players if p.hand == best_hand]

            # Split pot evenly among winners
            split_amount = self.pot // len(winners)
            remainder = self.pot % len(winners)

            for winner in winners:
                logging.info(f"{winner.name}'s chips before winning: ${winner.chips}")
                winner.chips += split_amount
                logging.info(
                    f"{winner.name} wins ${split_amount} chips with {winner.hand}!"
                )
                logging.info(f"{winner.name}'s chips after winning: ${winner.chips}")

            # Give any remainder to the first winner
            if remainder > 0:
                winners[0].chips += remainder
                logging.info(
                    f"{winners[0].name} wins ${remainder} extra chips (remainder)!"
                )
                logging.info(f"{winners[0].name}'s final chips: ${winners[0].chips}")

        # Reset all bets and pot
        for player in self.players:
            player.bet = 0
        self.pot = 0

    def remove_bankrupt_players(self) -> bool:
        """
        Remove players who have no chips left and check game ending conditions.

        Removes players with zero chips and determines if the game should continue
        based on the number of remaining players.

        Returns:
            bool: True if the game should continue, False if the game should end
                 (0 or 1 players remaining)

        Side Effects:
            - Updates the players list
            - Logs game ending messages if applicable
        """
        self.players = [player for player in self.players if player.chips > 0]

        # If only one player remains, declare them the winner and end the game
        if len(self.players) == 1:
            logging.info(
                f"\nGame Over! {self.players[0].name} wins with {self.players[0].chips} chips!"
            )
            return False
        elif len(self.players) == 0:
            logging.info("\nGame Over! All players are bankrupt!")
            return False

        return True

    def start_game(self) -> None:
        """
        Start and manage the main game loop until completion.

        This method controls the main game flow:
        1. Checks for minimum player count
        2. Manages game rounds including:
            - Removing bankrupt players
            - Dealing cards
            - Collecting blinds and antes
            - Managing betting rounds
            - Handling showdowns
        3. Continues until a winner is determined

        Side Effects:
            - Updates all game state
            - Logs game progress and results
        """
        # Initial check for minimum players
        if len(self.players) < 2:
            logging.info(
                f"\nGame Over! {self.players[0].name} wins with {self.players[0].chips} chips!"
            )
            return

        while True:
            # Remove bankrupt players and check remaining count
            self.remove_bankrupt_players()

            if len(self.players) < 2:
                logging.info(
                    f"\nGame Over! {self.players[0].name} wins with {self.players[0].chips} chips!"
                )
                return

            # Reset for new round
            self.deck = Deck()
            self.deck.shuffle()
            self.blinds_and_antes()

            for player in self.players:
                player.folded = False
                player.hand = Hand()
                player.hand.add_cards(self.deck.deal(5))

            logging.info("\n--- Pre-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            # Check if only one player remains after betting
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                winner = active_players[0]
                winner.chips += self.pot  # Award pot before ending
                logging.info(
                    f"\nGame Over! {winner.name} wins with {winner.chips} chips!"
                )
                return

            logging.info("\n--- Post-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                winner = active_players[0]
                winner.chips += self.pot  # Award pot before ending
                logging.info(
                    f"\nGame Over! {winner.name} wins with {winner.chips} chips!"
                )
                return

            self.showdown()
