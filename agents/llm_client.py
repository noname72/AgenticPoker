import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Union

from openai import OpenAI

from exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """Handles LLM queries with consistent error handling and retries.

    This class encapsulates all LLM interaction logic, providing a clean interface
    for different types of queries while handling retries, timeouts, and errors
    consistently.

    Attributes:
        client (OpenAI): OpenAI client instance
        max_retries (int): Maximum number of retry attempts
        retry_delay (float): Delay between retries in seconds
    """

    def __init__(self, client: OpenAI, max_retries: int = 3, retry_delay: float = 1.0):
        self.client = client
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def query(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_message: Optional[str] = None,
    ) -> str:
        """Base query method with retry logic.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            system_message: Optional system message for chat context

        Returns:
            str: LLM response text

        Raises:
            LLMError: If all retries fail
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content

            except Exception as e:
                logger.warning(f"LLM query attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise LLMError(
                        f"All {self.max_retries} LLM query attempts failed"
                    ) from e
                time.sleep(self.retry_delay)

    def generate_plan(self, strategy_style: str, game_state: str) -> Dict:
        """Generate a strategic plan using the LLM.

        Args:
            strategy_style: Player's strategic style
            game_state: Current game state

        Returns:
            Dict: Strategic plan containing approach, bet sizing, etc.
        """
        planning_prompt = f"""
        You are a {strategy_style} poker player planning your strategy.
        
        Current situation:
        {game_state}
        
        Create a strategic plan in valid JSON format:
        {{
            "approach": "aggressive|balanced|defensive",
            "reasoning": "<brief explanation>",
            "bet_sizing": "small|medium|large",
            "bluff_threshold": <0.0-1.0>,
            "fold_threshold": <0.0-1.0>
        }}
        """

        response = self.query(
            prompt=planning_prompt,
            temperature=0.7,
            system_message=f"You are a {strategy_style} poker strategist.",
        )

        return eval(response.strip())  # Safe since we control LLM output format

    def decide_action(
        self,
        strategy_style: str,
        game_state: str,
        plan: Dict,
        hand_eval: Optional[Tuple[str, int, List[int]]] = None,
    ) -> str:
        """Decide on a specific poker action using JSON-based response format.

        Args:
            strategy_style: Player's strategic style
            game_state: Current game state
            plan: Current strategic plan
            hand_eval: Current hand evaluation

        Returns:
            str: Poker action ('fold', 'call', or 'raise X')

        Raises:
            ValueError: If response cannot be parsed into valid action
        """
        execution_prompt = f"""
        You are a {strategy_style} poker player following this plan:
        Approach: {plan['approach']}
        Reasoning: {plan['reasoning']}
        
        Current hand evaluation:
        {hand_eval}
        
        Current situation:
        {game_state}
        
        Respond with a JSON object containing your action decision:
        {{
            "action": "fold" | "call" | "raise",
            "raise_amount": <optional number if action is raise>,
            "reasoning": "<brief explanation of decision>"
        }}
        """

        response = self.query(
            prompt=execution_prompt,
            temperature=0.5,  # Lower temperature for more consistent decisions
            system_message=f"You are a {strategy_style} poker player.",
        )

        try:
            # First try JSON parsing
            action_data = self._parse_json_action(response)
            if action_data:
                return self._format_action(action_data)

            # Fallback to regex parsing if JSON fails
            action = self._parse_regex_action(response)
            if action:
                return action

            # If both parsing methods fail, raise error
            raise ValueError("Could not parse valid action from response")

        except Exception as e:
            logger.error(f"Action parsing failed: {str(e)}")
            return "call"  # Safe fallback

    def _parse_json_action(self, response: str) -> Optional[Dict]:
        """Parse JSON action data from response.

        Returns:
            Optional[Dict]: Parsed action data or None if parsing fails
        """
        try:
            # Find JSON-like structure in response
            json_match = re.search(r"\{[^}]+\}", response)
            if not json_match:
                return None

            action_data = json.loads(json_match.group())

            # Validate required fields
            if "action" not in action_data:
                return None

            # Normalize action
            action_data["action"] = action_data["action"].lower().strip()

            # Validate action value
            if action_data["action"] not in ["fold", "call", "raise"]:
                return None

            return action_data

        except json.JSONDecodeError:
            return None

    def _parse_regex_action(self, response: str) -> Optional[str]:
        """Parse action using regex as fallback method.

        Returns:
            Optional[str]: Parsed action or None if parsing fails
        """
        try:
            # Look for EXECUTE: format
            execute_match = re.search(
                r"EXECUTE:\s*(fold|call|raise(?:\s+\d+)?)", response, re.IGNORECASE
            )
            if execute_match:
                return execute_match.group(1).lower().strip()

            # Alternative: Look for action keywords in text
            action_match = re.search(
                r"\b(fold|call|raise(?:\s+\d+)?)\b", response.lower()
            )
            if action_match:
                return action_match.group(1).strip()

            return None

        except Exception:
            return None

    def _format_action(self, action_data: Dict) -> str:
        """Format parsed action data into final action string.

        Args:
            action_data: Parsed action data dictionary

        Returns:
            str: Formatted action string
        """
        action = action_data["action"]
        if action == "raise" and "raise_amount" in action_data:
            return f"raise {action_data['raise_amount']}"
        return action

    def _validate_raise_amount(self, amount: Union[int, str]) -> Optional[int]:
        """Validate and normalize raise amount.

        Returns:
            Optional[int]: Valid raise amount or None if invalid
        """
        try:
            amount = int(str(amount).strip())
            if amount > 0:
                return amount
            return None
        except (ValueError, TypeError):
            return None

    def generate_message(
        self,
        strategy_style: str,
        game_state: str,
        communication_style: str,
        recent_history: str,
    ) -> str:
        """Generate table talk for the poker agent.

        Args:
            strategy_style: Player's strategic style
            game_state: Current game state
            communication_style: Desired communication style
            recent_history: Recent table history

        Returns:
            str: Generated message for table talk
        """
        message_prompt = f"""
        You are a {strategy_style} poker player with a {communication_style} communication style.
        
        Current situation:
        {game_state}
        
        Recent table history:
        {recent_history}
        
        Generate a short message for table talk.
        Respond with:
        MESSAGE: <your message>
        """

        response = self.query(
            prompt=message_prompt,
            max_tokens=50,  # Shorter for table talk
            system_message=f"You are a {communication_style} {strategy_style} poker player.",
        )

        if "MESSAGE:" in response:
            return response.split("MESSAGE:")[1].strip()
        return response.strip()
