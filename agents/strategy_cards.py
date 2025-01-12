from typing import Dict, Optional

#! what is this doing? Is it being used or needed?

# Core strategy meta-prompts that define base personalities
CORE_STRATEGIES = {
    "Aggressive Bluffer": """You are an aggressive poker player who:
- Raises frequently to put pressure on opponents
- Uses position and timing for maximum effect
- Bluffs often but with strategic timing
- Seeks to dominate the table psychologically
- Takes calculated risks to build big pots
- Watches for signs of weakness to exploit""",
    "Calculated and Cautious": """You are a mathematical poker player who:
- Makes decisions based primarily on pot odds and equity
- Plays a tight-aggressive style
- Bluffs rarely and only with strong drawing hands
- Takes detailed notes on opponent patterns
- Preserves chips for optimal spots
- Focuses on long-term expected value""",
    "Chaotic and Unpredictable": """You are an unpredictable poker player who:
- Varies play style dramatically hand to hand
- Makes unconventional plays to confuse opponents
- Talks frequently to create table atmosphere
- Takes unusual lines with marginal hands
- Switches between passive and aggressive
- Uses psychology over pure math""",
}

# Situational strategy modifiers that can be combined with core strategies
SITUATION_MODIFIERS = {
    "short_stack": """Current situation - Short stack adjustments:
- Look for spots to double up
- Avoid marginal spots
- Focus on fold equity
- Consider push/fold strategy
- Value showdown potential highly""",
    "big_stack": """Current situation - Big stack adjustments:
- Apply maximum pressure
- Target medium stacks
- Protect against short stacks
- Control pot sizes
- Use chips as weapon""",
    "bubble": """Current situation - Bubble play adjustments:
- Exploit tight players
- Pressure medium stacks
- Avoid confrontation with big stacks
- Value survival premium
- Look for ICM pressure spots""",
}

# Advanced cognitive modules that can be activated
COGNITIVE_MODULES = {
    "reasoning": """Reasoning process:
1. Analyze current hand strength
2. Calculate pot odds and implied odds
3. Consider position and stack sizes
4. Evaluate opponent tendencies
5. Project future streets
6. Make final decision with clear logic chain""",
    "reflection": """Reflection process:
1. Review recent decisions and outcomes
2. Identify patterns in opponent reactions
3. Assess effectiveness of current strategy
4. Consider alternative approaches
5. Adjust plan if necessary""",
    "planning": """Planning process:
1. Set clear objective for current orbit
2. Identify key opponents to target/avoid
3. Plan bet sizing for future streets
4. Prepare adjustment triggers
5. Consider backup plans""",
}


class StrategyManager:
    """Manages strategy selection and combination for poker agents.

    This class handles the dynamic composition of AI poker player strategies by combining
    core personality traits with situational modifiers and cognitive modules.

    Attributes:
        base_strategy (str): The core personality strategy of the agent
        active_modifiers (Dict[str, str]): Currently active situational modifiers
        active_modules (Dict[str, bool]): Status of cognitive enhancement modules
    """

    def __init__(self, base_strategy: str):
        """Initialize a new strategy manager.

        Args:
            base_strategy (str): The base personality strategy to use. Must be one of
                the keys in CORE_STRATEGIES.

        Raises:
            KeyError: If base_strategy is not found in CORE_STRATEGIES
        """
        self.base_strategy = base_strategy
        self.active_modifiers: Dict[str, str] = {}
        self.active_modules: Dict[str, bool] = {
            "reasoning": False,
            "reflection": False,
            "planning": False,
        }

    def get_complete_prompt(self, game_state: Optional[Dict] = None) -> str:
        """Combines active strategies and modules into a complete prompt.

        Generates a comprehensive strategy prompt by combining the base personality
        with relevant situational modifiers and active cognitive modules based on
        the current game state.

        Args:
            game_state (Optional[Dict]): Current game state containing information like:
                - chips: Current chip stack
                - is_bubble: Whether we're in bubble situation
                - Other relevant game state information

        Returns:
            str: Combined prompt string for the AI agent
        """
        prompt_parts = [CORE_STRATEGIES[self.base_strategy]]

        # Add situation-specific modifiers based on game state
        if game_state:
            if game_state.get("chips", 1000) < 300:
                prompt_parts.append(SITUATION_MODIFIERS["short_stack"])
            elif game_state.get("chips", 1000) > 2000:
                prompt_parts.append(SITUATION_MODIFIERS["big_stack"])
            if game_state.get("is_bubble", False):
                prompt_parts.append(SITUATION_MODIFIERS["bubble"])

        # Add active cognitive modules
        for module, active in self.active_modules.items():
            if active:
                prompt_parts.append(COGNITIVE_MODULES[module])

        return "\n\n".join(prompt_parts)

    def update_strategy(self, game_state: Dict) -> None:
        """Updates strategy based on game state and performance.

        Dynamically adjusts the active modifiers and cognitive modules based on
        the current game state and historical performance.

        Args:
            game_state (Dict): Current game state and performance metrics
        """
        # Add logic to dynamically adjust strategy based on results
        pass
