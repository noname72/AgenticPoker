import logging
from typing import List, Optional, Tuple

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
        deck (Deck): The deck of cards used for dealing.
        players (List[Player]): List of currently active players in the game.
        pot (int): Total chips in the current pot.
        small_blind (int): Required small blind bet amount.
        big_blind (int): Required big blind bet amount.
        dealer_index (int): Position of current dealer (0-based, moves clockwise).
        round_count (int): Number of completed game rounds.
        round_number (int): Current round number (increments at start of each round).
        max_rounds (Optional[int]): Maximum number of rounds to play, or None for unlimited.
    """

    def __init__(
        self,
        players,  # Can be list of names or list of Player objects
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
        max_rounds: Optional[int] = None,
    ) -> None:
        """
        Initialize a new poker game.

        Args:
            players: List of player names or Player objects
            starting_chips: Initial chip amount for each player
            small_blind: Small blind bet amount
            big_blind: Big blind bet amount
            max_rounds: Maximum number of rounds to play (None for unlimited)
        """
        self.deck = Deck()
        # Convert names to players if needed
        if players and isinstance(players[0], str):
            self.players = [Player(name, starting_chips) for name in players]
        else:
            self.players = players  # Use provided Player objects
        self.pot = 0
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.dealer_index = 0
        self.round_count = 0
        self.round_number = 0
        self.max_rounds = max_rounds
        logging.info(f"\n{'='*50}")
        logging.info(f"Game started with {len(players)} players")
        logging.info(f"Starting chips: ${starting_chips}")
        logging.info(f"Blinds: ${small_blind}/${big_blind}")
        if max_rounds:
            logging.info(f"Max rounds: {max_rounds}")
        logging.info(f"Players: {', '.join([p.name for p in players])}")
        logging.info(f"{'='*50}\n")

    def blinds_and_antes(self) -> None:
        """
        Collect mandatory bets (blinds and antes) at the start of each hand.
        """
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        # Collect antes first (if using antes)
        ante_amount = 1  # Consider making this configurable
        total_antes = 0
        if ante_amount > 0:  # Only collect and log antes if they're being used
            logging.info("\nCollecting antes ($1 from each player)...")
            for player in self.players:
                if player.chips > 0:
                    actual_ante = player.place_bet(ante_amount)
                    total_antes += actual_ante
                    if actual_ante > 0:
                        logging.info(f"{player.name} posts ante of ${actual_ante}")
            if total_antes > 0:
                self.pot += total_antes
                logging.info(f"Total antes collected: ${total_antes}")

        # Collect blinds
        logging.info("\nCollecting blinds...")

        # Small blind
        sb_player = self.players[sb_index]
        sb_amount = min(self.small_blind, sb_player.chips)
        actual_sb = sb_player.place_bet(sb_amount)
        self.pot += actual_sb
        logging.info(f"{sb_player.name} posts small blind of ${actual_sb}")

        # Big blind
        bb_player = self.players[bb_index]
        bb_amount = min(self.big_blind, bb_player.chips)
        actual_bb = bb_player.place_bet(bb_amount)
        self.pot += actual_bb
        logging.info(f"{bb_player.name} posts big blind of ${actual_bb}")

        # Log total pot after all mandatory bets
        logging.info(f"\nStarting pot: ${self.pot} (includes ${total_antes} in antes)")

        # Advance dealer position
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def handle_side_pots(self) -> List[Tuple[int, List[Player]]]:
        """
        Calculate and split the pot when players are all-in with different amounts.

        Creates separate pots based on the maximum amount each player could contribute,
        ensuring fair distribution when players have gone all-in for different amounts.
        Side pots are created in ascending order of bet sizes.

        Returns:
            List[Tuple[int, List[Player]]]: List of tuples where each contains:
                - int: The amount in this side pot
                - List[Player]: Players eligible to win this specific pot, sorted by bet size

        Example:
            If players A, B, C bet 100, 200, 300 respectively:
            [(100, [A, B, C]), (100, [B, C]), (100, [C])]
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
        Handle the showdown phase of the poker game.

        Determines winner(s) and distributes pot(s) according to poker rules:
        1. If only one active player remains, they win the entire pot
        2. For multiple players, handles side pots for all-in situations
        3. Compares hands of remaining players to determine winner(s)
        4. Splits pots equally among tied winners

        Side effects:
            - Updates player chip counts
            - Logs detailed pot distribution and chip movements
            - Resets pot to 0 after distribution
        """
        logging.info(f"\n{'='*20} SHOWDOWN {'='*20}")

        active_players = [p for p in self.players if not p.folded]

        # Single player remaining (everyone else folded)
        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.pot
            logging.info(f"\n{winner.name} wins ${self.pot} uncontested!")
            self._log_chip_summary()
            return

        # All-in showdown
        all_in_players = [p for p in active_players if p.chips == 0]
        if len(all_in_players) == len(active_players):
            logging.info("\nAll players are all-in!")

        # Multiple players - handle side pots
        side_pots = self.handle_side_pots()

        # Track initial chips before distribution
        initial_chips = {p: p.chips for p in self.players}

        logging.info("\nPot distribution:")
        for pot_amount, eligible_players in side_pots:
            if not eligible_players:
                continue

            logging.info(f"  Pot amount: ${pot_amount}")
            logging.info(f"  Eligible players: {[p.name for p in eligible_players]}")

            # Find winner(s) for this pot
            best_hand = max(p.hand for p in eligible_players)
            pot_winners = [p for p in eligible_players if p.hand == best_hand]

            # Split the pot
            split_amount = pot_amount // len(pot_winners)
            remainder = pot_amount % len(pot_winners)

            for winner in pot_winners:
                winner.chips += split_amount
                if remainder > 0:
                    winner.chips += 1
                    remainder -= 1

                logging.info(
                    f"  {winner.name} wins ${split_amount} with {winner.hand.evaluate()}"
                )

        # Log detailed chip movements
        logging.info("\nChip movement summary:")
        for player in self.players:
            net_change = player.chips - initial_chips[player]
            logging.info(f"  {player.name}:")
            logging.info(f"    Starting chips: ${initial_chips[player]}")
            logging.info(
                f"    Net change: ${net_change:+d}"
            )  # +:d shows + for positive numbers
            logging.info(f"    Final chips: ${player.chips}")

        self._log_chip_summary()

    def _log_chip_summary(self) -> None:
        """Log a summary of all players' chip counts, sorted by amount."""
        logging.info("\nFinal chip counts (sorted by amount):")
        # Sort players by chip count, descending
        sorted_players = sorted(self.players, key=lambda p: p.chips, reverse=True)
        for player in sorted_players:
            logging.info(f"  {player.name}: ${player.chips}")
        logging.info(f"{'='*50}\n")

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
        Execute the main game loop until a winner is determined or max rounds reached.

        Game flow:
        1. Remove players who can't afford big blind
        2. Deal cards and collect blinds/antes
        3. Run pre-draw betting round
        4. Handle draw phase (discard/draw)
        5. Run post-draw betting round
        6. Showdown or award pot to last player
        7. Repeat until only one player remains or max rounds reached

        Side effects:
            - Updates player chip counts
            - Eliminates bankrupt players
            - Tracks and logs round count
            - Logs final game results
        """
        while len(self.players) > 1:
            # Check if max rounds reached
            if self.max_rounds and self.round_count >= self.max_rounds:
                logging.info(f"\nGame ended after {self.max_rounds} rounds!")
                break

            # Remove players with less than big blind
            self.players = [p for p in self.players if p.chips >= self.big_blind]
            if len(self.players) < 2:
                break

            # Start new round
            self.start_round()
            self.blinds_and_antes()

            # Pre-draw betting
            logging.info("\n--- Pre-Draw Betting ---")
            initial_chips = {p: p.chips for p in self.players}  # Track starting chips
            self.pot = betting_round(self.players, self.pot)

            # Check if only one player remains after pre-draw betting
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                winner = active_players[0]
                winner.chips += self.pot
                logging.info(f"\n{winner.name} wins ${self.pot} (all others folded)")
                # Log chip movements
                for player in self.players:
                    if player.chips != initial_chips[player]:
                        logging.info(
                            f"{player.name}: ${initial_chips[player]} → ${player.chips}"
                        )
                self._log_chip_summary()
                self.round_count += 1
                self._reset_round()  # Reset for next round
                continue

            # Draw phase
            self.draw_phase()

            # Post-draw betting
            logging.info("\n--- Post-Draw Betting ---")
            self.pot = betting_round(self.players, self.pot)

            # Handle showdown or single winner
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) > 1:
                self.showdown()
            else:
                winner = active_players[0]
                winner.chips += self.pot
                logging.info(f"\n{winner.name} wins ${self.pot} (all others folded)")
                self._log_chip_summary()

            # After showdown or single winner
            for player in self.players:
                if player.chips != initial_chips[player]:
                    logging.info(
                        f"{player.name}: ${initial_chips[player]} → ${player.chips}"
                    )

            self.round_count += 1
            self._reset_round()  # Reset for next round

        # Log final game results
        logging.info("\n=== Game Summary ===")
        logging.info(f"Total rounds played: {self.round_count}")
        if self.max_rounds and self.round_count >= self.max_rounds:
            logging.info("Game ended due to maximum rounds limit")
        logging.info("\nFinal Standings:")
        for i, player in enumerate(
            sorted(self.players, key=lambda p: p.chips, reverse=True), 1
        ):
            logging.info(f"{i}. {player.name}: ${player.chips}")
        logging.info("\nFinal Standings:")
        for i, player in enumerate(
            sorted(self.players, key=lambda p: p.chips, reverse=True), 1
        ):
            logging.info(f"{i}. {player.name}: ${player.chips}")

    def start_round(self) -> None:
        """
        Start a new round of poker.

        Performs round initialization:
        1. Increments round counter
        2. Resets pot and deck
        3. Deals new 5-card hands to all players
        4. Resets player states (bets, folded status)
        5. Logs round information (dealer, blinds, chip counts)

        Side effects:
            - Updates round_number
            - Resets pot to 0
            - Creates new shuffled deck
            - Deals cards to players
            - Logs round start information

        Note:
            AI players can implement get_message() to provide pre-round
            table talk that will be included in the logs
        """
        self.round_number += 1
        self.pot = 0  # Reset pot at start of round

        logging.info(f"\n{'='*50}")
        logging.info(f"Round {self.round_number}")
        logging.info(f"{'='*50}")

        # Reset deck and deal new hands
        self.deck = Deck()
        self.deck.shuffle()
        for player in self.players:
            player.bet = 0  # Reset player bets
            player.folded = False  # Reset folded status
            player.hand = Hand()  # Reset hand
            player.hand.add_cards(self.deck.deal(5))  # Deal new cards

        # Log player states at start of round
        logging.info("\nChip counts:")
        for player in self.players:
            logging.info(f"  {player.name}: ${player.chips}")

        # Log dealer and blind positions
        dealer = self.players[self.dealer_index].name
        sb_player = self.players[(self.dealer_index + 1) % len(self.players)].name
        bb_player = self.players[(self.dealer_index + 2) % len(self.players)].name
        logging.info(f"\nDealer: {dealer}")
        logging.info(f"Small Blind: {sb_player}")
        logging.info(f"Big Blind: {bb_player}")

        # Let AI players send pre-round messages
        for player in self.players:
            if hasattr(player, "get_message"):
                game_state = f"Round {self.round_number}, Your chips: ${player.chips}"
                message = player.get_message(game_state)
                if message:
                    # Remove or replace problematic characters
                    message = message.encode("ascii", "replace").decode("ascii")
                    logging.info(f"\n{player.name} says: {message}")

        logging.info("\n")

    def draw_phase(self) -> None:
        """
        Handle the draw phase where players can discard and draw new cards.

        For each non-folded player:
        1. Shows current hand
        2. For AI players: Uses decide_draw() method to choose discards
        3. For human players: Currently keeps all cards (placeholder)
        4. Removes discarded cards and deals replacements
        5. Shows new hand after draw

        Side effects:
            - Modifies player hands by removing discards
            - Deals new cards from deck to replace discards
            - Logs all draw actions and hand changes

        Note:
            AI players must implement decide_draw() method that returns
            a list of indices (0-4) indicating which cards to discard.
            The method should return an empty list to keep all cards.
        """
        logging.info("\n--- Draw Phase ---")
        for player in self.players:
            if player.folded:
                continue

            logging.info(f"\n{player.name}'s turn to draw")
            logging.info(f"Current hand: {player.hand.show()}")

            if hasattr(player, "decide_draw"):
                # AI players decide which cards to discard
                discards = player.decide_draw()
                if discards:
                    # Remove discarded cards
                    player.hand.cards = [
                        card
                        for i, card in enumerate(player.hand.cards)
                        if i not in discards
                    ]
                    # Draw new cards
                    new_cards = self.deck.deal(len(discards))
                    player.hand.add_cards(new_cards)
                    logging.info(f"Drew {len(discards)} new cards")
                    logging.info(f"New hand: {player.hand.show()}")
            else:
                # Non-AI players keep their hand
                logging.info("Keeping current hand")

    def _reset_round(self) -> None:
        """Reset game state for the next round."""
        self.pot = 0
        for player in self.players:
            player.reset_for_new_round()
