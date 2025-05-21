import logging
import random
from typing import Any, Dict, List, Optional

from data.model import Game
from data.types.action_decision import ActionDecision, ActionType
from data.types.discard_decision import DiscardDecision
from game.evaluator import HandEvaluation
from game.player import Player

logger = logging.getLogger(__name__)


class RandomAgent(Player):
    """A poker player that makes random decisions."""

    def __init__(self, name: str, chips: int = 1000):
        """Initialize the random agent."""
        super().__init__(name, chips)

    def decide_action(
        self, game: "Game", hand_eval: Optional[HandEvaluation] = None
    ) -> ActionDecision:
        """Randomly decide an action based on valid options for both game types.

        Args:
            game: The current game state object.
            hand_eval: Optional hand evaluation (not used by RandomAgent).

        Returns:
            ActionDecision: The randomly chosen action.
        """
        possible_actions: List[ActionDecision] = []

        # FOLD is always an option (unless player is forced all-in by blinds, which Player.execute handles)
        possible_actions.append(ActionDecision(action_type=ActionType.FOLD))

        amount_to_call = game.current_bet - self.bet
        can_afford_call = self.chips >= amount_to_call

        # CHECK / CALL Logic
        if amount_to_call <= 0: # No bet to call, or already called enough
            possible_actions.append(ActionDecision(action_type=ActionType.CHECK))
        elif self.chips > 0 : # There's a bet to call and player has chips
            # Amount for CALL action is the additional amount needed.
            # Player.execute will cap it at self.chips if necessary.
            possible_actions.append(ActionDecision(action_type=ActionType.CALL, amount=amount_to_call))

        # BET Logic (only if no current bet from another player in this round)
        if game.current_bet == 0 and self.chips > 0:
            if game.game_type == "TEXAS_HOLDEM":
                min_bet_nl = game.big_blind
                if self.chips >= min_bet_nl:
                    # Bet between min_bet_nl and all-in
                    bet_val = random.randint(min_bet_nl, self.chips)
                    possible_actions.append(ActionDecision(action_type=ActionType.BET, amount=bet_val))
                else: # Can only bet all-in (less than min_bet_nl)
                    possible_actions.append(ActionDecision(action_type=ActionType.BET, amount=self.chips))
            else: # FIVE_CARD_DRAW (Limit)
                # Bet is typically fixed, e.g., game.big_blind
                fixed_bet_fcd = game.big_blind # Or game.config.min_bet from GameConfig
                if self.chips >= fixed_bet_fcd:
                    possible_actions.append(ActionDecision(action_type=ActionType.BET, amount=fixed_bet_fcd))
                else: # Can bet all-in if less than fixed bet
                     possible_actions.append(ActionDecision(action_type=ActionType.BET, amount=self.chips))
        
        # RAISE Logic (only if there is a current bet to raise, and player has chips beyond the call amount)
        chips_after_call = self.chips - amount_to_call
        if game.current_bet > 0 and chips_after_call > 0 and can_afford_call :
            if game.game_type == "TEXAS_HOLDEM":
                # Min additional raise amount for NLHE
                min_additional_raise = max(game.table.min_raise_amount, game.big_blind)
                if chips_after_call >= min_additional_raise:
                    max_additional_raise = chips_after_call # Can raise by up to remaining stack
                    raise_val = random.randint(min_additional_raise, max_additional_raise)
                    possible_actions.append(ActionDecision(action_type=ActionType.RAISE, amount=raise_val))
                elif chips_after_call > 0: # Can go all-in, but this raise is less than min_additional_raise
                    possible_actions.append(ActionDecision(action_type=ActionType.RAISE, amount=chips_after_call))

            else: # FIVE_CARD_DRAW (Limit)
                max_raises = game.config.max_raises_per_round if game.config.max_raises_per_round is not None else float('inf')
                current_raises = game.round_state.raise_count if game.round_state and hasattr(game.round_state, 'raise_count') else 0
                
                if current_raises < max_raises:
                    fixed_raise_fcd = game.big_blind # Fixed raise amount for limit
                    if chips_after_call >= fixed_raise_fcd:
                        possible_actions.append(ActionDecision(action_type=ActionType.RAISE, amount=fixed_raise_fcd))
                    elif chips_after_call > 0: # All-in raise, less than fixed amount
                        possible_actions.append(ActionDecision(action_type=ActionType.RAISE, amount=chips_after_call))

        # Filter out FOLD if player is already all-in and facing no further bet increase
        # (This state is complex, Player.execute handles most all-in mechanics)
        # For RandomAgent, if it's all-in (self.chips == 0) and amount_to_call is 0, it can only CHECK.
        if self.is_all_in and amount_to_call <= 0: # Already all-in and current bet is met or less
            possible_actions = [ActionDecision(ActionType.CHECK)] # Only check is possible

        # If no actions are possible (e.g. forced all-in and no valid options generated), default to FOLD.
        # This should ideally not be reached if FOLD is always added and CHECK/CALL logic is correct.
        if not possible_actions:
            logger.warning(f"{self.name} had no possible actions. Defaulting to FOLD.")
            return ActionDecision(action_type=ActionType.FOLD)
        
        # Ensure that if a call is required, CHECK is not chosen.
        final_actions_to_choose = []
        if amount_to_call > 0: # Must call or raise or fold
            for pa in possible_actions:
                if pa.action_type != ActionType.CHECK:
                    final_actions_to_choose.append(pa)
            if not final_actions_to_choose : # Should not happen if FOLD is always there
                 final_actions_to_choose.append(ActionDecision(action_type=ActionType.FOLD))
        else: # Can check
            final_actions_to_choose = possible_actions

        chosen_action = random.choice(final_actions_to_choose)
        logger.info(f"{self.name} (chips: {self.chips}, bet: {self.bet}, current_bet: {game.current_bet}, amount_to_call: {amount_to_call}) chose action: {chosen_action.action_type.name} {chosen_action.amount if chosen_action.amount is not None else ''}")
        return chosen_action

    def decide_discard(self) -> DiscardDecision:
        """Randomly decide which cards to discard.

        Returns:
            DiscardDecision: Contains list of card indices (0-4) to discard
        """
        # Randomly discard 0-3 cards
        num_to_discard = random.randint(0, 3)
        if num_to_discard == 0:
            return DiscardDecision(discard=[])

        # Get random positions to discard
        positions = list(range(5))  # 5 card positions
        discard_indices = sorted(random.sample(positions, num_to_discard))
        return DiscardDecision(discard=discard_indices)

    def get_message(self, game_state: str) -> str:
        """Return empty string as random agent doesn't communicate."""
        return ""

    def decide_draw(self) -> List[int]:
        """Randomly decide which cards to draw."""
        # Randomly discard 0-3 cards
        num_to_discard = random.randint(0, 3)
        if num_to_discard == 0:
            return []

        # Get random positions to discard
        positions = list(range(5))  # 5 card positions
        return sorted(random.sample(positions, num_to_discard))

    def perceive(self, game_state: str, opponent_message: str) -> Dict[str, Any]:
        """Do nothing as random agent doesn't track game state."""
        return {}

    def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
        """Do nothing as random agent doesn't learn."""
        pass
