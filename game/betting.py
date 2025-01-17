from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Union

from data.states.round_state import RoundPhase
from data.types.action_response import ActionType
from data.types.pot_types import SidePot
from loggers.betting_logger import BettingLogger

from .player import Player

if TYPE_CHECKING:
    from game.game import Game


def betting_round(
    game: "Game",
) -> Union[int, Tuple[int, List[SidePot]]]:
    """Manages a complete round of betting among active players.

    This function handles the core betting mechanics for a poker round, including:
    - Processing actions from each active player
    - Tracking betting amounts and pot size
    - Managing all-in situations and side pot creation
    - Ensuring proper betting order and round completion

    Args:
        game: The Game instance containing all game state, including players,
             pot manager, and round state.

    Returns:
        Either:
        - int: The new pot amount (if no side pots were created)
        - Tuple[int, List[SidePot]]: The new pot amount and list of side pots created
          from all-in situations
    """
    active_players: List[Player] = [p for p in game.players if not p.folded]
    all_in_players: List[Player] = [p for p in active_players if p.is_all_in]
    round_complete: bool = False
    last_raiser: Optional[Player] = None

    # Get big blind player based on position
    big_blind_player: Optional[Player] = _get_big_blind_player(game, active_players)

    # Track who needs to act and who has acted since last raise
    needs_to_act: Set[Player] = set(active_players)
    acted_since_last_raise: Set[Player] = set()

    # Main betting loop
    while not round_complete:
        _process_betting_cycle(
            game, active_players, needs_to_act, acted_since_last_raise, last_raiser
        )

        # Consolidated round-completion check
        round_complete = _is_round_complete(needs_to_act, active_players)

    # If any all-ins occurred, compute side pots
    if all_in_players:
        game.pot_manager.side_pots = game.pot_manager.calculate_side_pots(
            active_players
        )


def _is_round_complete(
    needs_to_act: Set[Player],
    active_players: List[Player],
) -> bool:
    """
    Returns True if any stopping condition is met:
    - No players need to act
    - 0 or 1 players left with chips
    """
    return len(needs_to_act) == 0 or sum(p.chips > 0 for p in active_players) <= 1


def _process_betting_cycle(
    game: "Game",
    active_players: List[Player],
    needs_to_act: Set[Player],
    acted_since_last_raise: Set[Player],
    last_raiser: Optional[Player],
) -> None:
    """
    Process a single cycle of betting for all active players.

    This function handles each player's turn in the current betting cycle.
    It no longer returns a value because the round completion logic is
    managed entirely in betting_round.
    """
    for agent in active_players:
        should_skip, reason = _should_skip_player(agent, needs_to_act)
        if should_skip:
            continue

        BettingLogger.log_player_turn(
            player_name=agent.name,
            hand=agent.hand.show() if hasattr(agent, "hand") else "Unknown",
            chips=agent.chips,
            current_bet=agent.bet,
            pot=game.pot_manager.pot,
            active_players=[p.name for p in active_players if not p.folded],
            last_raiser=last_raiser.name if last_raiser else None,
        )

        action_decision = agent.decide_action(game)
        agent.execute(action_decision, game)

        last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
            agent,
            action_decision.action_type,
            active_players,
            needs_to_act,
            acted_since_last_raise,
        )

        _should_continue_betting(
            active_players, acted_since_last_raise, last_raiser, needs_to_act
        )

        BettingLogger.log_line_break()


