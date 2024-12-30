import logging
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Tuple, TypedDict, Union

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player
from .types import SidePot, SidePotView


@dataclass
class GameConfig:
    """
    Configuration parameters for a poker game.

    Attributes:
        starting_chips: Initial chip amount for each player
        small_blind: Small blind bet amount
        big_blind: Big blind bet amount
        ante: Mandatory bet required from all players
        max_rounds: Maximum number of rounds to play (None for unlimited)
        session_id: Unique identifier for the game session
    """

    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    ante: int = 0
    max_rounds: Optional[int] = None
    session_id: Optional[str] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.starting_chips <= 0:
            raise ValueError("Starting chips must be positive")
        if self.small_blind <= 0 or self.big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if self.ante < 0:
            raise ValueError("Ante cannot be negative")


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
        side_pots (Optional[List[SidePot]]): List of side pots in the game.
        round_starting_stacks (Dict[Player, int]): Dictionary of starting chip counts for each round.
        config (GameConfig): Configuration parameters for the game.
    """

    # Class attributes defined before __init__
    deck: Deck
    players: List[Player]
    pot: int
    small_blind: int
    big_blind: int
    dealer_index: int
    round_count: int
    round_number: int
    max_rounds: Optional[int]
    ante: int
    side_pots: Optional[List[SidePot]]
    session_id: Optional[str]
    round_starting_stacks: Dict[Player, int]
    config: GameConfig

    def __init__(
        self,
        players: Union[List[str], List[Player]],
        small_blind: int = 10,
        big_blind: int = 20,
        ante: int = 0,
        session_id: Optional[str] = None,
        config: Optional[GameConfig] = None,
    ) -> None:
        """Initialize a new poker game with specified players and configuration."""
        if not players:
            raise ValueError("Must provide at least 2 players")

        # Support both direct parameter initialization and GameConfig
        if config:
            self.config = config
        else:
            self.config = GameConfig(
                small_blind=small_blind,
                big_blind=big_blind,
                ante=ante,
                session_id=session_id,
            )

        self.session_id = self.config.session_id
        self.deck = Deck()

        # Convert names to players if needed
        if players and isinstance(players[0], str):
            self.players = [
                Player(name, self.config.starting_chips) for name in players
            ]
        else:
            self.players = players  # Use provided Player objects
            # Validate player chips
            if any(p.chips < 0 for p in self.players):
                raise ValueError("Players cannot have negative chips")

        self.pot = 0
        self.small_blind = self.config.small_blind
        self.big_blind = self.config.big_blind
        self.dealer_index = 0
        self.round_count = 0
        self.round_number = 0
        self.max_rounds = self.config.max_rounds
        self.ante = self.config.ante
        self.side_pots = None

        # Log game configuration
        logging.info(f"\n{'='*50}")
        logging.info(f"Game Configuration")
        logging.info(f"{'='*50}")
        logging.info(f"Players: {', '.join([p.name for p in self.players])}")
        logging.info(f"Starting chips: ${self.config.starting_chips}")
        logging.info(f"Blinds: ${self.config.small_blind}/${self.config.big_blind}")
        logging.info(f"Ante: ${self.config.ante}")
        if self.config.max_rounds:
            logging.info(f"Max rounds: {self.config.max_rounds}")
        if self.config.session_id:
            logging.info(f"Session ID: {self.config.session_id}")
        logging.info(f"{'='*50}\n")

    def blinds_and_antes(self) -> None:
        """Collect mandatory bets (blinds and antes) at the start of each hand."""
        # Track actual amounts posted
        posted_amounts = {player: 0 for player in self.players}

        # Collect antes first
        if self.ante > 0:
            for player in self.players:
                actual_ante = player.place_bet(self.ante)
                posted_amounts[player] += actual_ante
                self.pot += actual_ante

        # Collect blinds
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        # Small blind
        sb_player = self.players[sb_index]
        actual_sb = sb_player.place_bet(self.small_blind)
        posted_amounts[sb_player] += actual_sb
        self.pot += actual_sb

        # Big blind
        bb_player = self.players[bb_index]
        actual_bb = bb_player.place_bet(self.big_blind)
        posted_amounts[bb_player] += actual_bb
        self.pot += actual_bb

    def _log_blind_post(self, blind_type: str, player: "Player", amount: int) -> None:
        """Helper to log blind postings consistently."""
        status = " (all in)" if player.chips == 0 else ""
        if amount < (self.small_blind if blind_type == "small" else self.big_blind):
            logging.info(
                f"{player.name} posts partial {blind_type} blind of ${amount}{status}"
            )
        else:
            logging.info(f"{player.name} posts {blind_type} blind of ${amount}{status}")

    def _calculate_side_pots(
        self, posted_amounts: Dict["Player", int]
    ) -> List[SidePot]:
        """
        Calculate side pots based on posted amounts.

        Args:
            posted_amounts: Dictionary mapping players to their total posted amounts

        Returns:
            List of SidePot objects containing pot amounts and eligible players
        """
        side_pots = []
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])

        current_amount = 0
        for player, amount in sorted_players:
            if amount > current_amount:
                eligible = [p for p, a in posted_amounts.items() if a >= amount]
                pot_size = (amount - current_amount) * len(eligible)
                if pot_size > 0:
                    side_pots.append(SidePot(pot_size, eligible))
                current_amount = amount

        return side_pots

    def _get_side_pots_view(self, side_pots: List[SidePot]) -> List[SidePotView]:
        """
        Convert side pots to a view-friendly format for logging/display.

        Args:
            side_pots: List of SidePot objects

        Returns:
            List of SidePotView dictionaries with player names instead of objects
        """
        return [
            {
                "amount": pot.amount,
                "eligible_players": [p.name for p in pot.eligible_players],
            }
            for pot in side_pots
        ]

    def _log_pot_summary(self, posted_amounts: Dict["Player", int]) -> None:
        """Log clear summary of pot state including any side pots."""
        ante_total = sum(min(self.ante, p.chips) for p in self.players if p.chips > 0)

        logging.info(f"\nStarting pot: ${self.pot}")
        if ante_total > 0:
            logging.info(f"  Includes ${ante_total} in antes")

        if self.side_pots:
            logging.info("\nSide pots:")
            side_pots_view = self._get_side_pots_view(self.side_pots)
            for i, pot in enumerate(side_pots_view, 1):
                players_str = ", ".join(pot["eligible_players"])
                logging.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")

    def handle_side_pots(self) -> List[SidePot]:
        """
        Calculate and manage side pots for all-in situations.

        Handles cases where players are all-in with different amounts,
        ensuring fair pot distribution.

        Returns:
            List[SidePot]: Side pots with their amounts and eligible players
        """
        # Get only players who contributed to the pot
        active_players = [p for p in self.players if p.bet > 0]
        if not active_players:
            return [SidePot(self.pot, self.players)]

        # Calculate posted amounts for each player
        posted_amounts = {player: player.bet for player in active_players}
        side_pots = self._calculate_side_pots(posted_amounts)

        # Handle any remaining chips from antes or odd amounts
        total_allocated = sum(pot.amount for pot in side_pots)
        remainder = self.pot - total_allocated
        if remainder > 0 and side_pots:
            # Add remainder to first pot
            first_pot = side_pots[0]
            side_pots[0] = SidePot(
                first_pot.amount + remainder, first_pot.eligible_players
            )

        return side_pots

    def showdown(self) -> None:
        """Determine winner(s) and distribute pot(s) at the end of betting."""
        logging.info(f"\n{'='*20} SHOWDOWN {'='*20}")

        active_players = [p for p in self.players if not p.folded]

        # Single player remaining (everyone else folded)
        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.pot
            logging.info(f"\n{winner.name} wins ${self.pot} uncontested!")
            self._log_chip_summary()
            return

        # Find best hand among active players
        best_hand = max(active_players, key=lambda p: p.hand)
        winners = [p for p in active_players if p.hand == best_hand.hand]

        # Split pot among winners
        pot_share = self.pot // len(winners)
        remainder = self.pot % len(winners)

        # Distribute pot
        for i, winner in enumerate(winners):
            share = pot_share + (1 if i < remainder else 0)
            winner.chips += share
            logging.info(f"{winner.name} wins ${share} with {winner.hand.evaluate()}")

        # Reset pot after distribution
        self.pot = 0
        self.side_pots = None

        # Log final chip movement summary
        self._log_chip_summary()

    def _log_chip_summary(self) -> None:
        """
        Log a summary of all players' chip counts, sorted by amount.

        Side Effects:
            - Writes chip counts to game log
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

        Returns:
            bool: True if game can continue, False if game should end
                  (one or zero players remain)

        Side Effects:
            - Updates players list
            - Logs elimination messages
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

    def _handle_eliminated_players(self, eliminated_players: List[Player]) -> None:
        """Check for and handle any newly eliminated players."""
        for player in self.players:
            if player.chips <= 0 and player not in eliminated_players:
                eliminated_players.append(player)
                logging.info(f"\n{player.name} is eliminated (out of chips)!")

    def _handle_single_remaining_player(
        self, initial_chips: Dict[Player, int], phase: str
    ) -> bool:
        """
        Award pot to last remaining player after others fold.

        Args:
            initial_chips: Starting chip counts for tracking changes
            phase: Game phase when win occurred ('pre-draw' or 'post-draw')

        Returns:
            bool: True if single winner found, False if multiple players remain

        Side Effects:
            - Updates winner's chip count
            - Logs win and chip movements
        """
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.pot
            logging.info(
                f"\n{winner.name} wins ${self.pot} (all others folded {phase})"
            )
            self._log_chip_movements(initial_chips)
            self._log_chip_summary()
            return True
        return False

    def _handle_pre_draw_betting(self) -> Tuple[bool, Dict[Player, int]]:
        """Handle the pre-draw betting round."""
        logging.info("\n--- Pre-Draw Betting ---")
        initial_chips = {p: p.chips for p in self.players}

        # Get active players
        active_players = [p for p in self.players if not p.folded]

        # Call betting round and update pot
        result = betting_round(active_players, self.pot)
        if isinstance(result, tuple):
            new_pot, new_side_pots = result
            self.pot = new_pot
            self.side_pots = new_side_pots
        else:
            self.pot = result

        if self._handle_single_remaining_player(initial_chips, "pre-draw"):
            return False, initial_chips

        return True, initial_chips

    def _handle_post_draw_betting(self, initial_chips: Dict[Player, int]) -> None:
        """Handle the post-draw betting round and winner determination."""
        logging.info("\n--- Post-Draw Betting ---")
        pot_result, new_side_pots = betting_round(self.players, self.pot)
        self.pot = pot_result
        if new_side_pots:
            self.side_pots = new_side_pots

        if not self._handle_single_remaining_player(initial_chips, "post-draw"):
            self.showdown()

    def _log_chip_movements(self, initial_chips: Dict[Player, int]) -> None:
        """Log the chip movements for each player from their initial amounts."""
        for player in self.players:
            if player.chips != initial_chips[player]:
                net_change = player.chips - initial_chips[player]
                logging.info(
                    f"{player.name}: ${initial_chips[player]} → ${player.chips} ({net_change:+d})"
                )

    def _log_game_summary(self, eliminated_players: List[Player]) -> None:
        """Log the final game summary and standings."""
        logging.info("\n=== Game Summary ===")
        logging.info(f"Total rounds played: {self.round_count}")
        if self.max_rounds and self.round_count >= self.max_rounds:
            logging.info("Game ended due to maximum rounds limit")

        # Use a set to ensure unique players
        all_players = list({player for player in (self.players + eliminated_players)})
        # Sort by chips (eliminated players will have 0)
        all_players.sort(key=lambda p: p.chips, reverse=True)

        logging.info("\nFinal Standings:")
        for i, player in enumerate(all_players, 1):
            status = " (eliminated)" if player in eliminated_players else ""
            logging.info(f"{i}. {player.name}: ${player.chips}{status}")

    def _initialize_round(self) -> None:
        """Initialize the basic round state."""
        self.round_number += 1
        self.pot = 0
        self.dealer_index = self.dealer_index % len(self.players)
        self.round_starting_stacks = {player: player.chips for player in self.players}

    def _deal_cards(self) -> None:
        """Reset the deck and deal new hands to all players."""
        self.deck = Deck()
        self.deck.shuffle()
        for player in self.players:
            player.bet = 0
            player.folded = False
            player.hand = Hand()
            player.hand.add_cards(self.deck.deal(5))

    def _log_round_info(self) -> None:
        """
        Log the current round state including stacks and positions.

        Side Effects:
            - Logs round number
            - Logs each player's stack and short stack status
            - Logs dealer and blind positions
        """
        logging.info(f"\n{'='*50}")
        logging.info(f"Round {self.round_number}")
        logging.info(f"{'='*50}")

        logging.info("\nStarting stacks (before antes/blinds):")
        for player in self.players:
            chips_str = f"${self.round_starting_stacks[player]}"
            if self.round_starting_stacks[player] < self.big_blind:
                chips_str += " (short stack)"
            logging.info(f"  {player.name}: {chips_str}")

        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        logging.info(f"\nDealer: {self.players[self.dealer_index].name}")
        logging.info(f"Small Blind: {self.players[sb_index].name}")
        logging.info(f"Big Blind: {self.players[bb_index].name}")
        logging.info("\n")

    def start_game(self) -> None:
        """Execute the main game loop until a winner is determined or max rounds reached."""
        eliminated_players = []

        while len(self.players) > 1:
            self._handle_eliminated_players(eliminated_players)

            # Check end conditions
            if len([p for p in self.players if p.chips > 0]) <= 1:
                break
            if self.max_rounds and self.round_count >= self.max_rounds:
                logging.info(f"\nGame ended after {self.max_rounds} rounds!")
                break

            # Start new round
            self.players = [p for p in self.players if p.chips > 0]
            self.start_round()
            self.blinds_and_antes()

            # Handle betting rounds
            should_continue, initial_chips = self._handle_pre_draw_betting()
            if not should_continue:
                self.round_count += 1
                self._reset_round()
                continue

            self.draw_phase()
            self._handle_post_draw_betting(initial_chips)

            self.round_count += 1
            self._reset_round()

        self._log_game_summary(eliminated_players)

    def start_round(self) -> None:
        """Start a new round of poker by initializing game state and dealing cards."""
        self._initialize_round()
        self._log_round_info()
        self._deal_cards()

        # Handle AI player pre-round messages
        for player in self.players:
            if hasattr(player, "get_message"):
                game_state = f"Round {self.round_number}, Your chips: ${player.chips}"
                message = player.get_message(game_state)

    def draw_phase(self) -> None:
        """
        Handle the draw phase where players can discard and draw new cards.

        Each non-folded player gets one opportunity to discard 0-5 cards and draw
        replacements. AI players use decide_draw() to choose discards, while non-AI
        players keep their current hand.

        Side Effects:
            - Modifies player hands
            - Updates deck composition
            - Logs all actions

        Notes:
            - Discarded cards are tracked to prevent redealing
            - Deck is reshuffled with discards if it runs low
        """
        logging.info("\n--- Draw Phase ---")
        discarded_cards = []

        active_players = [p for p in self.players if not p.folded]
        for player in active_players:
            logging.info(f"\n{player.name}'s turn to draw")
            logging.info(f"Current hand: {player.hand.show()}")

            if not hasattr(player, "decide_draw"):
                logging.info("Keeping current hand")
                continue

            # Handle AI player discards
            discards = player.decide_draw()
            if not discards:
                continue

            # Process discards
            discard_indices = sorted(discards)
            logging.info(f"Discarding cards at positions: {discard_indices}")

            # Track and remove discarded cards
            discarded = [player.hand.cards[i] for i in discard_indices]
            discarded_cards.extend(discarded)
            player.hand.cards = [
                card for i, card in enumerate(player.hand.cards) if i not in discards
            ]

            # Reshuffle if needed
            if len(self.deck.cards) < len(discards):
                logging.info("Reshuffling discarded cards into deck")
                self.deck.cards.extend(discarded_cards)
                self.deck.shuffle()
                discarded_cards = []

            # Draw and add new cards
            new_cards = self.deck.deal(len(discards))
            player.hand.add_cards(new_cards)
            logging.info(
                f"Drew {len(discards)} new card{'s' if len(discards) != 1 else ''}: "
                f"{', '.join(str(card) for card in new_cards)}"
            )

    def _reset_round(self) -> None:
        """
        Reset game state between rounds.

        Side Effects:
            - Resets pot to 0
            - Resets player bets and folded status
        """
        self.pot = 0
        for player in self.players:
            player.reset_for_new_round()

    def _log_side_pots(self) -> None:
        """
        Log the current side pot structure.

        Side Effects:
            - Logs each pot's amount and eligible players
        """
        if not self.side_pots:
            return

        logging.info("\nSide pots:")
        side_pots_view = self._get_side_pots_view(self.side_pots)
        for i, pot in enumerate(side_pots_view, 1):
            players_str = ", ".join(pot["eligible_players"])
            logging.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")
