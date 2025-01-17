from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Union

from config import GameConfig
from data.states.round_state import RoundPhase
from data.types.action_response import ActionResponse, ActionType
from data.types.pot_types import SidePot
from loggers.betting_logger import BettingLogger

from .player import Player

if TYPE_CHECKING:
    from agents.agent import Agent
    from game.game import Game


def betting_round(
    game: "Game",
) -> Union[int, Tuple[int, List[SidePot]]]:
    """Manages a complete round of betting among active players.

    Args:
        game

    Returns:
        Either:
        - int: The new pot amount (if no side pots were created)
        - Tuple[int, List[SidePot]]: The new pot amount and list of side pots
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
    #! make this a separate function
    while not round_complete:

        for agent in active_players:
            should_skip, reason = _should_skip_player(agent, needs_to_act)
            if should_skip:
                continue

            # Get player action
            BettingLogger.log_active_player(agent.name)
            #! combine agent betting into a single method
            #! decides and acts
            action_decision = agent.decide_action(game)

            # Process the action
            agent.execute(action_decision, game)

            # Update action tracking
            last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
                agent,
                action_decision.action_type,
                active_players,
                needs_to_act,
                acted_since_last_raise,
            )

            # Check if betting round should continue
            _should_continue_betting(
                active_players, acted_since_last_raise, last_raiser, needs_to_act
            )

        # End round conditions
        if not needs_to_act:
            round_complete = True

        # Or if we only have one or zero players with chips left
        active_with_chips = [p for p in active_players if p.chips > 0]
        if len(active_with_chips) <= 1:
            round_complete = True

    # If any all-ins occurred, compute side pots
    if all_in_players:
        game.pot_manager.side_pots = game.pot_manager.calculate_side_pots(
            active_players
        )


def handle_betting_round(
    game: "Game",
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """Manages a complete betting round for all players and determines if the
    game should continue.

    Args:
        game: Game object

    Returns:
        Tuple containing:
        - int: New pot amount
        - Optional[List[SidePot]]: Any side pots created
        - bool: Whether the game should continue
    """
    if not game.players:
        raise ValueError("Cannot run betting round with no players")
    if game.pot_manager.pot < 0:
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


def validate_bet_to_call(
    current_bet: int, player_bet: int, is_big_blind: bool = False
) -> int:
    """Calculates the amount a player needs to add to call the current bet.

    Args:
        current_bet: The current bet amount that needs to be matched
        player_bet: The amount the player has already bet in this round
        is_big_blind: Whether the player is in the big blind position

    Returns:
        int: The additional amount the player needs to bet to call.
            Returns 0 for big blind when no raises have occurred.
    """
    bet_to_call = max(
        0, current_bet - player_bet
    )  # Works for both blinds and everyone else
    return bet_to_call


def _process_player_action(
    player: Player,
    action_decision: ActionResponse,
    current_bet: int,
    last_raiser: Optional[Player],
    active_players: List[Player],
    all_in_players: List[Player],
    game: "Game",
) -> Tuple[int, int, Optional[Player]]:
    """Processes a player's betting action and updates game state accordingly.

    Handles the mechanics of:
    - Processing folds, calls, and raises
    - Managing all-in situations
    - Updating pot and bet amounts
    - Enforcing betting limits
    - Logging actions and state changes

    Args:
        player: Player making the action
        action: The action ('fold', 'call', or 'raise')
        amount: Bet amount (total bet for raises)
        pot: Current pot amount
        current_bet: Current bet to match
        last_raiser: Last player who raised
        active_players: List of players still in hand
        all_in_players: List of players who are all-in
        game: Game object

    Returns:
        Tuple containing:
        - int: Updated pot amount
        - int: New current bet amount
        - Optional[Player]: New last raiser (if any)
    """
    new_last_raiser = None

    # Get max raise settings from game state
    max_raise_multiplier = game.config.max_raise_multiplier  #! why not used
    max_raises_per_round = game.config.max_raises_per_round  #! why not used
    raise_count = game.round_state.raise_count if game.round_state else 0

    # Calculate how much player needs to call, accounting for big blind position
    is_big_blind = player.is_big_blind if hasattr(player, "is_big_blind") else False
    to_call = validate_bet_to_call(current_bet, player.bet, is_big_blind)

    # Log initial state with active player context
    BettingLogger.log_player_turn(
        player_name=player.name,
        hand=player.hand.show() if hasattr(player, "hand") else "Unknown",
        to_call=to_call,
        chips=player.chips,
        current_bet=player.bet,
        pot=game.pot_manager.pot,
        active_players=[p.name for p in active_players if not p.folded],
        last_raiser=last_raiser.name if last_raiser else None,
    )

    if action_decision.action_type == ActionType.CHECK:
        BettingLogger.log_player_action(player.name, "check")
        return game.pot_manager.pot, current_bet, None

    elif action_decision.action_type == ActionType.FOLD:
        player.folded = True
        BettingLogger.log_player_action(player.name, "fold")

    elif action_decision.action_type == ActionType.CALL:
        # Player can only bet what they have
        bet_amount = min(to_call, player.chips)
        actual_bet = player.place_bet(bet_amount)

        # Add the bet to the pot
        game.pot_manager.pot += actual_bet

        # If they went all-in trying to call, count it as a raise
        if player.chips == 0 and bet_amount < to_call:
            new_last_raiser = player

        status = " (all in)" if player.chips == 0 else ""
        BettingLogger.log_player_action(
            player.name,
            "call",
            bet_amount,
            is_all_in=player.chips == 0,
            pot=game.pot_manager.pot,
        )

    elif action_decision.action_type == ActionType.RAISE:
        # Get current raise count and minimum bet
        raise_count = game.round_state.raise_count if game.round_state else 0
        min_bet = game.config.min_bet

        # Check if we've hit max raises
        if raise_count >= game.config.max_raises_per_round:
            BettingLogger.log_raise_limit(game.config.max_raises_per_round)
            return _process_call(player, current_bet, game.pot_manager.pot)

        # Calculate minimum raise amount (current bet + minimum raise increment)
        min_raise = current_bet + min_bet

        # Process valid raise
        if action_decision.raise_amount >= min_raise:
            # Calculate how much more they need to add
            to_add = action_decision.raise_amount - player.bet
            actual_bet = player.place_bet(to_add)
            game.pot_manager.pot += actual_bet

            # Update current bet and raise count
            if action_decision.raise_amount > current_bet:
                current_bet = action_decision.raise_amount
                new_last_raiser = player
                if game.round_state is not None:
                    game.round_state.raise_count += 1

            status = " (all in)" if player.chips == 0 else ""
            BettingLogger.log_player_action(
                player.name,
                "raise",
                action_decision.raise_amount,
                is_all_in=player.chips == 0,
            )
        else:
            # Invalid raise amount, convert to call
            BettingLogger.log_invalid_raise(action_decision.raise_amount, min_raise)
            return _process_call(player, current_bet, game.pot_manager.pot)

    # Update all-in status considering active players
    if player.chips == 0 and not player.folded:
        if player not in all_in_players:
            all_in_players.append(player)
            # Check if this creates a showdown situation
            active_with_chips = [
                p for p in active_players if not p.folded and p.chips > 0
            ]
            if len(active_with_chips) <= 1:
                BettingLogger.log_showdown()

    # Log updated state
    BettingLogger.log_state_after_action(
        player.name, game.pot_manager.pot, player.chips
    )

    # Update game state if provided, but DON'T increment raise count here
    if game.round_state:
        game.round_state.current_bet = current_bet
        if new_last_raiser:
            game.round_state.last_raiser = new_last_raiser.name
            # Remove this line to prevent double-counting raises
            # game_state.round_state.raise_count += 1

    return game.pot_manager.pot, current_bet, new_last_raiser


def calculate_side_pots(
    active_players: List[Player], all_in_players: List[Player]
) -> List[SidePot]:
    """Creates side pots when one or more players are all-in.

    Args:
        active_players: List of players still in the hand
        all_in_players: List of players who are all-in

    Returns:
        List[SidePot]: List of side pots, each containing:
            - amount: The amount in this pot
            - eligible_players: Players who can win this pot
    """
    # Sort all-in players by their total bet
    all_in_players.sort(key=lambda p: p.bet)

    # Get all active players who haven't folded
    active_non_folded = [p for p in active_players if not p.folded]

    side_pots = []
    previous_bet = 0

    # Process each bet level (including all-in amounts)
    # Include both all-in players and active players to get all bet levels
    bet_levels = sorted(set(p.bet for p in active_non_folded))

    for bet_level in bet_levels:
        if bet_level > previous_bet:
            # Find eligible players for this level
            # A player is eligible if they bet at least this amount
            eligible_players = [p.name for p in active_non_folded if p.bet >= bet_level]

            # Calculate pot amount for this level
            # Each eligible player contributes the difference between this level and previous level
            level_amount = (bet_level - previous_bet) * len(eligible_players)

            if level_amount > 0:
                side_pots.append(
                    SidePot(amount=level_amount, eligible_players=eligible_players)
                )

            previous_bet = bet_level

    if side_pots:
        BettingLogger.log_side_pots(side_pots)

    return side_pots


def collect_blinds_and_antes(players, dealer_index, small_blind, big_blind, ante, game):
    """Collects mandatory bets (blinds and antes) from players."""
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


def _process_call(
    player: Player, current_bet: int, pot: int, game: "Game"
) -> Tuple[int, int, Optional[Player]]:
    """Process a call action from a player.

    Args:
        player: Player making the call
        current_bet: Current bet amount to match
        pot: Current pot amount

    Returns:
        Tuple containing:
        - int: Updated pot amount
        - int: Current bet (unchanged)
        - Optional[Player]: Last raiser (None for calls)
    """
    # Calculate how much more they need to add to call
    to_call = current_bet - player.bet
    bet_amount = min(to_call, player.chips)

    # Place the bet
    actual_bet = player.place_bet(bet_amount, game)
    pot += actual_bet

    # Log the action
    BettingLogger.log_player_action(
        player.name, "call", bet_amount, is_all_in=player.chips == 0, pot=pot
    )

    return pot, current_bet, None

    # Reset flags after round
    if big_blind_player:
        big_blind_player.is_big_blind = False


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


def _get_current_bet(game: "Game") -> int:
    """Get the current bet amount, using game state or default value.

    Args:
        game: Game instance

    Returns:
        int: The current bet amount
    """
    current_bet = game.current_bet
    if current_bet <= 0:
        current_bet = game.min_bet if game else GameConfig.min_bet
    return current_bet


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
