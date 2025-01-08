from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RoundState:
    """Represents the state of a single round of poker.

    Tracks all information specific to the current round including betting phases,
    player actions, pot evolution, and position tracking. This class maintains the
    complete state needed to manage a poker round from start to finish.

    Attributes:
        round_number (int): Sequential number identifying the current round
        phase (str): Current phase of the round ('pre_draw' or 'post_draw')
        current_bet (int): The current bet amount that players must match
        raise_count (int): Number of raises made in the current betting round
        last_raiser (Optional[str]): Name of the player who made the last raise
        last_aggressor (Optional[str]): Name of the last player to bet or raise
        needs_to_act (List[str]): Players who haven't acted in current betting round
        acted_this_phase (List[str]): Players who have already acted this phase
        dealer_position (Optional[int]): Index position of the dealer
        small_blind_position (Optional[int]): Index position of the small blind
        big_blind_position (Optional[int]): Index position of the big blind
        first_bettor_index (Optional[int]): Index of first player to bet this round
        main_pot (int): Total amount in the main pot
        side_pots (List[Dict[str, Any]]): List of side pots when players are all-in
        cards_drawn (Dict[str, int]): Maps player names to number of cards drawn
        is_complete (bool): Whether the round has finished
        winner (Optional[str]): Name of the winning player, if round is complete
    """

    # Round identification
    round_number: int
    phase: str  # "pre_draw" or "post_draw"

    # Betting round state
    current_bet: int = 0
    raise_count: int = 0
    last_raiser: Optional[str] = None  # Name of player who last raised
    last_aggressor: Optional[str] = None  # Name of last player to bet/raise
    needs_to_act: List[str] = field(
        default_factory=list
    )  # Names of players who still need to act
    acted_this_phase: List[str] = field(
        default_factory=list
    )  # Names of players who have acted

    # Position tracking
    dealer_position: Optional[int] = None
    small_blind_position: Optional[int] = None
    big_blind_position: Optional[int] = None
    first_bettor_index: Optional[int] = None

    # Pot tracking
    main_pot: int = 0
    side_pots: List[Dict[str, Any]] = field(default_factory=list)

    # Draw phase tracking
    cards_drawn: Dict[str, int] = field(
        default_factory=dict
    )  # Player name -> number of cards drawn

    # Round completion
    is_complete: bool = False
    winner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert round state to dictionary representation.

        Returns:
            Dict[str, Any]: A nested dictionary containing all round state information,
                organized by category (round info, betting state, positions, pot state,
                and draw phase information).
        """
        return {
            "round": {
                "number": self.round_number,
                "phase": self.phase,
                "is_complete": self.is_complete,
                "winner": self.winner,
            },
            "betting": {
                "current_bet": self.current_bet,
                "raise_count": self.raise_count,
                "last_raiser": self.last_raiser,
                "last_aggressor": self.last_aggressor,
                "needs_to_act": self.needs_to_act,
                "acted_this_phase": self.acted_this_phase,
            },
            "positions": {
                "dealer": self.dealer_position,
                "small_blind": self.small_blind_position,
                "big_blind": self.big_blind_position,
                "first_bettor": self.first_bettor_index,
            },
            "pot": {"main": self.main_pot, "side_pots": self.side_pots},
            "draw_phase": {"cards_drawn": self.cards_drawn},
        }

    @classmethod
    def new_round(cls, round_number: int) -> "RoundState":
        """Create a new round state.

        Args:
            round_number (int): The sequential number for this round

        Returns:
            RoundState: A new RoundState instance initialized for the pre-draw phase
        """
        return cls(round_number=round_number, phase="pre_draw")

    def advance_phase(self) -> None:
        """Advance to the next phase of the round.

        Transitions from pre-draw to post-draw phase, or marks the round as complete.
        Resets betting-related state when moving to post-draw phase, including:
        - Current bet amount
        - Raise count
        - Last raiser and aggressor
        - Lists of players who need to act or have acted
        """
        if self.phase == "pre_draw":
            self.phase = "post_draw"
            self.current_bet = 0
            self.raise_count = 0
            self.last_raiser = None
            self.last_aggressor = None
            self.needs_to_act.clear()
            self.acted_this_phase.clear()
        else:
            self.is_complete = True

    def record_action(
        self, player_name: str, action: str, amount: Optional[int] = None
    ) -> None:
        """Record a player's action in the current phase.

        Updates the round state to reflect a player's action, including tracking
        who has acted and managing betting-related state.

        Args:
            player_name (str): Name of the player taking the action
            action (str): Type of action taken ('bet', 'raise', etc.)
            amount (Optional[int]): Bet or raise amount, if applicable

        Note:
            When recording a bet or raise:
            - Updates the last raiser and aggressor
            - Increments the raise count
            - Sets the current bet amount if provided
        """
        self.acted_this_phase.append(player_name)
        if player_name in self.needs_to_act:
            self.needs_to_act.remove(player_name)

        if action in ["bet", "raise"]:
            self.last_raiser = player_name
            self.last_aggressor = player_name
            self.raise_count += 1
            if amount is not None:
                self.current_bet = amount
