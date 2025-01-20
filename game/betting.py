"""Poker betting round management and rules implementation.

This module handles all betting-related logic for a poker game, including:

Betting Order:
- Pre-flop: Action starts with player after big blind
- Post-flop: Action starts with first active player after dealer
- Big blind gets special privileges pre-flop (acts last if no raises)

Betting Rules:
1. Each player can:
   - Fold: Give up their hand and any right to the pot
   - Call: Match the current bet amount
   - Raise: Increase the current bet amount
   - Check: Pass action if no bets to call (equivalent to calling zero)

2. Betting Rounds:
   - Continue until all active players have:
     a) Put the same amount of chips in the pot
     b) Gone all-in with their remaining chips
     c) Folded their hand

3. Special Rules:
   - Pre-flop big blind rules:
     * BB acts last if everyone calls
     * BB can raise even if everyone just calls
     * BB must act again if someone raises
   - All-in rules:
     * Players can't be forced to fold if they can't match full bet
     * Side pots created when players go all-in for different amounts

The module uses a combination of sets and flags to track:
- Which players still need to act
- Who has acted since the last raise
- The last player to raise
- Special status (e.g., big blind, all-in)

Key Components:
- betting_round: Core betting loop and round management
- handle_betting_round: Main entry point with validation
- collect_blinds_and_antes: Handles forced bets
- Various helper functions for action tracking and validation
"""

from typing import TYPE_CHECKING, Optional, Set, Tuple

from data.states.round_state import RoundPhase
from data.types.action_response import ActionType
from loggers.betting_logger import BettingLogger

from .player import Player
from .player_queue import PlayerQueue

if TYPE_CHECKING:
    from game.game import Game


def handle_betting_round(game: "Game") -> bool:
    """Manages a complete betting round and updates game state accordingly.

    This function serves as the main entry point for handling a betting round.
    It performs the following:
    1. Input validation (players exist, pot is valid)
    2. Manages the betting process
    3. Handles side pot creation for all-in situations
    4. Updates game state with results
    5. Determines if the game should continue

    Args:
        game: Game object containing all game state and player information

    Returns:
        bool: Whether the game should continue (True if multiple players remain)

    Raises:
        ValueError: If there are no players or if the pot amount is negative
        TypeError: If any element in the players list is not a Player instance

    Side Effects:
        - Updates game.pot_manager with new pot amounts and side pots
        - May modify player chip counts and betting amounts
    """
    if not game.players:
        raise ValueError("Cannot run betting round with no players")

    # Initialize pot to 0 if None
    if game.pot_manager.pot is None:
        game.pot_manager.pot = 0
    elif game.pot_manager.pot < 0:
        raise ValueError("Pot amount cannot be negative")

    # Run betting round with validated GameState
    betting_round(game)

    # Determine if game should continue
    active_count = sum(1 for p in game.players if not p.folded)
    should_continue = active_count > 1

    return should_continue


def betting_round(game: "Game") -> None:
    """Manages a complete round of betting among active players.

    This function handles the core betting mechanics for a poker round, including:
    - Processing actions from each active player
    - Tracking betting amounts and pot size
    - Ensuring proper betting order and round completion

    Args:
        game: The Game instance containing all game state, including players,
             pot manager, and round state.
    """

    round_complete: bool = False
    last_raiser: Optional[Player] = None

    # Get big blind player based on position
    big_blind_player: Optional[Player] = _get_big_blind_player(game)

    # If it's preflop and big blind player exists, they should act last if no raises
    if big_blind_player and game.round_state.phase == RoundPhase.PREFLOP:
        game.players.needs_to_act.discard(big_blind_player)  # Remove BB initially
        game.players.acted_since_last_raise.add(
            big_blind_player
        )  # Mark BB as having acted

    # Main betting loop
    while not round_complete:
        _process_betting_cycle(
            game,
            last_raiser,
            big_blind_player,
        )

        # Check if round is complete
        round_complete = (
            game.players.is_round_complete() or game.players.all_players_acted()
        )


def _process_betting_cycle(
    game: "Game",
    last_raiser: Optional[Player],
    big_blind_player: Optional[Player],
) -> None:
    """Process a single cycle of betting for all active players."""
    # Add safety counter to prevent infinite loops
    max_iterations = len(game.players) * 2
    iteration_count = 0

    while not game.players.is_round_complete():
        iteration_count += 1
        if iteration_count > max_iterations:
            BettingLogger.log_line_break()
            BettingLogger.log_message(
                "Breaking potential infinite loop - all players skipped"
            )
            # Clear needs_to_act to properly end the round
            game.players.needs_to_act.clear()
            break

        agent = game.players.get_next_player()
        if not agent:
            # No more active players, clear needs_to_act and end round
            game.players.needs_to_act.clear()
            break

        should_skip, reason = _should_skip_player(agent, game.players.needs_to_act)
        if should_skip:
            game.players.needs_to_act.discard(agent)
            # If all players are being skipped, end the round
            if len(game.players.needs_to_act) == 0:
                break
            continue

        BettingLogger.log_player_turn(
            player_name=agent.name,
            hand=agent.hand.show() if hasattr(agent, "hand") else "Unknown",
            chips=agent.chips,
            current_bet=agent.bet,
            pot=game.pot_manager.pot,
            active_players=[p.name for p in game.players.players if not p.folded],
            last_raiser=last_raiser.name if last_raiser else None,
        )

        action_decision = agent.decide_action(game)
        agent.execute(action_decision, game)

        last_raiser = _update_action_tracking(
            agent,
            action_decision.action_type,
            game.players,
            big_blind_player,
            game.round_state.phase == RoundPhase.PREFLOP,
        )

        _should_continue_betting(game.players, last_raiser)

        BettingLogger.log_line_break()


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


