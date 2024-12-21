import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pokerkit import Automation, NoLimitTexasHoldem

# Load environment variables
load_dotenv()

# Initialize OpenAI API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Modified logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "poker_game.log", mode="w"
        ),  # 'w' mode overwrites the file each run
        logging.StreamHandler(),  # This maintains console output
    ],
)
logger = logging.getLogger(__name__)


class PokerAgent:
    """Advanced poker agent with perception, reasoning, communication, and action capabilities.

    A sophisticated AI poker player that combines game state perception, strategic communication,
    and decision-making abilities to play Texas Hold'em poker.

    Attributes:
        name (str): Unique identifier for the agent
        model_type (str): Type of language model to use ('gpt' or 'local_llm')
        last_message (str): Most recent message sent by the agent
        perception_history (list): Historical record of game states and opponent actions
        strategy_style (str): Agent's playing style (e.g., 'Aggressive Bluffer', 'Calculated and Cautious')
    """

    def __init__(
        self, name: str, model_type: str = "gpt", strategy_style: Optional[str] = None
    ) -> None:
        self.name: str = name
        self.model_type: str = model_type
        self.last_message: str = ""
        self.perception_history: List[Dict[str, Any]] = []
        self.strategy_style: str = strategy_style or random.choice(
            [
                "Aggressive Bluffer",
                "Calculated and Cautious",
                "Chaotic and Unpredictable",
            ]
        )

    def perceive(
        self, game_state: Dict[str, Any], opponent_message: str
    ) -> Dict[str, Any]:
        """Process and store current game state and opponent's message.

        Args:
            game_state (dict): Current state of the poker game
            opponent_message (str): Message received from the opponent

        Returns:
            dict: Perception data including game state, opponent message, and timestamp
        """
        perception = {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": time.time(),
        }
        self.perception_history.append(perception)
        return perception

    def get_message(self, game_state: Dict[str, Any]) -> str:
        """Generate strategic communication based on game state and strategy style.

        Uses LLM to create contextually appropriate messages that align with the agent's
        strategy style and current game situation.

        Args:
            game_state (dict): Current state of the poker game

        Returns:
            str: Strategic message to influence opponent
        """
        prompt = f"""
        You are a {self.strategy_style} poker player in Texas Hold'em.
        
        Current situation:
        Game State: {game_state}
        Your recent observations: {self.perception_history[-3:] if len(self.perception_history) > 0 else "None"}
        
        Generate a strategic message to influence your opponent. Your personality is {self.strategy_style}.
        
        Your message should:
        1. Match your strategy style
        2. Be under 10 words
        3. Try to influence your opponent's next decision
        4. Consider your previous interactions
        
        What message will you send?
        """
        self.last_message = self._query_llm(prompt).strip()
        return self.last_message

    def interpret_message(self, opponent_message: str) -> str:
        """Enhanced message interpretation with historical context.

        Analyzes opponent messages considering recent game history and agent's strategy style.

        Args:
            opponent_message (str): Message received from the opponent

        Returns:
            str: Interpretation result ('trust', 'ignore', or 'counter-bluff')
        """
        recent_history = self.perception_history[-3:] if self.perception_history else []

        prompt = f"""
        You are a {self.strategy_style} poker player.
        Opponent's message: '{opponent_message}'
        Recent game history: {recent_history}
        
        Based on your strategy style and the game history:
        1. Analyze if they are bluffing, truthful, or misleading
        2. Consider their previous behavior patterns
        3. Think about how this fits your strategy style
        
        Respond with only: 'trust', 'ignore', or 'counter-bluff'
        """
        return self._query_llm(prompt).strip().lower()

    def get_action(
        self, game_state: Dict[str, Any], opponent_message: Optional[str] = None
    ) -> str:
        """Strategic action decision incorporating game history and style.

        Determines optimal poker action based on current game state, opponent behavior,
        and agent's strategy style.

        Args:
            game_state (dict): Current state of the poker game
            opponent_message (str, optional): Message received from opponent. Defaults to None.

        Returns:
            str: Chosen action ('fold', 'call', or 'raise')
        """
        recent_history = self.perception_history[-3:] if self.perception_history else []

        prompt = f"""
        You are a {self.strategy_style} poker player in a crucial moment.
        
        Current situation:
        Game State: {game_state}
        Opponent's Message: '{opponent_message or "nothing"}'
        Recent History: {recent_history}
        
        Consider:
        1. Your strategy style: {self.strategy_style}
        2. The opponent's recent behavior
        3. Your position and chip stack
        4. The credibility of their message
        
        Choose your action. Respond with only: 'fold', 'call', or 'raise'
        """
        return self._query_llm(prompt).strip().lower()

    def _query_llm(self, prompt: str) -> str:
        """Enhanced LLM query with error handling, retries, and logging.

        Makes API calls to either GPT or local LLM with built-in retry mechanism
        and comprehensive error handling.

        Args:
            prompt (str): Input prompt for the language model

        Returns:
            str: Model's response text

        Raises:
            Exception: If all retry attempts fail, returns 'fold' as fallback
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info("\n[LLM Query] Attempt %d for %s", attempt + 1, self.name)
                logger.debug("[LLM Query] Prompt: %s", prompt)

                if self.model_type == "gpt":
                    logger.info("[LLM Query] Using GPT model...")
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": f"You are a {self.strategy_style} poker player.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=20,
                        temperature=0.7,
                    )
                    result = response.choices[0].message.content
                    logger.info("[LLM Query] Response: %s", result)
                    return result

                elif self.model_type == "local_llm":
                    logger.info("[LLM Query] Using Local LLM...")
                    endpoint = os.getenv("LOCAL_LLM_ENDPOINT")
                    logger.debug("[LLM Query] Endpoint: %s", endpoint)

                    response = requests.post(
                        endpoint,
                        json={"prompt": prompt, "max_tokens": 20},
                        timeout=5,
                    )
                    result = response.json()["choices"][0]["text"]
                    logger.info("[LLM Query] Response: %s", result)
                    return result

            except Exception as e:
                logger.error("[LLM Query] Error on attempt %d: %s", attempt + 1, str(e))
                logger.debug("[LLM Query] Error type: %s", type(e).__name__)
                if hasattr(e, "response"):
                    logger.error(
                        "[LLM Query] Response status: %d", e.response.status_code
                    )
                    logger.error("[LLM Query] Response body: %s", e.response.text)

                if attempt == max_retries - 1:
                    logger.warning(
                        "[LLM Query] All attempts failed for %s. Defaulting to 'fold'",
                        self.name,
                    )
                    return "fold"
                time.sleep(1)  # Wait before retry


# Set up the Poker Game
def play_poker_round() -> None:
    # Create the table with proper automations and settings
    table = NoLimitTexasHoldem.create_state(
        automations=(
            Automation.ANTE_POSTING,
            Automation.BET_COLLECTION,
            Automation.BLIND_OR_STRADDLE_POSTING,
            Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
            Automation.HAND_KILLING,
            Automation.CHIPS_PUSHING,
            Automation.CHIPS_PULLING,
        ),
        ante_trimming_status=True,  # Whether antes should be uniform
        raw_antes=0,  # Ante amount
        raw_blinds_or_straddles=(50, 100),  # Small blind, big blind
        min_bet=100,  # Minimum betting amount
        raw_starting_stacks=[1000, 1000],  # Starting chips for each player
        player_count=2,  # Number of players
    )

    # Initialize enhanced agents
    agents = {
        "GPT_Agent_1": PokerAgent(
            name="GPT_Agent_1", model_type="gpt", strategy_style="Aggressive Bluffer"
        ),
        "GPT_Agent_2": PokerAgent(
            name="GPT_Agent_2",
            model_type="gpt",
            strategy_style="Calculated and Cautious",
        ),
    }

    logger.info("\n=== Starting Poker Game ===\n")

    # Initialize opponent messages dictionary
    opponent_messages = {name: "" for name in agents.keys()}

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
            logger.info("Board: %s", " ".join(str(card) for card in table.board_cards))

        # Debug print for each iteration
        logger.info("Current stacks: %s", table.stacks)

        # Handle betting round
        current_street = table.street_count
        betting_complete = False
        while (
            current_street == table.street_count and not betting_complete
        ):  # Continue while we're still in the same street
            # Get the current actor from the table's actor_indices
            if not table.actor_indices:
                betting_complete = True
                continue

            current_player = table.actor_indices[0]  # Get the next player to act
            agent = list(agents.values())[current_player]

            logger.info("\n--- %s's Turn (Player %d) ---", agent.name, current_player)
            logger.info("Current street: %s", table.street)
            logger.info("Current pot: %d", sum(table.pots))
            logger.info("Current bets: %s", table.bets)

            # Agent sends a message before acting
            message = agent.get_message(str(table))
            logger.info("%s says: '%s'", agent.name, message)
            opponent_messages[agent.name] = message

            # Interpret opponent's last message
            opponent_name = next(name for name in agents.keys() if name != agent.name)
            opponent_message = opponent_messages.get(opponent_name, "")
            if opponent_message:
                interpretation = agent.interpret_message(opponent_message)
                logger.info(
                    "%s interprets %s's message '%s' as: %s",
                    agent.name,
                    opponent_name,
                    opponent_message,
                    interpretation,
                )

            # Decide action considering the opponent's message
            action = agent.get_action(str(table), opponent_message)
            logger.info("%s chooses: %s", agent.name, action)

            # Modified action handling
            if action == "fold":
                table.fold()
                logger.info("%s folds!", agent.name)
                return  # End the game if someone folds
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
                # First check if we can actually raise
                if not table.can_complete_bet_or_raise_to():
                    logger.info("%s cannot raise, calling instead", agent.name)
                    table.check_or_call()
                else:
                    # Calculate valid raise amount
                    min_raise = table.street.min_completion_betting_or_raising_amount
                    current_bet = max(table.bets)
                    raise_to = (
                        current_bet + min_raise
                    )  # This ensures we're raising by at least the minimum amount

                    logger.info(
                        "Raising to %d (min raise was %d, current bet was %d)",
                        raise_to,
                        min_raise,
                        current_bet,
                    )
                    table.complete_bet_or_raise_to(raise_to)
                    logger.info("%s raises to %d", agent.name, raise_to)

            # Check if betting is complete (no more actors)
            if not table.actor_indices:
                betting_complete = True

        # Move to next street if betting round is complete
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

    # End of hand
    logger.info("\n=== Hand Complete! ===")
    logger.info("Final board: %s", " ".join(str(card) for card in table.board_cards))
    logger.info("Final hands:")
    logger.info("GPT_Agent_1 (Player 1): AhKh")
    logger.info("GPT_Agent_2 (Player 2): 2c3c")
    logger.info("Final pots: %s", list(table.pots))
    logger.info("Final stacks: %s", table.stacks)

    # Determine winner (based on who has more chips than initial stack)
    initial_stack = 1000
    for player_idx, final_stack in enumerate(table.stacks):
        agent_name = list(agents.keys())[player_idx]
        if final_stack > initial_stack:
            logger.info(
                "\nWinner: %s (+%d chips)", agent_name, final_stack - initial_stack
            )
        elif final_stack < initial_stack:
            logger.info(
                "\nLoser: %s (-%d chips)", agent_name, initial_stack - final_stack
            )


if __name__ == "__main__":
    play_poker_round()
