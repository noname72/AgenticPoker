from typing import Dict, Optional
from unittest.mock import MagicMock

from data.types.action_decision import ActionDecision, ActionType
from data.types.llm_responses import PlanResponse
from data.types.plan import Plan


class MockLLMResponseGenerator:
    """A mock implementation of the LLMResponseGenerator class for testing purposes.

    This mock provides the same interface as the real LLMResponseGenerator but with
    configurable responses for testing different planning and action scenarios.

    Usage:
        # Basic initialization
        generator = MockLLMResponseGenerator()

        # Configure plan response
        generator.set_plan_response({
            "approach": "aggressive",
            "reasoning": "Strong hand",
            "bluff_threshold": 0.3,
            "fold_threshold": 0.8
        })

        # Configure action response
        generator.set_action_response(
            action_type=ActionType.RAISE,
            amount=100,
            reasoning="Strong hand, applying pressure"
        )

        # Use in tests
        plan = generator.generate_plan(player_mock, game_state_mock, hand_eval_mock)
        action = generator.generate_action(
            player_mock,
            game_state_mock,
            plan_mock,
            hand_eval_mock
        )

        # Verify calls
        generator.generate_plan.assert_called_once()
        generator.generate_action.assert_called_with(
            player_mock,
            game_state_mock,
            plan_mock,
            hand_eval_mock
        )

    Default Behaviors:
        - generate_plan: Returns configured plan or default conservative plan
        - generate_action: Returns configured action or default CALL action
        - parse_action_response: Returns configured ActionDecision
    """

    def __init__(self):
        """Initialize mock response generator with default configurations."""
        # Create mock methods
        self.generate_plan = MagicMock()
        self.generate_action = MagicMock()
        self.parse_action_response = MagicMock()

        # Set up default behaviors
        self.generate_plan.side_effect = self._default_generate_plan
        self.generate_action.side_effect = self._default_generate_action
        self.parse_action_response.side_effect = self._default_parse_action_response

        # Response configuration
        self._plan_response = None
        self._action_response = None
        self._parsed_action_response = None

    def _default_generate_plan(self, player, game_state, hand_eval) -> Dict:
        """Default behavior for plan generation."""
        if self._plan_response is not None:
            return self._plan_response

        # Return a default conservative plan
        return {
            "approach": "conservative",
            "reasoning": "Default testing approach",
            "bluff_threshold": 0.5,
            "fold_threshold": 0.7,
        }

    def _default_generate_action(
        self, player, game_state, current_plan: Plan, hand_eval
    ) -> str:
        """Default behavior for action generation."""
        if self._action_response is not None:
            return self._action_response

        # Return a default CALL action
        return "ACTION: CALL\nREASONING: Default testing action"

    def _default_parse_action_response(self, response: str) -> ActionDecision:
        """Default behavior for action response parsing."""
        if self._parsed_action_response is not None:
            return self._parsed_action_response

        # Return a default CALL action response
        return ActionDecision(
            action_type=ActionType.CALL,
            amount=0,
            reasoning="Default parsed action response",
        )

    def set_plan_response(
        self,
        approach: str = "conservative",
        reasoning: str = "Test reasoning",
        bluff_threshold: float = 0.5,
        fold_threshold: float = 0.7,
    ) -> None:
        """Configure the plan response for testing.

        Args:
            approach: Strategy approach
            reasoning: Plan reasoning
            bluff_threshold: Threshold for bluffing
            fold_threshold: Threshold for folding
        """
        self._plan_response = {
            "approach": approach,
            "reasoning": reasoning,
            "bluff_threshold": bluff_threshold,
            "fold_threshold": fold_threshold,
        }
        self.generate_plan.reset_mock()

    def set_action_response(
        self,
        action_type: ActionType = ActionType.CALL,
        amount: int = 0,
        reasoning: str = "Test reasoning",
    ) -> None:
        """Configure the action response for testing.

        Args:
            action_type: Type of action
            amount: Bet/raise amount
            reasoning: Action reasoning
        """
        self._action_response = (
            f"ACTION: {action_type.value}\n"
            f"AMOUNT: {amount}\n"
            f"REASONING: {reasoning}"
        )
        self._parsed_action_response = ActionDecision(
            action_type=action_type,
            amount=amount,
            reasoning=reasoning,
        )
        self.generate_action.reset_mock()
        self.parse_action_response.reset_mock()

    def configure_for_test(
        self,
        plan_response: Optional[Dict] = None,
        action_type: Optional[ActionType] = None,
        action_amount: int = 0,
        action_reasoning: str = "Test reasoning",
    ) -> None:
        """Configure both plan and action responses in one call.

        Args:
            plan_response: Optional plan response dictionary
            action_type: Optional action type
            action_amount: Action amount
            action_reasoning: Action reasoning
        """
        if plan_response is not None:
            self.set_plan_response(**plan_response)

        if action_type is not None:
            self.set_action_response(action_type, action_amount, action_reasoning)

    def reset_responses(self) -> None:
        """Reset all configured responses to defaults."""
        self._plan_response = None
        self._action_response = None
        self._parsed_action_response = None
        self.generate_plan.reset_mock()
        self.generate_action.reset_mock()
        self.parse_action_response.reset_mock()

    def __str__(self) -> str:
        """Get string representation of mock generator state."""
        return (
            f"MockLLMResponseGenerator: "
            f"Plan: {self._plan_response is not None}, "
            f"Action: {self._action_response is not None}"
        )
