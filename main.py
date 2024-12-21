import os
import random
import time

import openai
import pokerkit as pk
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")


class PokerAgent:
    """Advanced poker agent with perception, reasoning, communication, and action capabilities."""

    def __init__(self, name, model_type="gpt", strategy_style=None):
        self.name = name
        self.model_type = model_type
        self.last_message = ""
        self.perception_history = []  # Track game states and opponent actions
        self.strategy_style = strategy_style or random.choice(
            [
                "Aggressive Bluffer",
                "Calculated and Cautious",
                "Chaotic and Unpredictable",
            ]
        )

    def perceive(self, game_state, opponent_message):
        """Process and store current game state and opponent's message."""
        perception = {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": time.time(),
        }
        self.perception_history.append(perception)
        return perception

    def get_message(self, game_state):
        """Generate strategic communication based on game state and strategy style."""
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

    def interpret_message(self, opponent_message):
        """Enhanced message interpretation with historical context."""
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

    def get_action(self, game_state, opponent_message=None):
        """Strategic action decision incorporating game history and style."""
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

    def _query_llm(self, prompt):
        """Enhanced LLM query with error handling and retries."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.model_type == "gpt":
                    response = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=prompt,
                        max_tokens=20,
                        temperature=0.7,
                    )
                    return response["choices"][0]["text"]
                elif self.model_type == "local_llm":
                    response = requests.post(
                        os.getenv("LOCAL_LLM_ENDPOINT"),
                        json={"prompt": prompt, "max_tokens": 20},
                        timeout=5,
                    )
                    return response.json()["choices"][0]["text"]
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    print(f"All attempts failed for {self.name}. Defaulting to 'fold'")
                    return "fold"
                time.sleep(1)  # Wait before retry


# Set up the Poker Game
def play_poker_round():
    # Create the table with 2 enhanced agents
    table = pk.Table(
        name="Test Table",
        seats=[
            pk.Seat(name="GPT_Agent"),
            pk.Seat(name="LocalLLM_Agent"),
        ],
    )

    # Initialize enhanced agents
    agents = {
        "GPT_Agent": PokerAgent(
            name="GPT_Agent", model_type="gpt", strategy_style="Aggressive Bluffer"
        ),
        "LocalLLM_Agent": PokerAgent(
            name="LocalLLM_Agent",
            model_type="local_llm",
            strategy_style="Calculated and Cautious",
        ),
    }

    # Play a single hand
    table.sitdown()
    table.deal()
    print("Starting Poker Round with Bluffing!")

    # Iterate over betting rounds
    opponent_messages = {name: "" for name in agents.keys()}
    while not table.finished:
        for player in table.current_players:
            if player.active:
                agent = agents[player.name]

                # Agent sends a message before acting
                message = agent.get_message(str(table))
                print(f"{player.name} says: '{message}'")
                opponent_messages[player.name] = message

                # Interpret opponent's last message
                opponent_name = next(
                    (p.name for p in table.current_players if p.name != player.name),
                    None,
                )
                opponent_message = opponent_messages.get(opponent_name, "")
                interpretation = agent.interpret_message(opponent_message)
                print(
                    f"{player.name} interprets '{opponent_name}' as: {interpretation}"
                )

                # Decide action considering the opponent's message
                action = agent.get_action(str(table), opponent_message)
                print(f"{player.name} chooses: {action}")

                if action == "fold":
                    table.fold(player)
                elif action == "call":
                    table.call(player)
                elif action == "raise":
                    table.raise_bet(player, amount=10)

        table.next_round()

    # End of hand
    print("Poker round complete!")
    print(table.results())


if __name__ == "__main__":
    play_poker_round()
