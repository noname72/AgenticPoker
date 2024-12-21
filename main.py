import os
import random
import time

import openai
import requests
from dotenv import load_dotenv
from pokerkit import Automation, NoLimitTexasHoldem

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
        raw_antes=0,                # Ante amount
        raw_blinds_or_straddles=(50, 100),  # Small blind, big blind
        min_bet=100,               # Minimum betting amount
        raw_starting_stacks=[1000, 1000],  # Starting chips for each player
        player_count=2             # Number of players
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

    print("\n=== Starting Poker Round with Bluffing! ===\n")

    # Deal hole cards - using actual card representations
    table.deal_hole("AhKh")  # First player gets Ace-King of hearts
    table.deal_hole("2c3c")  # Second player gets 2-3 of clubs
    
    # Log initial hands
    print("Initial hands:")
    print(f"GPT_Agent (Player 1): AhKh")
    print(f"LocalLLM_Agent (Player 2): 2c3c")
    print(f"\nStarting stacks: {table.stacks}")
    print(f"Blinds: Small Blind = 50, Big Blind = 100\n")

    # Iterate over betting rounds
    opponent_messages = {name: "" for name in agents.keys()}
    current_street = "preflop"
    while not table.status:
        if table.board_cards != []:
            print(f"\nBoard: {' '.join(str(card) for card in table.board_cards)}")
        
        for player_idx, player in enumerate(range(table.num_players)):
            if table.can_act(player):
                agent = list(agents.values())[player_idx]
                
                print(f"\n--- {agent.name}'s Turn ---")
                print(f"Current street: {current_street}")
                print(f"Current pot: {sum(table.pots)}")
                print(f"Required bet to call: {table.min_bet}")
                print(f"Player stacks: {table.stacks}")

                # Agent sends a message before acting
                message = agent.get_message(str(table))
                print(f"\n{agent.name} says: '{message}'")
                opponent_messages[agent.name] = message

                # Interpret opponent's last message
                opponent_name = next(name for name in agents.keys() if name != agent.name)
                opponent_message = opponent_messages.get(opponent_name, "")
                if opponent_message:
                    interpretation = agent.interpret_message(opponent_message)
                    print(f"{agent.name} interprets {opponent_name}'s message '{opponent_message}' as: {interpretation}")

                # Decide action considering the opponent's message
                action = agent.get_action(str(table), opponent_message)
                print(f"{agent.name} chooses: {action}")

                # Convert action to pokerkit format
                if action == "fold":
                    table.act_fold()
                    print(f"{agent.name} folds!")
                elif action == "call":
                    table.act_call()
                    print(f"{agent.name} calls {table.min_bet}")
                elif action == "raise":
                    raise_amount = min(20, table.max_raise_size())
                    table.act_raise(raise_amount)
                    print(f"{agent.name} raises to {raise_amount}")

        if table.street_over():
            if not table.status:
                # Deal next street with actual cards
                table.burn_card("2d")
                if len(table.board_cards) == 0:
                    current_street = "flop"
                    table.deal_board("7h8h9h")
                    print("\n=== FLOP ===")
                    print("Board: 7h 8h 9h")
                elif len(table.board_cards) == 3:
                    current_street = "turn"
                    table.deal_board("Th")
                    print("\n=== TURN ===")
                    print("Board: 7h 8h 9h Th")
                elif len(table.board_cards) == 4:
                    current_street = "river"
                    table.deal_board("Jh")
                    print("\n=== RIVER ===")
                    print("Board: 7h 8h 9h Th Jh")
                table.next_street()

    # End of hand
    print("\n=== Hand Complete! ===")
    print(f"Final board: {' '.join(str(card) for card in table.board_cards)}")
    print("\nFinal hands:")
    print(f"GPT_Agent (Player 1): AhKh")
    print(f"LocalLLM_Agent (Player 2): 2c3c")
    print(f"\nFinal pots: {table.pots}")
    print(f"Final stacks: {table.stacks}")
    
    # Determine winner (based on who has more chips than initial stack)
    initial_stack = 1000
    for player_idx, final_stack in enumerate(table.stacks):
        agent_name = list(agents.keys())[player_idx]
        if final_stack > initial_stack:
            print(f"\nWinner: {agent_name} (+{final_stack - initial_stack} chips)")
        elif final_stack < initial_stack:
            print(f"\nLoser: {agent_name} (-{initial_stack - final_stack} chips)")


if __name__ == "__main__":
    play_poker_round()
