import logging
from typing import Dict, List, Optional, Tuple

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player


class AgenticPoker:
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
        session_id (Optional[str]): Unique identifier for this game session.
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
        Initialize a new poker game with specified parameters.

        Args:
            players (Union[List[str], List[Player]]): List of player names or Player objects
            starting_chips (int): Initial chip amount for each player. Defaults to 1000.
            small_blind (int): Small blind bet amount. Defaults to 10.
            big_blind (int): Big blind bet amount. Defaults to 20.
            max_rounds (Optional[int]): Maximum number of rounds to play. Defaults to None.
            ante (int): Mandatory bet required from all players. Defaults to 0.
            session_id (Optional[str]): Unique identifier for this game session.

        Raises:
            ValueError: If any of these conditions are met:
                - Empty players list
                - starting_chips <= 0
                - small_blind <= 0
                - big_blind <= 0
                - ante < 0

        Side Effects:
            - Creates Player objects if names provided
            - Initializes game state attributes
            - Sets up logging with session context
            - Logs initial game configuration

        Example:
            >>> game = AgenticPoker(['Alice', 'Bob'], starting_chips=500)
            >>> game = AgenticPoker(player_list, small_blind=5, big_blind=10, ante=1)

            Game Configuration
            =================================================
            Players: Alice, Bob
            Starting chips: $500
            Blinds: $5/$10
            Ante: $1
            =================================================
        """
        if not players:
            raise ValueError("Must provide at least 2 players")
        if starting_chips <= 0:
            raise ValueError("Starting chips must be positive")
        if small_blind <= 0 or big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if ante < 0:
            raise ValueError("Ante cannot be negative")

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
        self.side_pots = None

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

        Collects forced bets in this order:
        1. Antes from all players (if any)
        2. Small blind from player left of dealer
        3. Big blind from player left of small blind

        The method handles:
        - Partial postings when players can't cover full amounts
        - All-in situations and side pot creation
        - Accurate tracking of posted amounts per player
        - Special cases like short stacks and missing blinds

        Side Effects:
            - Reduces player chip counts
            - Updates pot total
            - Creates side pots if needed
            - Updates player bet amounts
            - Logs all chip movements

        Attributes Modified:
            - self.pot: Updated with total collected bets
            - self.side_pots: Created if players are all-in with different amounts
            - player.chips: Reduced by posted amounts
            - player.bet: Updated with posted amounts

        Example:
            >>> game.blinds_and_antes()

            Collecting antes...
            Alice posts ante of $1
            Bob posts ante of $1
            Charlie posts ante of $1 (all in)

            Bob posts small blind of $10
            Charlie posts partial big blind of $5 (all in)

            Starting pot: $18
              Includes $3 in antes

            Side pots:
              Pot 1: $15 (Eligible: Alice, Bob)
              Pot 2: $3 (Eligible: Alice, Bob, Charlie)
        """
        # Track actual amounts posted for accurate pot calculation
        posted_amounts = {player: 0 for player in self.players}

        # Collect antes first
        if self.ante > 0:
            logging.info("\nCollecting antes...")
            for player in self.players:
                if player.chips > 0:
                    actual_ante = min(self.ante, player.chips)
                    actual_ante = player.place_bet(actual_ante)
                    posted_amounts[player] += actual_ante
                    status = " (all in)" if player.chips == 0 else ""
                    logging.info(f"{player.name} posts ante of ${actual_ante}{status}")

        # Collect blinds with accurate tracking
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        # Small blind
        sb_player = self.players[sb_index]
        if sb_player.chips > 0:
            actual_sb = min(self.small_blind, sb_player.chips)
            actual_sb = sb_player.place_bet(actual_sb)
            posted_amounts[sb_player] += actual_sb
            self._log_blind_post("small", sb_player, actual_sb)

        # Big blind
        bb_player = self.players[bb_index]
        if bb_player.chips > 0:
            actual_bb = min(self.big_blind, bb_player.chips)
            actual_bb = bb_player.place_bet(actual_bb)
            posted_amounts[bb_player] += actual_bb
            self._log_blind_post("big", bb_player, actual_bb)

        # Calculate total pot and create initial side pots if needed
        total_posted = sum(posted_amounts.values())
        self.pot = total_posted

        # Initialize side pots if any players are all-in
        all_in_players = [p for p in self.players if p.chips == 0]
        if all_in_players:
            self.side_pots = self._calculate_side_pots(posted_amounts)
            self._log_side_pots()
        else:
            self.side_pots = None

        # Log final pot state clearly
        self._log_pot_summary(posted_amounts)

    def _log_blind_post(self, blind_type: str, player: "Player", amount: int) -> None:
        """Helper to log blind postings consistently."""
        status = " (all in)" if player.chips == 0 else ""
        if amount < (self.small_blind if blind_type == "small" else self.big_blind):
            logging.info(
                f"{player.name} posts partial {blind_type} blind of ${amount}{status}"
            )
        else:
            logging.info(f"{player.name} posts {blind_type} blind of ${amount}{status}")

    def _calculate_side_pots(self, posted_amounts: Dict["Player", int]) -> List[Dict]:
        """
        Calculate side pots based on posted amounts.
        Returns list of dicts with amount and eligible players.
        """
        side_pots = []
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])

        current_amount = 0
        for player, amount in sorted_players:
            if amount > current_amount:
                eligible = [p for p, a in posted_amounts.items() if a >= amount]
                pot_size = (amount - current_amount) * len(eligible)
                if pot_size > 0:
                    side_pots.append(
                        {
                            "amount": pot_size,
                            "eligible_players": [p.name for p in eligible],
                        }
                    )
                current_amount = amount

        return side_pots

    def _log_pot_summary(self, posted_amounts: Dict["Player", int]) -> None:
        """Log clear summary of pot state including any side pots."""
        ante_total = sum(min(self.ante, p.chips) for p in self.players if p.chips > 0)

        logging.info(f"\nStarting pot: ${self.pot}")
        if ante_total > 0:
            logging.info(f"  Includes ${ante_total} in antes")

        if self.side_pots:
            logging.info("\nSide pots:")
            for i, pot in enumerate(self.side_pots, 1):
                players_str = ", ".join(pot["eligible_players"])
                logging.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")

    def handle_side_pots(self) -> List[Tuple[int, List[Player]]]:
        """
        Calculate and split the pot when players are all-in with different amounts.
        """
        # Get only players who contributed to the pot
        active_players = [p for p in self.players if p.bet > 0]
        if not active_players:
            return [(self.pot, self.players)]

        active_players.sort(key=lambda p: p.bet)
        pots = []
        pot_amount = int(self.pot)  # Ensure we're working with an integer
        previous_bet = 0

        while active_players:
            current_bet = active_players[0].bet
            bet_difference = current_bet - previous_bet
            pot_contribution = bet_difference * len(active_players)

            if pot_contribution > 0:
                # Create tuple of (pot_amount, eligible_players)
                pots.append((pot_contribution, active_players[:]))
                pot_amount = max(
                    0, pot_amount - pot_contribution
                )  # Ensure we don't go negative

            previous_bet = current_bet
            active_players = active_players[1:]

        # If there's any remaining pot amount (from antes or odd chips), add it to the first pot
        if pot_amount > 0 and pots:
            first_pot_amount, first_pot_players = pots[0]
            pots[0] = (first_pot_amount + pot_amount, first_pot_players)

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

        # Use existing side pots if available, otherwise calculate them
        if self.side_pots:
            # Convert side_pots format to list of tuples
            side_pots = [
                (
                    pot["amount"],
                    [p for p in self.players if p.name in pot["eligible_players"]],
                )
                for pot in self.side_pots
            ]
        else:
            side_pots = self.handle_side_pots()

        logging.info(f"\nDetected {len(side_pots)} pot(s) due to all-in players.")

        for pot_index, (pot_amount, eligible_players) in enumerate(side_pots, start=1):
            if not eligible_players:
                continue

            # Log which players can win this pot
            logging.info(
                f"\nSide Pot #{pot_index}: ${pot_amount} among {[p.name for p in eligible_players]}"
            )

            # Find best hand among eligible players
            best_hand_value = max(eligible_players, key=lambda p: p.hand).hand
            winners = [p for p in eligible_players if p.hand == best_hand_value]

            # Distribute pot to winner(s)
            pot_share = pot_amount // len(winners)
            remainder = pot_amount % len(winners)

            logging.info(f"  Distributing ${pot_amount} to {len(winners)} winner(s).")
            for i, winner in enumerate(winners):
                share = pot_share + (1 if i < remainder else 0)
                winner.chips += share
                logging.info(
                    f"  {winner.name} wins ${share} with {winner.hand.evaluate()}"
                )

        # Reset pot and side pots after distribution
        self.pot = 0
        self.side_pots = None

        # Log final chip movement summary
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

        Returns:
            bool: True if game should continue, False if game should end
                 (only one or zero players remain).

        Side Effects:
            - Updates self.players list
            - Logs game over messages if appropriate
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
            pot_result, new_side_pots = betting_round(self.players, self.pot)
            self.pot = pot_result
            if new_side_pots:
                self.side_pots = new_side_pots

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
            self.draw_phase()

            # Post-draw betting
            logging.info("\n--- Post-Draw Betting ---")
            pot_result, new_side_pots = betting_round(self.players, self.pot)
            self.pot = pot_result
            if new_side_pots:
                self.side_pots = new_side_pots

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
        Start a new round of poker by initializing game state and dealing cards.

        The method performs these steps in order:
        1. Increments round number
        2. Resets pot to zero
        3. Rotates dealer position
        4. Records starting chip counts
        5. Shuffles deck and deals hands
        6. Resets player states (bets, folded status)
        7. Logs round information

        Side Effects:
            - Updates game state:
                - round_number: Incremented
                - pot: Reset to 0
                - dealer_index: Rotated
                - round_starting_stacks: Set
            - Modifies player state:
                - hand: New 5-card hand
                - bet: Reset to 0
                - folded: Reset to False
            - Creates new shuffled deck
            - Logs round setup information

        Notes:
            - Each player receives exactly 5 cards
            - Players with chips < big blind are marked as "short stack"
            - AI players may send pre-round messages
            - Dealer button moves clockwise each round

        Example:
            >>> game.start_round()
            =================================================
            Round 42
            =================================================

            Starting stacks (before antes/blinds):
              Alice: $1200
              Bob: $800
              Charlie: $15 (short stack)

            Dealer: Alice
            Small Blind: Bob
            Big Blind: Charlie
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

        logging.info("\n")

    def draw_phase(self) -> None:
        """
        Handle the draw phase where players can discard and draw new cards.

        During this phase, each non-folded player gets one opportunity to:
        1. Discard any number of cards from their hand (0-5)
        2. Draw an equal number of new cards from the deck

        The method handles:
        - Tracking discarded cards to prevent redealing
        - Reshuffling discards if deck runs low
        - AI player decision-making for discards
        - Maintaining hand size of exactly 5 cards

        Side Effects:
            - Modifies player hands
            - Updates deck composition
            - Logs all discard and draw actions

        Notes:
            - Players who have folded are skipped
            - AI players use their decide_draw() method to choose discards
            - Non-AI players automatically keep their current hand
            - If deck runs low, discarded cards are reshuffled back in

        Example:
            >>> game.draw_phase()
            --- Draw Phase ---

            Alice's turn to draw
            Current hand: A♠ K♠ 3♣ 4♥ 7♦
            Discarding cards at positions: [2, 3, 4]
            Drew 3 new cards: Q♣, J♥, 10♦
        """
        logging.info("\n--- Draw Phase ---")

        # Track all discarded cards to ensure they don't get redealt
        discarded_cards = []

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

                    # Track discarded cards before removing them
                    discarded = [player.hand.cards[i] for i in discard_indices]
                    discarded_cards.extend(discarded)

                    # Remove discarded cards
                    player.hand.cards = [
                        card
                        for i, card in enumerate(player.hand.cards)
                        if i not in discards
                    ]

                    # Draw exactly the same number of cards as were discarded
                    num_discards = len(discards)

                    # Verify deck has enough cards
                    if len(self.deck.cards) < num_discards:
                        logging.info("Reshuffling discarded cards into deck")
                        self.deck.cards.extend(discarded_cards)
                        self.deck.shuffle()
                        discarded_cards = []

                    new_cards = self.deck.deal(num_discards)
                    player.hand.add_cards(new_cards)

                    # Log the new cards that were drawn
                    logging.info(
                        f"Drew {num_discards} new card{'s' if num_discards != 1 else ''}: "
                        f"{', '.join(str(card) for card in new_cards)}"
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

    def _log_side_pots(self) -> None:
        """
        Log the current side pot structure.

        Formats and logs each side pot's amount and eligible players
        for clear tracking of pot distribution.
        """
        if not self.side_pots:
            return

        logging.info("\nSide pots:")
        for i, pot in enumerate(self.side_pots, 1):
            players_str = ", ".join(pot["eligible_players"])
            logging.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")