def handle_betting_round(
    game: "Game",
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """Manages a complete betting round and updates game state accordingly.

    This function serves as the main entry point for handling a betting round.
    It performs input validation, manages the betting process, and updates the
    game state with the results.

    Args:
        game: Game object containing all game state and player information

    Returns:
        Tuple containing:
        - int: New pot amount after the betting round
        - Optional[List[SidePot]]: Any side pots created during all-in situations,
          or None if no side pots were created
        - bool: Whether the game should continue (True if multiple players remain)

    Raises:
        ValueError: If there are no players or if the pot amount is negative
        TypeError: If any element in the players list is not a Player instance
    """
    if not game.players:
        raise ValueError("Cannot run betting round with no players")

    # Initialize pot to 0 if None
    if game.pot_manager.pot is None:
        game.pot_manager.pot = 0
    elif game.pot_manager.pot < 0:
        raise ValueError("Pot amount cannot be negative")

    if any(not isinstance(p, Player) for p in game.players):
        raise TypeError("All elements in players list must be Player instances")

    # Run betting round with validated GameState
    result = betting_round(game)

    # Handle return value based on whether side pots were created
    if isinstance(result, tuple):
        new_pot, side_pots = result
    else:
        new_pot = result
        side_pots = None

    # Update game state
    game.pot_manager.main_pot = new_pot
    if side_pots:
        game.pot_manager.side_pots = [
            {
                "amount": pot.amount,
                "eligible_players": pot.eligible_players,  # Already strings, no need to convert
            }
            for pot in side_pots
        ]

    # Determine if game should continue
    active_count = sum(1 for p in game.players if not p.folded)
    should_continue = active_count > 1

    return new_pot, side_pots, should_continue


def validate_bet_to_call(current_bet: int, player_bet: int) -> int:
    """Calculates the amount a player needs to add to call the current bet.

    This function determines how many more chips a player needs to commit to match
    the current betting amount, accounting for any chips they've already bet in
    this round.

    Args:
        current_bet: The current bet amount that needs to be matched
        player_bet: The amount the player has already bet in this round

    Returns:
        int: The additional amount the player needs to bet to call. Returns 0 if
             the player has already bet enough.
    """
    bet_to_call = max(
        0, current_bet - player_bet
    )  # Works for both blinds and everyone else
    return bet_to_call


def collect_blinds_and_antes(players, dealer_index, small_blind, big_blind, ante, game):
    """Collects mandatory bets (blinds and antes) from players.

    This function handles the collection of forced bets at the start of a hand:
    - Collects antes from all players (if applicable)
    - Collects small blind from the player after the dealer
    - Collects big blind from the player after the small blind

    Args:
        players: List of all players in the game
        dealer_index: Position of the dealer button
        small_blind: Amount of the small blind
        big_blind: Amount of the big blind
        ante: Amount of the ante (0 if no ante)
        game: Game instance for updating game state

    Returns:
        int: Total amount collected from blinds and antes
    """
    collected = 0
    num_players = len(players)

    # Collect antes
    if ante > 0:
        BettingLogger.log_collecting_antes()
        for player in players:
            ante_amount = min(ante, player.chips)
            player.chips -= ante_amount
            collected += ante_amount

            BettingLogger.log_blind_or_ante(
                player.name, ante, ante_amount, is_ante=True
            )

    # Small blind
    sb_index = (dealer_index + 1) % num_players
    sb_player = players[sb_index]
    sb_amount = min(small_blind, sb_player.chips)
    actual_sb = sb_player.place_bet(sb_amount, game)
    collected += actual_sb

    BettingLogger.log_blind_or_ante(
        sb_player.name, small_blind, actual_sb, is_small_blind=True
    )

    # Big blind
    bb_index = (dealer_index + 2) % num_players
    bb_player = players[bb_index]
    bb_amount = min(big_blind, bb_player.chips)
    actual_bb = bb_player.place_bet(bb_amount, game)
    collected += actual_bb

    BettingLogger.log_blind_or_ante(bb_player.name, big_blind, actual_bb)

    BettingLogger.log_line_break()
    return collected


def _get_big_blind_player(
    game: "Game", active_players: List[Player]
) -> Optional[Player]:
    """Get the big blind player and set their flag.

    Args:
        game: Game instance
        active_players: List of active players

    Returns:
        Optional[Player]: The big blind player if found, None otherwise
    """
    is_preflop = game.round_state and game.round_state.phase == RoundPhase.PREFLOP

    if (
        is_preflop
        and game.round_state
        and game.round_state.big_blind_position is not None
    ):
        bb_index = game.round_state.big_blind_position
        if 0 <= bb_index < len(active_players):
            big_blind_player = active_players[bb_index]
            # Set flag on player object for bet validation
            big_blind_player.is_big_blind = True
            return big_blind_player

    return None


def _should_skip_player(player: Player, needs_to_act: Set[Player]) -> Tuple[bool, str]:
    """Determines if a player should be skipped in the betting round.

    Args:
        player: The player to check
        needs_to_act: Set of players that still need to act

    Returns:
        Tuple[bool, str]: (should_skip, reason)
    """
    if player.folded or player.chips == 0:
        BettingLogger.log_skip_player(player.name, "folded or has no chips")
        return True, "folded or has no chips"

    if player not in needs_to_act:
        BettingLogger.log_skip_player(player.name, "doesn't need to act")
        return True, "doesn't need to act"

    return False, ""


def _update_action_tracking(
    agent: Player,
    action_type: ActionType,
    active_players: List[Player],
    needs_to_act: Set[Player],
    acted_since_last_raise: Set[Player],
) -> Tuple[Optional[Player], Set[Player], Set[Player]]:
    """Updates player action tracking sets after a betting action.

    Args:
        agent: The player who just acted
        action_type: The type of action taken
        active_players: List of players still in the hand
        needs_to_act: Set of players that still need to act
        acted_since_last_raise: Set of players who have acted since last raise

    Returns:
        Tuple containing:
        - Optional[Player]: The new last raiser (if any)
        - Set[Player]: Updated needs_to_act set
        - Set[Player]: Updated acted_since_last_raise set
    """
    last_raiser = None

    if action_type == ActionType.RAISE:
        last_raiser = agent
        # Reset acted_since_last_raise set
        acted_since_last_raise = {agent}
        # Everyone except the raiser needs to act again
        needs_to_act = set(
            p for p in active_players if p != agent and not p.folded and p.chips > 0
        )
    else:
        # Add player to acted set and remove from needs_to_act
        acted_since_last_raise.add(agent)
        needs_to_act.discard(agent)

    return last_raiser, needs_to_act, acted_since_last_raise


def _should_continue_betting(
    active_players: List[Player],
    acted_since_last_raise: Set[Player],
    last_raiser: Optional[Player],
    needs_to_act: Set[Player],
) -> None:
    """Determines if betting should continue and updates who needs to act.

    Args:
        active_players: List of players still in the hand
        acted_since_last_raise: Set of players who have acted since last raise
        last_raiser: The last player who raised
        needs_to_act: Set of players that still need to act

    Side Effects:
        Updates needs_to_act set based on betting conditions
    """
    # Get active non-folded players with chips
    active_non_folded = set(p for p in active_players if not p.folded and p.chips > 0)
    all_acted = acted_since_last_raise == active_non_folded

    # If everyone has acted since last raise, give last raiser final chance
    if all_acted and last_raiser and not last_raiser.folded and last_raiser.chips > 0:
        needs_to_act.clear()
        needs_to_act.add(last_raiser)
    elif all_acted:
        needs_to_act.clear()  # No one else needs to act
