import logging
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Tuple, TypedDict, Union

from .betting import betting_round
from .deck import Deck
from .hand import Hand
from .player import Player
from .pot_manager import PotManager
from .types import SidePot


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
        max_raise_multiplier: Maximum raise as multiplier of current bet (e.g., 3 means max raise is 3x current bet)
        max_raises_per_round: Maximum number of raises allowed per betting round
    """

    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    ante: int = 0
    max_rounds: Optional[int] = None
    session_id: Optional[str] = None
    max_raise_multiplier: int = 3
    max_raises_per_round: int = 4

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.starting_chips <= 0:
            raise ValueError("Starting chips must be positive")
        if self.small_blind <= 0 or self.big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if self.ante < 0:
            raise ValueError("Ante cannot be negative")
        if self.max_raise_multiplier <= 0:
            raise ValueError("Max raise multiplier must be positive")
        if self.max_raises_per_round <= 0:
            raise ValueError("Max raises per round must be positive")


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
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

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

        self.pot = 0  # Initialize pot
        self.pot_manager = PotManager()

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
        """
        Collect mandatory bets (blinds and antes) at the start of each hand.

        This method:
        1. Stores initial chip counts for tracking changes
        2. Collects antes from all players who can afford them
        3. Collects small blind from player after dealer
        4. Collects big blind from player after small blind
        5. Handles partial blind postings for short-stacked players

        Side Effects:
            - Updates player chip counts
            - Updates game pot
            - Stores round starting stacks

        Notes:
            - Players can post partial blinds/antes if they don't have enough chips
            - Posting order is: antes first, then small blind, then big blind
        """
        # Store starting stacks
        self.round_starting_stacks = {p: p.chips for p in self.players}

        # Collect antes
        for player in self.players:
            ante_amount = min(self.ante, player.chips)
            if ante_amount > 0:
                actual_ante = player.place_bet(ante_amount)
                self.pot += actual_ante

        # Collect blinds
        sb_pos = (self.dealer_index + 1) % len(self.players)
        bb_pos = (self.dealer_index + 2) % len(self.players)

        # Small blind
        sb_amount = min(self.small_blind, self.players[sb_pos].chips)
        actual_sb = self.players[sb_pos].place_bet(sb_amount)
        self.pot += actual_sb

        # Big blind
        bb_amount = min(self.big_blind, self.players[bb_pos].chips)
        actual_bb = self.players[bb_pos].place_bet(bb_amount)
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

    def handle_side_pots(self) -> List[SidePot]:
        """Calculate side pots when players are all-in."""
        # Example usage:
        posted_amounts = {p: p.bet for p in self.players if p.bet > 0}
        side_pots = self.pot_manager.calculate_side_pots(posted_amounts)
        self.pot_manager.log_side_pots(logging)
        return side_pots

    def showdown(self) -> None:
        """Handle the showdown phase where winners are determined and pots are distributed."""
        active_players = [p for p in self.players if not p.folded]

        if len(active_players) == 1:
            # Single player remaining gets the pot
            winner = active_players[0]
            winner.chips += self.pot
            logging.info(f"{winner.name} wins ${self.pot}")
        else:
            # Multiple players - evaluate hands
            winners = self._evaluate_hands(active_players, self.pot)
            if winners:
                split_amount = self.pot // len(winners)
                for winner in winners:
                    winner.chips += split_amount
                    logging.info(f"{winner.name} wins ${split_amount}")

        # Handle any side pots
        if self.side_pots:
            for side_pot in self.side_pots:
                eligible_players = side_pot.eligible_players
                pot_winners = self._evaluate_hands(eligible_players, side_pot.amount)
                if pot_winners:
                    split_amount = side_pot.amount // len(pot_winners)
                    for winner in pot_winners:
                        winner.chips += split_amount
                        logging.info(
                            f"{winner.name} wins ${split_amount} from side pot"
                        )

        # Reset pot after distribution
        self.pot = 0
        self.side_pots = None

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
            winner.chips += self.pot_manager.pot
            logging.info(
                f"\n{winner.name} wins ${self.pot_manager.pot} (all others folded {phase})"
            )
            self._log_chip_movements(initial_chips)
            self._log_chip_summary()
            return True
        return False

    def _create_game_state(self) -> dict:
        """Create a dictionary containing the current game state."""
        return {
            "pot": self.pot_manager.pot,
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "bet": p.bet,
                    "folded": p.folded,
                    "position": i,
                }
                for i, p in enumerate(self.players)
            ],
            "current_bet": max(p.bet for p in self.players) if self.players else 0,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_index": self.dealer_index,
        }

    def _handle_pre_draw_betting(self, initial_chips: Dict[Player, int]) -> None:
        """
        Handle the betting round that occurs before the draw phase.

        Args:
            initial_chips: Dictionary mapping players to their chip counts at start of round

        This method:
        1. Creates current game state including pot, player info, and betting limits
        2. Executes betting round with all active players
        3. Updates main pot with results of betting

        Side Effects:
            - Updates player chip counts and bets
            - Updates game pot
        """
        # Initialize game state
        game_state = {
            "pot": self.pot,
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "bet": p.bet,
                    "folded": p.folded,
                    "position": i,
                }
                for i, p in enumerate(self.players)
            ],
            "current_bet": 0,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_index": self.dealer_index,
        }

        # Run betting round and update pot
        new_pot = betting_round(self.players, self.pot, game_state)
        self.pot = new_pot

    def _handle_post_draw_betting(self, initial_chips: Dict[Player, int]) -> None:
        """Handle the post-draw betting round and winner determination."""
        logging.info("\n--- Post-Draw Betting ---")

        # Create game state with correct pot amount
        game_state = {
            "pot": self.pot,  # Use current pot amount
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "bet": p.bet,
                    "folded": p.folded,
                    "position": i,
                }
                for i, p in enumerate(self.players)
            ],
            "current_bet": 0,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_index": self.dealer_index,
        }

        # Call betting round with current pot amount
        result = betting_round(self.players, self.pot, game_state)

        # Handle return value
        if isinstance(result, tuple):
            new_pot, side_pots = result
            self.side_pots = side_pots
        else:
            new_pot = result

        self.pot = new_pot  # Update pot directly

        # Call showdown to determine winner(s)
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
        """Initialize the state for a new round."""
        # Rotate dealer button first
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

        # Reset round state
        self.pot_manager.reset_pot()
        self.round_starting_stacks = {p: p.chips for p in self.players}

        # Reset player states
        for player in self.players:
            player.bet = 0
            player.folded = False

        # Deal cards
        self._deal_cards()

    def start_round(self) -> None:
        """Start a new round of poker."""
        self._initialize_round()

        # Log round info
        self._log_round_info()

        # Collect blinds and antes after initialization
        self.blinds_and_antes()

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
        """Reset the state after a round is complete."""
        # Clear hands and bets
        for player in self.players:
            player.bet = 0
            player.folded = False
            if hasattr(player, "hand"):
                player.hand = None

        # Reset pot in pot_manager as well
        self.pot_manager.reset_pot()

    def _log_side_pots(self) -> None:
        """
        Log the current side pot structure.

        Side Effects:
            - Logs each pot's amount and eligible players
        """
        if not self.side_pots:
            return

        logging.info("\nSide pots:")
        side_pots_view = self.pot_manager.get_side_pots_view()
        for i, pot in enumerate(side_pots_view, 1):
            players_str = ", ".join(pot["eligible_players"])
            logging.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")

    def start_game(self) -> None:
        """Execute the main game loop until a winner is determined or max rounds reached."""
        eliminated_players = []
        self.round_number = 0  # Initialize round counter

        while len(self.players) > 1:
            self.round_number += 1  # Increment round number at start of each iteration
            self._handle_eliminated_players(eliminated_players)

            # Check end conditions
            if len([p for p in self.players if p.chips > 0]) <= 1:
                break
            if self.max_rounds and self.round_count >= self.max_rounds:
                logging.info(f"\nGame ended after {self.max_rounds} rounds!")
                break

            # Start new round
            self.players = [p for p in self.players if p.chips > 0]

            # Store initial chips before starting round
            initial_chips = {p: p.chips for p in self.players}

            self.start_round()  # This will handle all round logging

            # Handle betting rounds with initial chips
            should_continue = self._handle_pre_draw_betting(initial_chips)
            if not should_continue:
                self.round_count += 1
                self._reset_round()
                continue

            self.draw_phase()
            self._handle_post_draw_betting(initial_chips)

            self.round_count += 1
            self._reset_round()

        self._log_game_summary(eliminated_players)

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

    def play_round(self) -> None:
        """Play a single round of poker."""
        self.round_number += 1  # Increment round number at start of each round

        logging.info(f"\n{'='*50}")
        logging.info(f"Round {self.round_number}")
        logging.info(f"{'='*50}\n")

        # Log starting stacks
        logging.info("Starting stacks (before antes/blinds):")
        for player in self.players:
            logging.info(f"  {player.name}: ${player.chips}")

        # ... rest of play_round implementation ...

    def _get_player_action(self, player: Player, current_bet: int) -> Tuple[str, int]:
        """
        Get and validate a player's action.

        Args:
            player: The player whose action to get
            current_bet: Current bet amount to call

        Returns:
            Tuple[str, int]: Action type and amount tuple (e.g., ("raise", 200))
        """
        # Create game state for AI decision
        game_state = {
            "pot": self.pot_manager.pot,
            "current_bet": current_bet,
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "bet": p.bet,
                    "folded": p.folded,
                    "position": i,
                }
                for i, p in enumerate(self.players)
            ],
        }

        # Get player's action
        if hasattr(player, "decide_action"):
            action = player.decide_action(game_state)

            # Parse action string
            if isinstance(action, tuple):
                action_type, amount = action
            elif action.startswith("raise"):
                try:
                    action_type = "raise"
                    amount = int(action.split()[1])
                except (IndexError, ValueError):
                    action_type = "call"
                    amount = current_bet
            else:
                action_type = action
                amount = current_bet if action == "call" else 0

            # Validate raise amount
            if action_type == "raise":
                min_raise = current_bet * 2
                max_raise = current_bet * self.config.max_raise_multiplier
                if amount < min_raise:
                    amount = min_raise
                elif amount > max_raise:
                    amount = max_raise

            return action_type, amount
        else:
            # Default to call for non-AI players
            return "call", current_bet

    def _handle_side_pots(
        self, all_in_players: List[Player], active_players: List[Player]
    ) -> None:
        """
        Calculate and distribute side pots when players are all-in.

        Args:
            all_in_players: List of players who have gone all-in
            active_players: List of players still in the hand

        This method:
        1. Uses pot manager to calculate side pots based on all-in amounts
        2. For each side pot:
            - Determines eligible winners from that pot's players
            - Splits pot amount evenly among winners
            - Updates winner chip counts

        Side Effects:
            - Updates player chip counts
            - Modifies side pot structures
        """
        side_pots = self.pot_manager.calculate_side_pots(active_players, all_in_players)

        for side_pot in side_pots:
            winners = self._evaluate_hands(side_pot.eligible_players, side_pot)
            split_amount = side_pot.amount // len(winners)
            for winner in winners:
                winner.chips += split_amount

    def _evaluate_hands(self, players: List[Player], pot_amount: int) -> List[Player]:
        """
        Evaluate player hands to determine winner(s).

        Args:
            players: List of players to evaluate
            pot_amount: Amount in the current pot being contested

        Returns:
            List[Player]: List of winning players (multiple in case of tie)
        """
        active_players = [p for p in players if not p.folded]
        if not active_players:
            return []

        # Find best hand(s)
        best_players = [active_players[0]]
        best_hand = active_players[0].hand

        for player in active_players[1:]:
            # Try compare_to first, fall back to direct comparison
            try:
                comparison = player.hand.compare_to(best_hand)
            except AttributeError:
                # For test mocks, use direct comparison
                if player.hand > best_hand:
                    comparison = 1
                elif player.hand == best_hand:
                    comparison = 0
                else:
                    comparison = -1

            if comparison > 0:  # Current player has better hand
                best_players = [player]
                best_hand = player.hand
            elif comparison == 0:  # Tie
                best_players.append(player)

        return best_players

    def _handle_betting_round(
        self, initial_chips: Dict[Player, int], current_pot: int
    ) -> Tuple[int, Optional[List[SidePot]]]:
        """
        Handle a single betting round.

        Args:
            initial_chips: Starting chip counts for each player
            current_pot: Current pot amount before betting

        Returns:
            Tuple[int, Optional[List[SidePot]]]: New pot amount and any side pots
        """
        game_state = {
            "pot": current_pot,
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "bet": p.bet,
                    "folded": p.folded,
                    "position": i,
                }
                for i, p in enumerate(self.players)
            ],
            "current_bet": 0,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_index": self.dealer_index,
        }

        result = betting_round(self.players, current_pot, game_state)

        # Handle both tuple and single value returns
        if isinstance(result, tuple):
            new_pot, side_pots = result
        else:
            new_pot = result
            side_pots = None

        self.pot = new_pot
        self.side_pots = side_pots

        return new_pot, side_pots
