import logging
import os
from typing import Optional

from dotenv import load_dotenv

from agents.prompts import ACTION_PROMPT, PLANNING_PROMPT
from data.types.action_response import ActionResponse, ActionType
from data.types.llm_responses import PlanResponse
from data.types.plan import Plan

from .llm_client import LLMClient

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "")


class LLMStrategyGenerator:
    """
    Encapsulates the logic for generating prompts, querying the LLM,
    and parsing the responses for poker strategy and actions.
    """

    def __init__(
        self,
        strategy_style: str,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
    ):
        self.strategy_style = strategy_style
        self.llm_client = LLMClient(api_key=API_KEY, model=model)

    def generate_plan(self, game_state, hand_eval) -> dict:
        """
        Create a plan by calling the LLM with the appropriate planning prompt.
        Returns the parsed dictionary of plan data.
        """
        prompt = PLANNING_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            hand_eval=hand_eval,
        )
        response = self.llm_client.query(prompt=prompt, temperature=0.7, max_tokens=200)
        return PlanResponse.parse_llm_response(response)

    def generate_action(self, game_state, current_plan: Plan, hand_eval) -> str:
        """
        Create an action by calling the LLM with the action prompt.
        Returns the raw LLM response string for further parsing.
        """
        execution_prompt = ACTION_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            hand_eval=hand_eval,
            plan_approach=current_plan.approach,
            plan_reasoning=current_plan.reasoning,
            bluff_threshold=current_plan.bluff_threshold,
            fold_threshold=current_plan.fold_threshold,
        )
        return self.llm_client.query(
            prompt=execution_prompt,
            temperature=0.7,
            max_tokens=100,
        )

    def parse_action_response(self, response: str) -> ActionResponse:
        """
        Parse the raw LLM response string into an ActionResponse.
        Falls back to ActionType.CALL on errors.
        """
        try:
            return ActionResponse.parse_llm_response(response)
        except Exception as e:
            logger.error(f"[Action] Error parsing action response: {str(e)}")
            return ActionResponse(action_type=ActionType.CALL)
