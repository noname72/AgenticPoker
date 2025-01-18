from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from data.types.action_response import ActionResponse, ActionType
from tests.mocks.mock_llm_client import MockLLMClient
from tests.mocks.mock_player import MockPlayer
from tests.mocks.mock_strategy_planner import MockStrategyPlanner


class MockAgent(MockPlayer):
    """A mock implementation of the Agent class for testing purposes.

    This mock provides the same interface as the real Agent but with configurable
    behaviors for testing different scenarios. It uses other mocks (LLMClient,
    LLMResponseGenerator, StrategyPlanner) to simulate the agent's cognitive modules.

    Usage:
        # Basic initialization
        agent = MockAgent(name="TestBot", chips=1000)

        # Configure specific behaviors
        agent.configure_for_test(
            strategy_style="aggressive",
            should_use_planning=True,
            should_raise_error=False
        )

        # Configure action responses
        agent.set_action_response(
            action_type=ActionType.RAISE,
            amount=100,
            reasoning="Strong hand"
        )

        # Configure messages
        agent.set_message_response("I'm going all in!")

        # Use in tests
        action = agent.decide_action(game_mock)
        message = agent.get_message(game_mock)

        # Verify calls
        agent.decide_action.assert_called_once()
        agent.get_message.assert_called_with(game_mock)

    Default Behaviors:
        - decide_action: Returns configured action or default CALL
        - get_message: Returns configured message or default
        - perceive: Updates perception history with game state
        - decide_discard: Returns configured discard positions
    """

    def __init__(
        self,
        name: str = "TestBot",
        chips: int = 1000,
        strategy_style: str = "Aggressive Bluffer",
        use_planning: bool = True,
    ):
        """Initialize mock agent with configurable parameters."""
        super().__init__(name=name, chips=chips)

        # Basic configuration
        self.strategy_style = strategy_style
        self.use_planning = use_planning
        self.communication_style = "Intimidating"
        self.emotional_state = "confident"

        # Initialize mock components
        self.llm_client = MockLLMClient()
        self.strategy_planner = (
            MockStrategyPlanner(strategy_style) if use_planning else None
        )

        # Create mock methods
        self.decide_action = MagicMock()
        self.get_message = MagicMock()
        self.perceive = MagicMock()
        self.decide_discard = MagicMock()
        self.analyze_opponent = MagicMock()
        self.update_strategy = MagicMock()

        # Set up default behaviors
        self.decide_action.side_effect = self._default_decide_action
        self.get_message.side_effect = self._default_get_message
        self.perceive.side_effect = self._default_perceive
        self.decide_discard.side_effect = self._default_decide_discard

        # Configuration state
        self._action_response = None
        self._message_response = None
        self._discard_positions = []
        self._should_raise_error = False
        self._error_message = "Mock Agent Error"

        # Initialize tracking structures
        self.perception_history = []
        self.conversation_history = []
        self.table_history = []
        self.action_history = []

    def _default_decide_action(self, game) -> ActionResponse:
        """Default behavior for action decisions."""
        if self._should_raise_error:
            raise Exception(self._error_message)

        if self._action_response:
            return self._action_response

        return ActionResponse(action_type=ActionType.CALL)

    def _default_get_message(self, game) -> str:
        """Default behavior for message generation."""
        if self._should_raise_error:
            return "..."

        return self._message_response or "I call."

    def _default_perceive(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> Dict:
        """Default behavior for perception."""
        perception = {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": "mock_timestamp",
        }
        self.perception_history.append(perception)
        return perception

    def _default_decide_discard(
        self, game_state: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Default behavior for discard decisions."""
        return self._discard_positions or []

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
        self._action_response = ActionResponse(
            action_type=action_type,
            amount=amount,
            reasoning=reasoning,
        )
        self.decide_action.reset_mock()

    def set_message_response(self, message: str) -> None:
        """Configure the message response for testing.

        Args:
            message: Message to return
        """
        self._message_response = message
        self.get_message.reset_mock()

    def set_discard_positions(self, positions: List[int]) -> None:
        """Configure the discard positions for testing.

        Args:
            positions: List of card positions to discard
        """
        self._discard_positions = positions
        self.decide_discard.reset_mock()

    def configure_for_test(
        self,
        strategy_style: Optional[str] = None,
        should_use_planning: Optional[bool] = None,
        should_raise_error: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Configure the mock agent's behavior for testing.

        Args:
            strategy_style: Optional strategy style to set
            should_use_planning: Whether to use planning
            should_raise_error: Whether methods should raise errors
            error_message: Custom error message when raising errors
        """
        if strategy_style is not None:
            self.strategy_style = strategy_style

        if should_use_planning is not None:
            self.use_planning = should_use_planning
            if should_use_planning:
                self.strategy_planner = MockStrategyPlanner(self.strategy_style)
            else:
                self.strategy_planner = None

        self._should_raise_error = should_raise_error
        if error_message:
            self._error_message = error_message

    def reset(self) -> None:
        """Reset the mock agent to default state."""
        super().reset()  # Reset MockPlayer state

        self._action_response = None
        self._message_response = None
        self._discard_positions = []
        self._should_raise_error = False
        self._error_message = "Mock Agent Error"

        self.perception_history.clear()
        self.conversation_history.clear()
        self.table_history.clear()
        self.action_history.clear()

        self.decide_action.reset_mock()
        self.get_message.reset_mock()
        self.perceive.reset_mock()
        self.decide_discard.reset_mock()

        if self.strategy_planner:
            self.strategy_planner.reset()

    def __str__(self) -> str:
        """Get string representation of mock agent state."""
        return (
            f"MockAgent: {self.name}, "
            f"Style: {self.strategy_style}, "
            f"Planning: {self.use_planning}, "
            f"Chips: {self.chips}"
        )
