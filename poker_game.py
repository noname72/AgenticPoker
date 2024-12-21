import logging
from typing import Dict, List, Tuple
import pydantic

from pokerkit import Automation, NoLimitTexasHoldem
from pydantic import BaseModel, Field

from poker_agents import PokerAgent

logger = logging.getLogger(__name__)

# Check Pydantic version
PYDANTIC_V2 = pydantic.VERSION.startswith("2")


class PlayerConfig(BaseModel):
    """Configuration for a poker player/agent."""

    name: str
    model_type: str = Field(default="gpt")
    strategy_style: str
    starting_stack: int = Field(default=1000)

    def to_dict(self):
        """Convert config to dict, handling Pydantic version differences."""
        return self.model_dump() if PYDANTIC_V2 else self.dict()


class GameConfig(BaseModel):
    """Configuration for the poker game."""

    small_blind: int = Field(default=50)
    big_blind: int = Field(default=100)
    min_bet: int = Field(default=100)
    ante: int = Field(default=0)
    player_count: int = Field(default=2)
    automations: Tuple[str, ...] = Field(
        default=(
            "ANTE_POSTING",
            "BET_COLLECTION",
            "BLIND_OR_STRADDLE_POSTING",
            "HOLE_CARDS_SHOWING_OR_MUCKING",
            "HAND_KILLING",
            "CHIPS_PUSHING",
            "CHIPS_PULLING",
        )
    )

    def to_dict(self):
        """Convert config to dict, handling Pydantic version differences."""
        return self.model_dump() if PYDANTIC_V2 else self.dict()


