import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Union, Any

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

    def generate_plan(self, strategy_style: str, game_state: str) -> Dict[str, Any]:
        """Generate a strategic plan using the LLM.

        Args:
            strategy_style: Player's strategic style
            game_state: Current game state

        Returns:
            Dict[str, Any]: Strategic plan containing approach, bet sizing, etc.
        """
        try:
            planning_prompt = f"""You are a {strategy_style} poker player planning your strategy.
            
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

Example valid response:
{{
    "approach": "aggressive",
    "reasoning": "Strong hand and good position",
    "bet_sizing": "large",
    "bluff_threshold": 0.8,
    "fold_threshold": 0.2
}}
"""

            response = self.query(
                prompt=planning_prompt,
                temperature=0.7,
                system_message=f"You are a {strategy_style} poker strategist.",
            )

            # Try to parse JSON response
            try:
                import json
                plan_data = json.loads(response.strip())
                
                # Validate required fields
                required_fields = ['approach', 'reasoning', 'bet_sizing', 'bluff_threshold', 'fold_threshold']
                for field in required_fields:
                    if field not in plan_data:
                        raise ValueError(f"Missing required field: {field}")
                        
                return plan_data
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse plan JSON: {response}")
                # Return default plan
                return {
                    "approach": "balanced",
                    "reasoning": "Default plan due to parsing error",
                    "bet_sizing": "medium",
                    "bluff_threshold": 0.7,
                    "fold_threshold": 0.3
                }

        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}")
            # Return default plan
            return {
                "approach": "balanced",
                "reasoning": "Default plan due to error",
                "bet_sizing": "medium",
                "bluff_threshold": 0.7,
                "fold_threshold": 0.3
            }

    def decide_action(
        self,
        strategy_style: str,
        game_state: str,
        plan: Dict[str, Any],
        min_raise: int,
    ) -> str:
        """Determine the next action based on strategy plan.
        
        Args:
            strategy_style: Current strategy style being used
            game_state: Current state of the game
            plan: Strategic plan dictionary containing approach and parameters
            min_raise: Minimum raise amount allowed
            
        Returns:
            str: Action decision ('fold', 'call', or 'raise X')
        """
        # Create decision prompt with min_raise information
        prompt = f"""You are a {strategy_style} poker player.

Current game state:
{game_state}

Your current strategic plan:
- Approach: {plan['approach']}
- Reasoning: {plan['reasoning']}
- Bet Sizing: {plan['bet_sizing']}
- Bluff Threshold: {plan['bluff_threshold']}
- Fold Threshold: {plan['fold_threshold']}

Important betting rules:
- Minimum raise amount: ${min_raise}
- Any raise must be at least ${min_raise}
- If you want to raise, it must be 'raise X' where X >= {min_raise}

Based on your strategy and the minimum raise requirement, decide your action.
Respond with exactly one line starting with 'ACTION: ' followed by either:
- 'fold'
- 'call'
- 'raise X' (where X is your raise amount, must be >= {min_raise})

Example responses:
ACTION: fold
ACTION: call
ACTION: raise {min_raise}
"""

        try:
            # Query LLM with retry logic
            for attempt in range(3):  # 3 retries
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=50,  # Short response needed
                    )

                    # Extract action from response
                    action_line = None
                    for line in response.choices[0].message.content.split('\n'):
                        if line.startswith('ACTION:'):
                            action_line = line.replace('ACTION:', '').strip().lower()
                            break

                    if action_line:
                        # Validate raise amount if it's a raise
                        if action_line.startswith('raise'):
                            try:
                                _, amount = action_line.split()
                                amount = int(amount)
                                if amount < min_raise:
                                    self.logger.warning(
                                        f"LLM suggested raise {amount} below minimum {min_raise}, adjusting to minimum"
                                    )
                                    return f"raise {min_raise}"
                            except (ValueError, IndexError):
                                self.logger.warning("Invalid raise format from LLM")
                                return "call"  # Safe fallback
                        return action_line
                    
                    self.logger.warning(f"No valid action found in response: {response.choices[0].message.content}")
                    continue  # Try again

                except Exception as e:
                    if attempt < 2:  # Don't log on last attempt
                        self.logger.warning(f"LLM query attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(1)  # Wait before retry
                    continue

            # If all retries failed, return safe default
            self.logger.error("All LLM query attempts failed")
            return "call"

        except Exception as e:
            self.logger.error(f"Error in decide_action: {str(e)}")
            return "call"  # Safe fallback

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
