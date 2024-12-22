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
        ante (int): Mandatory bet required from all players at start of each hand.
    """

    def __init__(
        self,
        players,
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
        max_rounds: Optional[int] = None,
        ante: int = 0,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Initialize a new poker game.

        Args:
            players (Union[List[str], List[Player]]): List of player names or Player objects.
            starting_chips (int, optional): Initial chip amount for each player. Defaults to 1000.
            small_blind (int, optional): Small blind bet amount. Defaults to 10.
            big_blind (int, optional): Big blind bet amount. Defaults to 20.
            max_rounds (Optional[int], optional): Maximum number of rounds to play. Defaults to None.
            ante (int, optional): Mandatory bet required from all players. Defaults to 0.
            session_id (Optional[str], optional): Unique identifier for this game session.
                If None, uses timestamp-based ID.

        Example:
            >>> game = PokerGame(['Alice', 'Bob', 'Charlie'], starting_chips=500)
            >>> game = PokerGame(player_list, small_blind=5, big_blind=10, ante=1)
        """
        # Initialize session-specific logging
        self.session_id = session_id

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
        self.ante = ante

        # Log game configuration with clear session context
        logging.info(f"\n{'='*50}")
        logging.info(f"Game Configuration")
        logging.info(f"{'='*50}")
        logging.info(f"Players: {', '.join([p.name for p in players])}")
        logging.info(f"Starting chips: ${starting_chips}")
        logging.info(f"Blinds: ${small_blind}/${big_blind}")
        logging.info(f"Ante: ${ante}")
        if max_rounds:
            logging.info(f"Max rounds: {max_rounds}")
        logging.info(f"{'='*50}\n")

    def blinds_and_antes(self) -> None:
        """
        Collect mandatory bets (blinds and antes) at the start of each hand.
        """
        # Calculate blind positions
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        # Collect antes first (if using antes)
        ante_amount = self.ante
        total_antes = 0
        if ante_amount > 0:
            logging.info("\nCollecting antes...")
            for player in self.players:
                if player.chips > 0:  # Any player with chips must post ante
                    actual_ante = min(
                        ante_amount, player.chips
                    )  # Can't ante more than you have
                    if actual_ante > 0:
                        actual_ante = player.place_bet(actual_ante)
                        total_antes += actual_ante
                        status = " (all in)" if player.chips == 0 else ""
                        logging.info(
                            f"{player.name} posts ante of ${actual_ante}{status}"
                        )
            if total_antes > 0:
                self.pot += total_antes
                logging.info(f"Total antes collected: ${total_antes}")

        # Collect blinds
        logging.info("\nCollecting blinds...")

        # Small blind - player can go all-in for less
        sb_player = self.players[sb_index]
        if sb_player.chips > 0:
            actual_sb = min(self.small_blind, sb_player.chips)
            actual_sb = sb_player.place_bet(actual_sb)
            self.pot += actual_sb
            status = " (all in)" if sb_player.chips == 0 else ""
            if actual_sb < self.small_blind:
                logging.info(
                    f"{sb_player.name} posts partial small blind of ${actual_sb}{status}"
                )
            else:
                logging.info(
                    f"{sb_player.name} posts small blind of ${actual_sb}{status}"
                )

        # Big blind - player can go all-in for less
        bb_player = self.players[bb_index]
        if bb_player.chips > 0:
            actual_bb = min(self.big_blind, bb_player.chips)
            actual_bb = bb_player.place_bet(actual_bb)
            self.pot += actual_bb
            status = " (all in)" if bb_player.chips == 0 else ""
            if actual_bb < self.big_blind:
                logging.info(
                    f"{bb_player.name} posts partial big blind of ${actual_bb}{status}"
                )
            else:
                logging.info(
                    f"{bb_player.name} posts big blind of ${actual_bb}{status}"
                )

        # Log total pot after all mandatory bets
        logging.info(
            f"\nStarting pot: ${self.pot}"
            + (f" (includes ${total_antes} in antes)" if total_antes > 0 else "")
        )

        # Advance dealer position to next player with chips
        current_index = (self.dealer_index + 1) % len(self.players)
        while self.players[current_index].chips == 0:
            current_index = (current_index + 1) % len(self.players)
        self.dealer_index = current_index

    def handle_side_pots(self) -> List[Tuple[int, List[Player]]]:
        """
        Calculate and split the pot when players are all-in with different amounts.

        Creates separate pots based on the maximum amount each player could contribute,
        ensuring fair distribution when players have gone all-in for different amounts.
        Side pots are created in ascending order of bet sizes.

        Returns:
            List[Tuple[int, List[Player]]]: List of tuples containing:
                - int: The amount in this side pot
                - List[Player]: Players eligible to win this specific pot

        Example:
            If players bet:
                - Player A: $100 (all-in)
                - Player B: $200 (all-in)
                - Player C: $300
            Returns:
                [(100, [A, B, C]),  # Main pot: all players eligible
                 (100, [B, C]),     # First side pot: only B and C eligible
                 (100, [C])]        # Second side pot: only C eligible
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

        Side Effects:
            - Updates player chip counts
            - Logs detailed pot distribution and chip movements
            - Resets pot to 0 after distribution

        Example:
            With three players and a $300 pot:
            - Player A (all-in): Pair of Kings
            - Player B (all-in): Two Pair
            - Player C: Fold
            Result: Player B wins the pot, chips are transferred, and results are logged
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

        # Multiple players - show hands and determine winner
        logging.info("\nFinal hands:")
        for player in active_players:
            logging.info(f"{player.name}: {player.hand.show()}")

        # Find best hand(s)
        best_hand = max(active_players, key=lambda p: p.hand)
        winners = [p for p in active_players if p.hand == best_hand.hand]

        # Handle pot distribution
        pot_share = self.pot // len(winners)  # Split pot evenly among winners
        remainder = self.pot % len(winners)  # Handle any odd chips

        logging.info("\nPot distribution:")
        logging.info(f"  - Pot amount: ${self.pot}")
        logging.info(f"  - Eligible players: {[p.name for p in active_players]}")

        for winner in winners:
            # First winner gets any odd chips from the split
            chips_won = pot_share + (remainder if winner == winners[0] else 0)
            winner.chips += chips_won
            # Show if this was an all-in win
            all_in_status = " (all-in)" if winner.chips == chips_won else ""
            logging.info(
                f"  - {winner.name} wins ${chips_won}{all_in_status} with {winner.hand.evaluate()}"
            )

        # Verify pot was fully distributed
        total_distributed = pot_share * len(winners) + remainder
        if total_distributed != self.pot:
            logging.error(
                f"Error: Pot distribution mismatch! Pot: ${self.pot}, Distributed: ${total_distributed}"
            )

        # Log chip movements
        logging.info("\nChip movement summary:")
        for player in self.players:
            true_starting_stack = self.round_starting_stacks[player]
            net_change = player.chips - true_starting_stack
            logging.info(f"  {player.name}:")
            logging.info(
                f"    Starting stack (pre-ante/blinds): ${true_starting_stack}"
            )
            logging.info(f"    Net change: ${net_change:+d}")
            logging.info(f"    Final stack: ${player.chips}")

        self._log_chip_summary()

    def _log_chip_summary(self) -> None:
        """
        Log a summary of all players' chip counts, sorted by amount.

        Creates a formatted log entry showing each player's current chip count,
        sorted in descending order by amount.

        Side Effects:
            - Writes to game log with current chip counts
            - Adds separator lines for readability
        """
        logging.info("\nFinal chip counts (sorted by amount):")
        # Sort players by chip count, descending
        sorted_players = sorted(self.players, key=lambda p: p.chips, reverse=True)
        for player in sorted_players:
            logging.info(f"  {player.name}: ${player.chips}")
        logging.info(f"{'='*50}\n")

    def remove_bankrupt_players(self) -> bool:
        """
        Remove players with zero chips and check if game should continue.
        Players are only removed when they have exactly 0 chips.
        """
        # Only remove players with exactly 0 chips
        self.players = [player for player in self.players if player.chips > 0]

        # If only one player remains, declare them the winner and end the game
        if len(self.players) == 1:
            logging.info(
                f"\nGame Over! {self.players[0].name} wins with ${self.players[0].chips}!"
            )
            return False
        elif len(self.players) == 0:
            logging.info("\nGame Over! All players are bankrupt!")
            return False

        return True

    def start_game(self) -> None:
        """
        Execute the main game loop until a winner is determined or max rounds reached.

        Controls the overall flow of the poker game, managing rounds until an end condition
        is met. Each round consists of:
        1. Pre-draw betting (including blinds/antes)
        2. Draw phase (players can discard and draw new cards)
        3. Post-draw betting
        4. Showdown (if multiple players remain)

        Game End Conditions:
            - Only one player has chips remaining
            - Maximum number of rounds reached (if specified)

        Side Effects:
            - Updates player chip counts
            - Tracks eliminated players
            - Logs all game actions and results
            - Produces final standings and game summary

        Example Round Flow:
            1. Collect blinds/antes
            2. Pre-draw betting round
            3. Players discard and draw new cards
            4. Post-draw betting round
            5. Winner determination:
               - Single player remaining (others folded)
               - Showdown between multiple players
            6. Chip distribution and round cleanup

        Note:
            - Players can play as long as they have any chips (no minimum)
            - Eliminated players (0 chips) are tracked for final standings
            - All chip movements are logged with net changes
        """
        eliminated_players = []

        while len(self.players) > 1:
            # Track all players with chips
            all_players = self.players.copy()

            # Check which players can still play
            active_players = []
            for player in all_players:
                if player.chips > 0:  # Any player with chips can play
                    active_players.append(player)
                else:
                    if player not in eliminated_players:
                        eliminated_players.append(player)
                        logging.info(f"\n{player.name} is eliminated (out of chips)!")

            # If only one player has chips, they win
            if len(active_players) <= 1:
                break

            # Check if max rounds reached
            if self.max_rounds and self.round_count >= self.max_rounds:
                logging.info(f"\nGame ended after {self.max_rounds} rounds!")
                break

            # Start new round with all players who have chips
            self.players = active_players
            self.start_round()
            self.blinds_and_antes()

            # Pre-draw betting
            logging.info("\n--- Pre-Draw Betting ---")
            initial_chips = {p: p.chips for p in self.players}
            self.pot = betting_round(self.players, self.pot)

            # Check if only one player remains after pre-draw betting
            active_players = [p for p in self.players if not p.folded]
            if len(active_players) == 1:
                winner = active_players[0]
                winner.chips += self.pot
                logging.info(
                    f"\n{winner.name} wins ${self.pot} (all others folded pre-draw)"
                )
                # Log chip movements
                for player in self.players:
                    if player.chips != initial_chips[player]:
                        net_change = player.chips - initial_chips[player]
                        logging.info(
                            f"{player.name}: ${initial_chips[player]} → ${player.chips} ({net_change:+d})"
                        )
                self._log_chip_summary()
                self.round_count += 1
                self._reset_round()
                continue

            # Draw phase
            logging.info("\n--- Draw Phase ---")
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
                logging.info(
                    f"\n{winner.name} wins ${self.pot} (all others folded post-draw)"
                )
                # Log chip movements
                for player in self.players:
                    if player.chips != initial_chips[player]:
                        net_change = player.chips - initial_chips[player]
                        logging.info(
                            f"{player.name}: ${initial_chips[player]} → ${player.chips} ({net_change:+d})"
                        )
                self._log_chip_summary()

            self.round_count += 1
            self._reset_round()

        # Log final game results including eliminated players
        logging.info("\n=== Game Summary ===")
        logging.info(f"Total rounds played: {self.round_count}")
        if self.max_rounds and self.round_count >= self.max_rounds:
            logging.info("Game ended due to maximum rounds limit")

        # Include all players in final standings, sorted by chips
        all_players = sorted(
            self.players + eliminated_players, key=lambda p: p.chips, reverse=True
        )
        logging.info("\nFinal Standings:")
        for i, player in enumerate(all_players, 1):
            status = " (eliminated)" if player in eliminated_players else ""
            logging.info(f"{i}. {player.name}: ${player.chips}{status}")

    def start_round(self) -> None:
        """
        Start a new round of poker.
        """
        self.round_number += 1
        self.pot = 0

        logging.info(f"\n{'='*50}")
        logging.info(f"Round {self.round_number}")
        logging.info(f"{'='*50}")

        # Ensure dealer index is valid for current number of players
        self.dealer_index = self.dealer_index % len(self.players)

        # Store true starting stacks before any deductions
        self.round_starting_stacks = {player: player.chips for player in self.players}

        # Reset deck and deal new hands
        self.deck = Deck()
        self.deck.shuffle()
        for player in self.players:
            player.bet = 0
            player.folded = False
            player.hand = Hand()
            player.hand.add_cards(self.deck.deal(5))

        # Log true starting stacks before any deductions
        logging.info("\nStarting stacks (before antes/blinds):")
        for player in self.players:
            chips_str = f"${self.round_starting_stacks[player]}"
            if self.round_starting_stacks[player] < self.big_blind:
                chips_str += " (short stack)"
            logging.info(f"  {player.name}: {chips_str}")

        # Log dealer and blind positions
        dealer = self.players[self.dealer_index].name
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        logging.info(f"\nDealer: {self.players[self.dealer_index].name}")
        logging.info(f"Small Blind: {self.players[sb_index].name}")
        logging.info(f"Big Blind: {self.players[bb_index].name}")

        # Let AI players send pre-round messages
        for player in self.players:
            if hasattr(player, "get_message"):
                game_state = f"Round {self.round_number}, Your chips: ${player.chips}"
                message = player.get_message(game_state)
                if message:
                    message = message.encode("ascii", "replace").decode("ascii")
                    logging.info(f"\n{player.name} says: {message}")

        logging.info("\n")

    def draw_phase(self) -> None:
        """
        Handle the draw phase where players can discard and draw new cards.
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
                    # Log the intended discards before making changes
                    discard_indices = sorted(discards)
                    logging.info(f"Discarding cards at positions: {discard_indices}")

                    # Remove discarded cards
                    player.hand.cards = [
                        card
                        for i, card in enumerate(player.hand.cards)
                        if i not in discards
                    ]

                    # Draw exactly the same number of cards as were discarded
                    num_discards = len(discards)
                    new_cards = self.deck.deal(num_discards)
                    player.hand.add_cards(new_cards)

                    logging.info(
                        f"Drew {num_discards} new card{'s' if num_discards != 1 else ''}"
                    )
            else:
                # Non-AI players keep their hand
                logging.info("Keeping current hand")

    def _reset_round(self) -> None:
        """
        Reset game state for the next round.

        Resets the pot and player states between rounds to ensure
        clean state for the next round of play.

        Side Effects:
            - Sets pot to 0
            - Resets all player round-specific attributes (bets, folded status)
        """
        self.pot = 0
        for player in self.players:
            player.reset_for_new_round()
