import logging
from typing import List, Tuple

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player


class PokerGame:
    """
    A 5-card draw poker game manager that handles multiple players and betting rounds.

    Manages the complete game flow including dealing cards, collecting blinds/antes,
    handling betting rounds, and determining winners. Supports side pots and tracks
    player eliminations.

    Attributes:
        deck (Deck): The deck of cards for dealing.
        players (List[Player]): Currently active players in the game.
        pot (int): Total chips in the current pot.
        small_blind (int): Required small blind bet amount.
        big_blind (int): Required big blind bet amount.
        dealer_index (int): Position of current dealer (0-based, moves clockwise).
        round_count (int): Number of completed game rounds.
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
        self.round_count = 0

    def blinds_and_antes(self) -> None:
        """
        Collect mandatory bets (blinds and antes) at the start of each hand.

        Processes in order:
        1. Collects 1-chip ante from each player who has chips
        2. Collects small blind from player left of dealer
        3. Collects big blind from player two left of dealer
        4. Advances dealer position clockwise

        Note: Players cannot bet more than their remaining chips.
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
        Calculate and split the pot when players are all-in with different amounts.

        Creates separate pots based on the maximum amount each player could contribute,
        ensuring fair distribution when players have gone all-in for different amounts.

        Returns:
            List of tuples, each containing:
            - int: The amount in this side pot
            - List[Player]: Players eligible to win this specific pot, sorted by bet size
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
        Evaluate hands and distribute pot(s) to the winner(s).

        Handles:
        - Single winner scenarios (all others folded)
        - Multiple active players with hand comparisons
        - Equal splitting of pots among tied winners
        - Distribution of remainder chips to first winner
        - Resetting of betting state for next hand

        Logs all chip movements and winning hands for transparency.
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
        Remove players with zero chips and check if game should continue.

        Removes bankrupt players from the game and determines if enough players
        remain to continue playing.

        Returns:
            bool: True if game should continue (2+ players remain),
                 False if game should end (0-1 players remain)
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
        Execute the main game loop until a winner is determined.

        Game flow:
        1. Verify minimum 2 players to start
        2. For each round:
           - Remove bankrupt players
           - Deal new hands
           - Collect blinds/antes
           - Run pre-draw betting
           - Run post-draw betting
           - Handle showdown
        3. Log final game statistics and standings

        The game ends when only 0-1 players remain with chips.
        """
        # Initial check for minimum players
        if len(self.players) < 2:
            logging.info(
                f"\nGame Over! {self.players[0].name} wins with {self.players[0].chips} chips!"
            )
            return

        while True:
            self.round_count += 1
            # Remove bankrupt players and check remaining count
            if not self.remove_bankrupt_players():
                break  # Game is over, will log summary after loop

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
                winner.chips += self.pot
                break  # Game is over, will log summary after loop

            logging.info("\n--- Post-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                winner = active_players[0]
                winner.chips += self.pot
                break  # Game is over, will log summary after loop

            self.showdown()

        # Log game summary after any ending condition
        # Sort all players by final chip count
        final_standings = sorted(self.players, key=lambda p: p.chips, reverse=True)

        logging.info("\n=== Game Summary ===")
        logging.info(f"Total rounds played: {self.round_count}")
        logging.info("\nFinal Standings:")
        for i, player in enumerate(final_standings, 1):
            logging.info(f"{i}. {player.name}: ${player.chips}")

        # Log bankrupt players if any
        bankrupt_players = [p for p in self.players if p.chips == 0]
        if bankrupt_players:
            logging.info("\nBankrupt Players:")
            for player in bankrupt_players:
                logging.info(f"- {player.name}")
