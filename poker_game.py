import logging
from typing import Dict, List, Tuple

from pokerkit import Automation, NoLimitTexasHoldem
from pydantic import BaseModel, Field

from poker_agents import PokerAgent

logger = logging.getLogger(__name__)


class PlayerConfig(BaseModel):
    """Configuration for a poker player/agent."""

    name: str
    model_type: str = Field(default="gpt")
    strategy_style: str
    starting_stack: int = Field(default=1000)


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


class PokerGame:
    """Manages a poker game between AI agents.

    Handles game setup, state management, and round progression for a Texas Hold'em poker game
    between two AI agents.
    """

    def __init__(self) -> None:
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

        logger.info("\n=== Starting Poker Game ===\n")

        # Deal hole cards - using actual card representations
        table.deal_hole("AhKh")  # First player gets Ace-King of hearts
        table.deal_hole("2c3c")  # Second player gets 2-3 of clubs

        # Log initial hands
        logger.info("Initial hands:")
        logger.info("GPT_Agent_1 (Player 1): AhKh")
        logger.info("GPT_Agent_2 (Player 2): 2c3c")
        logger.info("Starting stacks: %s", table.stacks)
        logger.info("Blinds: Small Blind = 50, Big Blind = 100")

        # Debug print
        logger.debug("Game status: %s", table.status)
        logger.debug("Player count: %d", table.player_count)
        logger.debug("Current street: %s", table.street)
        logger.debug("Can check/call? %s", table.can_check_or_call())
        logger.debug("Can complete/bet/raise? %s", table.can_complete_bet_or_raise_to())

        # Main game loop - continue until the hand is complete
        while table.status:
            logger.info("\n=== Street: %s ===", table.street)

            if table.board_cards:
                logger.info(
                    "Board: %s", " ".join(str(card) for card in table.board_cards)
                )

            # Debug print for each iteration
            logger.info("Current stacks: %s", table.stacks)

            # Handle betting round
            current_street = table.street_count
            betting_complete = False
            while current_street == table.street_count and not betting_complete:
                self._handle_betting_round(table)
                if not table.actor_indices:
                    betting_complete = True

            # Move to next street if betting round is complete
            self._advance_to_next_street(table)

        self._end_game(table)

    def _handle_betting_round(self, table: NoLimitTexasHoldem) -> None:
        """Handle a single betting round."""
        if not table.actor_indices:
            return

        current_player = table.actor_indices[0]  # Get the next player to act
        agent = list(self.agents.values())[current_player]

        logger.info("\n--- %s's Turn (Player %d) ---", agent.name, current_player)
        logger.info("Current street: %s", table.street)
        logger.info("Current pot: %d", sum(table.pots))
        logger.info("Current bets: %s", table.bets)

        # Agent sends a message before acting
        message = agent.get_message(str(table))
        logger.info("%s says: '%s'", agent.name, message)
        self.opponent_messages[agent.name] = message

        # Interpret opponent's last message
        opponent_name = next(name for name in self.agents.keys() if name != agent.name)
        opponent_message = self.opponent_messages.get(opponent_name, "")
        if opponent_message:
            interpretation = agent.interpret_message(opponent_message)
            logger.info(
                "%s interprets %s's message '%s' as: %s",
                agent.name,
                opponent_name,
                opponent_message,
                interpretation,
            )

        # Decide and execute action
        self._execute_action(table, agent, opponent_message)

    def _execute_action(
        self, table: NoLimitTexasHoldem, agent: PokerAgent, opponent_message: str
    ) -> None:
        """Execute an agent's chosen action."""
        action = agent.get_action(str(table), opponent_message)
        logger.info("%s chooses: %s", agent.name, action)

        if action == "fold":
            table.fold()
            logger.info("%s folds!", agent.name)
        elif action == "call":
            table.check_or_call()
            logger.info(
                "%s %s",
                agent.name,
                (
                    "checks"
                    if table.street.min_completion_betting_or_raising_amount == 0
                    else "calls"
                ),
            )
        elif action == "raise":
            if not table.can_complete_bet_or_raise_to():
                logger.info("%s cannot raise, calling instead", agent.name)
                table.check_or_call()
            else:
                min_raise = table.street.min_completion_betting_or_raising_amount
                current_bet = max(table.bets)
                raise_to = current_bet + min_raise

                logger.info(
                    "Raising to %d (min raise was %d, current bet was %d)",
                    raise_to,
                    min_raise,
                    current_bet,
                )
                table.complete_bet_or_raise_to(raise_to)
                logger.info("%s raises to %d", agent.name, raise_to)

    def _advance_to_next_street(self, table: NoLimitTexasHoldem) -> None:
        """Advance the game to the next street."""
        if not table.status:
            return

        if table.street_count == 0:  # Pre-flop
            table.burn_card("2d")
            table.deal_board("7h8h9h")
            logger.info("\n=== FLOP ===")
            logger.info("Board: 7h 8h 9h")
        elif table.street_count == 1:  # Flop
            table.burn_card("2d")
            table.deal_board("Th")
            logger.info("\n=== TURN ===")
            logger.info("Board: 7h 8h 9h Th")
        elif table.street_count == 2:  # Turn
            table.burn_card("2d")
            table.deal_board("Jh")
            logger.info("\n=== RIVER ===")
            logger.info("Board: 7h 8h 9h Th Jh")

        if table.status:
            table.next_street()

    def _end_game(self, table: NoLimitTexasHoldem) -> None:
        """Handle end of game logging and winner determination."""
        logger.info("\n=== Hand Complete! ===")
        logger.info(
            "Final board: %s", " ".join(str(card) for card in table.board_cards)
        )
        logger.info("Final hands:")
        logger.info("GPT_Agent_1 (Player 1): AhKh")
        logger.info("GPT_Agent_2 (Player 2): 2c3c")
        logger.info("Final pots: %s", list(table.pots))
        logger.info("Final stacks: %s", table.stacks)

        # Use configured starting stack instead of hardcoded value
        initial_stack = next(iter(self.player_configs.values())).starting_stack
        for player_idx, final_stack in enumerate(table.stacks):
            agent_name = list(self.agents.keys())[player_idx]
            if final_stack > initial_stack:
                logger.info(
                    "\nWinner: %s (+%d chips)", agent_name, final_stack - initial_stack
                )
            elif final_stack < initial_stack:
                logger.info(
                    "\nLoser: %s (-%d chips)", agent_name, initial_stack - final_stack
                )