class PokerGame:
    """Manages a poker game between AI agents.

    Handles game setup, state management, and round progression for a Texas Hold'em poker game
    between two AI agents.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # Initialize game configuration
        self.game_config = GameConfig()

        # Initialize player configurations
        self.player_configs = {
            "GPT_Agent_1": PlayerConfig(
                name="GPT_Agent_1",
                strategy_style="Aggressive Bluffer",
            ),
            "GPT_Agent_2": PlayerConfig(
                name="GPT_Agent_2",
                strategy_style="Calculated and Cautious",
            ),
        }

        # Initialize enhanced agents using configurations
        self.agents = {
            name: PokerAgent(
                name=config.name,
                model_type=config.model_type,
                strategy_style=config.strategy_style,
            )
            for name, config in self.player_configs.items()
        }

        # Initialize opponent messages dictionary
        self.opponent_messages = {name: "" for name in self.agents.keys()}

    def play_round(self) -> None:
        """Play a single round of poker between the agents."""
        try:
            # Create the table with proper automations and settings
            table = NoLimitTexasHoldem.create_state(
                automations=tuple(
                    getattr(Automation, auto) for auto in self.game_config.automations
                ),
                ante_trimming_status=True,
                raw_antes=self.game_config.ante,
                raw_blinds_or_straddles=(
                    self.game_config.small_blind,
                    self.game_config.big_blind,
                ),
                min_bet=self.game_config.min_bet,
                raw_starting_stacks=[
                    config.starting_stack for config in self.player_configs.values()
                ],
                player_count=self.game_config.player_count,
            )

            self.logger.info("=== Starting New Poker Game ===")
            self.logger.debug("Game Configuration: %s", self.game_config.to_dict())

            # Deal hole cards
            table.deal_hole("AhKh")
            table.deal_hole("2c3c")

            # Log initial game state
            self._log_game_state(table, "Initial")

            # Main game loop
            while table.status:
                self._handle_street(table)

            self._end_game(table)

        except Exception as e:
            self.logger.error("Fatal error during game: %s", str(e), exc_info=True)
            raise

    def _log_game_state(self, table: NoLimitTexasHoldem, prefix: str = "") -> None:
        """Log the current state of the game."""
        self.logger.info("%s Game State:", prefix)
        self.logger.info("+-- Hands:")
        self.logger.info("|   +-- GPT_Agent_1 (Player 1): AhKh")
        self.logger.info("|   +-- GPT_Agent_2 (Player 2): 2c3c")
        self.logger.info("+-- Stacks: %s", table.stacks)
        self.logger.info("+-- Street: %s", table.street)
        if table.board_cards:
            self.logger.info("+-- Board: %s", " ".join(str(card) for card in table.board_cards))
        self.logger.info("+-- Pot: %d", sum(table.pots))

        # Log detailed state information at debug level
        self.logger.debug("Detailed Game State:")
        self.logger.debug("+-- Status: %s", table.status)
        self.logger.debug("+-- Can Check/Call: %s", table.can_check_or_call())
        self.logger.debug("+-- Can Raise: %s", table.can_complete_bet_or_raise_to())

    def _handle_betting_round(self, table: NoLimitTexasHoldem) -> None:
        """Handle a single betting round."""
        if not table.actor_indices:
            return

        current_player = table.actor_indices[0]
        agent = list(self.agents.values())[current_player]

        self.logger.info("--- %s's Turn (Player %d) ---", agent.name, current_player)
        
        # Log current game situation
        self.logger.debug("Current Game Situation:")
        self.logger.debug("+-- Street: %s", table.street)
        self.logger.debug("+-- Pot: %d", sum(table.pots))
        self.logger.debug("+-- Current Bets: %s", table.bets)

        try:
            # Agent sends a message
            message = agent.get_message(str(table))
            self.logger.info("%s says: '%s'", agent.name, message)
            self.opponent_messages[agent.name] = message

            # Interpret opponent's message
            opponent_name = next(name for name in self.agents.keys() if name != agent.name)
            opponent_message = self.opponent_messages.get(opponent_name, "")
            if opponent_message:
                interpretation = agent.interpret_message(opponent_message)
                self.logger.debug(
                    "Message Interpretation: %s → %s: '%s'",
                    opponent_name,
                    agent.name,
                    interpretation,
                )

            # Execute action
            self._execute_action(table, agent, opponent_message)

        except Exception as e:
            self.logger.error(
                "Error during %s's turn: %s", agent.name, str(e), exc_info=True
            )
            raise

    def _execute_action(
        self, table: NoLimitTexasHoldem, agent: PokerAgent, opponent_message: str
    ) -> None:
        """Execute an agent's chosen action."""
        action = agent.get_action(str(table), opponent_message)
        
        if action == "fold":
            self.logger.warning("%s decides to fold!", agent.name)
            table.fold()
        elif action == "call":
            action_type = "checks" if table.street.min_completion_betting_or_raising_amount == 0 else "calls"
            self.logger.info("%s %s", agent.name, action_type)
            table.check_or_call()
        elif action == "raise":
            if not table.can_complete_bet_or_raise_to():
                self.logger.warning(
                    "%s attempted to raise but cannot - falling back to call",
                    agent.name
                )
                table.check_or_call()
            else:
                min_raise = table.street.min_completion_betting_or_raising_amount
                current_bet = max(table.bets)
                raise_to = current_bet + min_raise

                self.logger.info("%s raises to %d", agent.name, raise_to)
                self.logger.debug(
                    "Raise details: current_bet=%d, min_raise=%d, raise_to=%d",
                    current_bet,
                    min_raise,
                    raise_to
                )
                table.complete_bet_or_raise_to(raise_to)

    def _advance_to_next_street(self, table: NoLimitTexasHoldem) -> None:
        """Advance the game to the next street."""
        if not table.status:
            return

        if table.street_count == 0:  # Pre-flop
            table.burn_card("2d")
            table.deal_board("7h8h9h")
            self.logger.info("\n=== FLOP ===")
            self.logger.info("Board: 7h 8h 9h")
        elif table.street_count == 1:  # Flop
            table.burn_card("2d")
            table.deal_board("Th")
            self.logger.info("\n=== TURN ===")
            self.logger.info("Board: 7h 8h 9h Th")
        elif table.street_count == 2:  # Turn
            table.burn_card("2d")
            table.deal_board("Jh")
            self.logger.info("\n=== RIVER ===")
            self.logger.info("Board: 7h 8h 9h Th Jh")

        if table.status:
            table.next_street()

    def _end_game(self, table: NoLimitTexasHoldem) -> None:
        """Handle end of game logging and winner determination."""
        self.logger.info("\n=== Hand Complete! ===")
        self.logger.info(
            "Final board: %s", " ".join(str(card) for card in table.board_cards)
        )
        self.logger.info("Final hands:")
        self.logger.info("GPT_Agent_1 (Player 1): AhKh")
        self.logger.info("GPT_Agent_2 (Player 2): 2c3c")
        self.logger.info("Final pots: %s", list(table.pots))
        self.logger.info("Final stacks: %s", table.stacks)

        # Use configured starting stack instead of hardcoded value
        initial_stack = next(iter(self.player_configs.values())).starting_stack
        for player_idx, final_stack in enumerate(table.stacks):
            agent_name = list(self.agents.keys())[player_idx]
            if final_stack > initial_stack:
                self.logger.info(
                    "\nWinner: %s (+%d chips)", agent_name, final_stack - initial_stack
                )
            elif final_stack < initial_stack:
                self.logger.info(
                    "\nLoser: %s (-%d chips)", agent_name, initial_stack - final_stack
                )

    def _handle_street(self, table: NoLimitTexasHoldem) -> None:
        """Handle all betting rounds for the current street."""
        current_street = table.street_count
        betting_complete = False
        
        while current_street == table.street_count and not betting_complete:
            self._handle_betting_round(table)
            if not table.actor_indices:
                betting_complete = True
        
        # Move to next street if betting round is complete
        self._advance_to_next_street(table)