def collect_blinds_and_antes(game, dealer_index, small_blind, big_blind, ante):
    """Collects mandatory bets (blinds and antes) from players.

    This function handles the collection of forced bets at the start of a hand:
    - Collects antes from all players (if applicable)
    - Collects small blind from the player after the dealer
    - Collects big blind from the player after the small blind

    Args:
        game: Game instance for updating game state
        dealer_index: Position of the dealer button
        small_blind: Amount of the small blind
        big_blind: Amount of the big blind
        ante: Amount of the ante (0 if no ante)

    Returns:
        int: Total amount collected from blinds and antes
    """
    collected = 0
    num_players = len(game.players)

    # Reset all player bets first
    for player in game.players:
        player.bet = 0

    # Collect antes
    if ante > 0:
        BettingLogger.log_collecting_antes()
        for player in game.players:
            ante_amount = min(ante, player.chips)
            collected += player.place_bet(ante_amount, game)
            BettingLogger.log_blind_or_ante(
                player.name, ante, ante_amount, is_ante=True
            )

    # Reset bets after antes
    for player in game.players:
        player.bet = 0

    # Small blind
    sb_index = (dealer_index + 1) % num_players
    sb_player = game.players[sb_index]
    sb_amount = min(small_blind, sb_player.chips)
    actual_sb = sb_player.place_bet(sb_amount, game)
    collected += actual_sb

    BettingLogger.log_blind_or_ante(
        sb_player.name, small_blind, actual_sb, is_small_blind=True
    )

    # Big blind
    bb_index = (dealer_index + 2) % num_players
    bb_player = game.players[bb_index]
    bb_amount = min(big_blind, bb_player.chips)
    actual_bb = bb_player.place_bet(bb_amount, game)
    collected += actual_bb

    BettingLogger.log_blind_or_ante(bb_player.name, big_blind, actual_bb)

    BettingLogger.log_line_break()
    return collected


def _get_big_blind_player(game: "Game") -> Optional[Player]:
    """Get the big blind player and set their flag.

    Args:
        game: Game instance

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
        if 0 <= bb_index < len(game.players):
            big_blind_player = game.players[bb_index]
            # Set flag on player object for bet validation
            big_blind_player.is_big_blind = True
            return big_blind_player

    return None


def _should_skip_player(player: Player, needs_to_act: Set[Player]) -> Tuple[bool, str]:
    """Determines if a player should be skipped in the betting round."""
    if player.folded:
        BettingLogger.log_skip_player(player.name, "folded")
        return True, "folded"

    if player.chips == 0:
        BettingLogger.log_skip_player(player.name, "has no chips")
        return True, "has no chips"

    if player not in needs_to_act:
        BettingLogger.log_skip_player(player.name, "doesn't need to act")
        return True, "doesn't need to act"

    return False, ""


def _update_action_tracking(
    agent: Player,
    action_type: ActionType,
    player_queue: PlayerQueue,
    big_blind_player: Optional[Player],
    is_preflop: bool,
) -> Optional[Player]:
    """Updates player action tracking sets after a betting action.

    Args:
        agent: The player who just acted
        action_type: The type of action taken
        player_queue: PlayerQueue instance
        big_blind_player: The big blind player
        is_preflop: Whether the current round is preflop

    Returns:
        Optional[Player]: The new last raiser (if any)
    """
    last_raiser = None

    # Mark player's action and handle raise case
    is_raise = action_type == ActionType.RAISE
    player_queue.mark_player_acted(agent, is_raise=is_raise)

    if is_raise:
        last_raiser = agent
        # If someone raises, BB needs to act again in preflop
        if is_preflop and big_blind_player and agent != big_blind_player:
            player_queue.needs_to_act.add(big_blind_player)
    else:
        # Give BB option to raise on their first action in preflop
        if (
            is_preflop
            and big_blind_player
            and agent == big_blind_player
            and not last_raiser
        ):
            player_queue.needs_to_act.add(big_blind_player)

    return last_raiser


def _should_continue_betting(
    player_queue: PlayerQueue,
    last_raiser: Optional[Player],
) -> None:
    """Determines if betting should continue and updates who needs to act.

    This function implements the following betting round logic:
    1. If all active players have acted since the last raise:
       - If there was a raise, give the raiser one final option to raise again
       - If no raise, end the betting round
    2. Otherwise, continue the betting round with remaining players

    Args:
        player_queue: PlayerQueue instance
        last_raiser: The player who made the last raise, if any

    Side Effects:
        Updates needs_to_act set based on betting conditions:
        - Clears set if betting round should end
        - Adds last raiser if they get final option
        - Leaves set unchanged if betting should continue
    """
    # Get active non-folded players with chips
    active_non_folded = set(
        p for p in player_queue.active_players if not p.folded and p.chips > 0
    )
    all_acted = player_queue.acted_since_last_raise == active_non_folded

    # If everyone has acted since last raise, give last raiser final chance
    if all_acted and last_raiser and not last_raiser.folded and last_raiser.chips > 0:
        player_queue.needs_to_act.clear()
        player_queue.needs_to_act.add(last_raiser)
    elif all_acted:
        player_queue.needs_to_act.clear()  # No one else needs to act
