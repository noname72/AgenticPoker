import logging
import os

from dotenv import load_dotenv

from agents.prompts import ACTION_PROMPT, PLANNING_PROMPT
from data.types.action_response import ActionResponse, ActionType
from data.types.llm_responses import PlanResponse
from data.types.plan import Plan

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "")


class LLMResponseGenerator:
    """
    Encapsulates the logic for generating prompts, querying the LLM,
    and parsing the responses for poker strategy and actions.
    """

    @classmethod
    def generate_plan(cls, player, game_state, hand_eval) -> dict:
        """
        Create a plan by calling the LLM with the appropriate planning prompt.
        Returns the parsed dictionary of plan data.
        """
        prompt = PLANNING_PROMPT.format(
            strategy_style=player.strategy_style,
            game_state=game_state,
            hand_eval=hand_eval,
        )
        response = player.llm_client.query(
            prompt=prompt, temperature=0.7, max_tokens=200
        )
        return PlanResponse.parse_llm_response(response)

    @classmethod
    def generate_action(cls, player, game_state, current_plan: Plan, hand_eval) -> str:
        """
        Create an action by calling the LLM with the action prompt.
        Returns the raw LLM response string for further parsing.
        """
        # Set default values if planning is disabled
        plan_approach = getattr(current_plan, "approach", "No specific approach")
        plan_reasoning = getattr(current_plan, "reasoning", "Direct decision making")
        bluff_threshold = getattr(current_plan, "bluff_threshold", 0.5)
        fold_threshold = getattr(current_plan, "fold_threshold", 0.7)

        execution_prompt = ACTION_PROMPT.format(
            strategy_style=player.strategy_style,
            game_state=game_state,
            hand_eval=hand_eval,
            plan_approach=plan_approach,
            plan_reasoning=plan_reasoning,
            bluff_threshold=bluff_threshold,
            fold_threshold=fold_threshold,
        )
        return player.llm_client.query(
            prompt=execution_prompt,
            temperature=0.7,
            max_tokens=100,
        )

    @classmethod
    def parse_action_response(cls, response: str) -> ActionResponse:
        #! is this used anywhere???
        """
        Parse the raw LLM response string into an ActionResponse.
        Falls back to ActionType.CALL on errors.
        """
        try:
            return ActionResponse.parse_llm_response(response)
        except Exception as e:
            logger.error(f"[Action] Error parsing action response: {str(e)}")
            return ActionResponse(action_type=ActionType.CALL)
