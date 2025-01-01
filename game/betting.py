import logging
from typing import List, Optional, Tuple, Union

from .player import Player
from .types import SidePot


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[dict] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """
    Run a betting round and return the final pot size.

    Args:
        players: List of players in the hand
        current_pot: Current pot size
        game_state: Optional game state for AI decisions

    Returns:
        Union[int, Tuple[int, List[SidePot]]]: Final pot size and side pots if any
    """
    pot = current_pot
    active_players = [p for p in players if not p.folded]
    all_in_players: List[Player] = []
    round_complete = False
    last_raiser = None

    # Get current bet from game state if provided
    current_bet = game_state.get("current_bet", 0) if game_state else 0

    # If there is no current bet, define a minimum bet (e.g., 10)
    if current_bet <= 0:
        current_bet = 10

    # Reset has_acted flag for all players at start of round
    for player in players:
        player.has_acted = False
        player.bet = 0  # Reset bets at start of round

    # Track who needs to act and who has acted since last raise
    needs_to_act = set(active_players)
    acted_since_last_raise = set()

    # Track the highest bet seen in this round
    highest_bet = current_bet

    # Main betting loop
    while not round_complete:
        round_complete = True

        for player in active_players:
            # Skip if player can't act
            if player.folded or player.chips == 0:
                continue

            # Skip if player doesn't need to act
            if player not in needs_to_act:
                continue

            round_complete = False

            # Get and process player action
            action, amount = _get_action_and_amount(player, highest_bet, game_state)

            # For raises, amount is the total bet they want to make
            if action == "raise":
                # Ensure amount includes their current bet
                amount = max(amount, highest_bet)

                # If they can't match the current bet and have enough chips to call,
                # convert to call. But if they're going all-in, let them do it.
                if amount <= highest_bet and player.chips > (highest_bet - player.bet):
                    action = "call"
                    amount = highest_bet
            elif action == "call":
                # For calls, always try to match the highest bet
                amount = highest_bet

            # Process the action
            pot, new_current_bet, new_last_raiser = _process_player_action(
                player,
                action,
                amount,
                pot,
                highest_bet,
                last_raiser,
                active_players,
                all_in_players,
                game_state,
            )

            # Update highest bet seen
            if new_current_bet > highest_bet:
                highest_bet = new_current_bet

            # Update last raiser
            if new_last_raiser:
                last_raiser = new_last_raiser
                # Reset acted_since_last_raise set
                acted_since_last_raise = {player}
                # Everyone except the raiser needs to act again
                needs_to_act = set(
                    p
                    for p in active_players
                    if p != player and not p.folded and p.chips > 0
                )
            else:
                # Add player to acted set and remove from needs_to_act
                acted_since_last_raise.add(player)
                needs_to_act.discard(player)

            # Check if betting round should continue
            active_non_folded = set(
                p for p in active_players if not p.folded and p.chips > 0
            )
            all_acted = acted_since_last_raise == active_non_folded

            # If everyone has acted since last raise, give last raiser final chance
            if (
                all_acted
                and last_raiser
                and not last_raiser.folded
                and last_raiser.chips > 0
            ):
                needs_to_act = {last_raiser}
                last_raiser = None  # Reset to prevent infinite loop
            elif all_acted:
                needs_to_act.clear()  # No one else needs to act

        # End round conditions
        if not needs_to_act:
            round_complete = True

        # Or if we only have one or zero players with chips left
        active_with_chips = [p for p in active_players if p.chips > 0]
        if len(active_with_chips) <= 1:
            round_complete = True

    # If any all-ins occurred, compute side pots
    if all_in_players:
        side_pots = calculate_side_pots(active_players, all_in_players)
        return pot, side_pots

    return pot


def _player_needs_to_act(
    player: Player,
    last_raiser: Optional[Player],
    current_bet: int,
    players_acted_this_cycle: set,
    current_cycle: int,
    last_raise_cycle: int,
    active_players: List[Player],
) -> bool:
    """
    Determine if `player` still needs to act.
    """
    # Skip players with zero chips - they can't act
    if player.chips == 0:
        return False

    # A player needs to act if:
    # 1. Their bet is less than the current bet (they need to call or fold)
    # 2. They haven't acted in this cycle yet
    needs_to_call = player.bet < current_bet
    hasnt_acted = player not in players_acted_this_cycle

    # The last raiser gets another chance after everyone else has acted
    is_last_raiser = player == last_raiser
    others_have_acted = len(players_acted_this_cycle) == len(
        [p for p in active_players if not p.folded and p != player]
    )

    # Player needs to act if:
    # - They need to call
    # - Haven't acted yet
    # - OR they're the last raiser and everyone else has acted
    return needs_to_call or hasnt_acted or (is_last_raiser and others_have_acted)


def _get_action_and_amount(
    player: Player, current_bet: int, game_state: Optional[dict]
) -> Tuple[str, int]:
    """
    Retrieve the player's decision.
    Defaults to "call" the current bet if no decision function is provided.
    """
    if hasattr(player, "decide_action"):
        decision = player.decide_action(game_state)
        # If the player returns just 'fold'/'call'/'raise', default the amount
        if isinstance(decision, tuple):
            action, amount = decision
        else:
            action, amount = decision, current_bet
    else:
        # Fallback to calling if no custom logic is provided
        action, amount = "call", current_bet

    # If action is invalid, default to "call" for safety
    if action not in ("fold", "call", "raise"):
        action, amount = "call", current_bet

    # For raises, amount represents the total bet they want to make
    if action == "raise":
        # If they try to raise less than the current bet, convert to call
        if amount <= current_bet:
            action = "call"
            amount = current_bet

    # Ensure non-negative amounts
    amount = max(0, amount)

    return action, amount


def validate_bet_to_call(current_bet: int, player_bet: int) -> int:
    """
    Ensure bet to call amount is correct.

    Args:
        current_bet: Current bet amount on the table
        player_bet: Player's current bet amount

    Returns:
        int: Amount player needs to call
    """
    bet_to_call = max(0, current_bet - player_bet)  # Can't be negative
    return bet_to_call


def _process_player_action(
    player: Player,
    action: str,
    amount: int,
    pot: int,
    current_bet: int,
    last_raiser: Optional[Player],
    active_players: List[Player],
    all_in_players: List[Player],
    game_state: Optional[dict] = None,
) -> Tuple[int, int, Optional[Player]]:
    """Handle the player's action (fold, call, raise)."""
    new_last_raiser = None

    # Get max raise settings from game state
    max_raise_multiplier = (
        game_state.get("max_raise_multiplier", 3) if game_state else 3
    )
    max_raises_per_round = (
        game_state.get("max_raises_per_round", 4) if game_state else 4
    )
    raise_count = game_state.get("raise_count", 0) if game_state else 0

    # Calculate how much player needs to call
    to_call = validate_bet_to_call(current_bet, player.bet)

    # Log initial state
    logging.info(f"\n{player.name}'s turn:")
    logging.info(
        f"  Hand: {player.hand.show() if hasattr(player, 'hand') else 'Unknown'}"
    )
    logging.info(f"  Current bet to call: ${to_call}")
    logging.info(f"  Player chips: ${player.chips}")
    logging.info(f"  Player current bet: ${player.bet}")
    logging.info(f"  Current pot: ${pot}")

    if action == "fold":
        player.folded = True
        logging.info(f"{player.name} folds")

    elif action == "call":
        # Player can only bet what they have
        bet_amount = min(to_call, player.chips)
        actual_bet = player.place_bet(bet_amount)
        pot += actual_bet

        # If they went all-in trying to call, count it as a raise
        if player.chips == 0 and bet_amount < to_call:
            new_last_raiser = player

        status = " (all in)" if player.chips == 0 else ""
        logging.info(f"{player.name} calls ${bet_amount}{status}")

    elif action == "raise":
        # For raises, amount represents the total bet they want to make
        total_wanted_bet = amount

        # Calculate the actual amount they can bet
        max_raise = current_bet * max_raise_multiplier
        max_possible_bet = min(player.chips + player.bet, max_raise)
        actual_total_bet = min(total_wanted_bet, max_possible_bet)

        # If it's not a valid raise amount or we've hit max raises, convert to call
        # But if they're going all-in, let them do it
        if (
            actual_total_bet <= current_bet and player.chips > to_call
        ) or raise_count >= max_raises_per_round:
            # Player can only bet what they have
            bet_amount = min(to_call, player.chips)
            actual_bet = player.place_bet(bet_amount)
            pot += actual_bet

            # If they went all-in trying to call, count it as a raise
            if player.chips == 0 and bet_amount < to_call:
                new_last_raiser = player

            if raise_count >= max_raises_per_round:
                logging.info(f"{player.name} calls ${bet_amount} (max raises reached)")
            else:
                logging.info(
                    f"{player.name} calls ${bet_amount} (invalid raise converted to call)"
                )
        else:
            # Valid raise or all-in
            to_add = min(actual_total_bet - player.bet, player.chips)
            actual_bet = player.place_bet(to_add)
            pot += actual_bet

            # For raises, update current bet if it's higher
            if actual_total_bet > current_bet:
                current_bet = actual_total_bet
                new_last_raiser = player
            elif player.chips == 0:
                # All-in below current bet still counts as a raise
                new_last_raiser = player

            status = " (all in)" if player.chips == 0 else ""
            if actual_total_bet < total_wanted_bet:
                logging.info(
                    f"{player.name} raises to ${actual_total_bet}{status} (capped at {max_raise_multiplier}x)"
                )
            else:
                logging.info(f"{player.name} raises to ${actual_total_bet}{status}")

    # Check for all-in
    if player.chips == 0 and not player.folded:
        if player not in all_in_players:
            all_in_players.append(player)
            logging.info(f"{player.name} is all in!")

    # Log updated state
    logging.info(f"  Pot after action: ${pot}")
    logging.info(f"  {player.name}'s remaining chips: ${player.chips}")

    return pot, current_bet, new_last_raiser


def _no_more_betting_needed(
    active_players: List[Player],
    current_bet: int,
) -> bool:
    """
    Check if all active (non-folded) players have matched the current bet.
    """
    # If every non-folded player's bet is the same, no more betting.
    return all(p.bet == current_bet for p in active_players if not p.folded)


def calculate_side_pots(
    active_players: List[Player], all_in_players: List[Player]
) -> List[SidePot]:
    """
    Calculate side pots when one or more players is all-in.

    The logic is:
    1. Sort all-in players by their total bet.
    2. Create a pot for each distinct all-in level.
    3. Calculate which players are eligible for each pot.
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
            eligible_players = [p for p in active_non_folded if p.bet >= bet_level]

            # Calculate pot amount for this level
            # Each eligible player contributes the difference between this level and previous level
            level_amount = (bet_level - previous_bet) * len(eligible_players)

            if level_amount > 0:
                side_pots.append(SidePot(level_amount, eligible_players))

            previous_bet = bet_level

    if side_pots:
        logging.debug("Side pots created:")
        for i, pot in enumerate(side_pots, start=1):
            logging.debug(
                f"  Pot {i}: ${pot.amount} - Eligible: {[p.name for p in pot.eligible_players]}"
            )

    return side_pots


def log_action(
    player: Player, action: str, amount: int = 0, current_bet: int = 0, pot: int = 0
) -> None:
    """
    Log player actions with optional all-in indicators.
    """
    action_str = (
        f"{player.name}'s turn:\n"
        f"  Current bet to call: ${current_bet}\n"
        f"  Player chips: ${player.chips}\n"
        f"  Player current bet: ${player.bet}\n"
        f"  Current pot: ${pot}"
    )

    if action == "fold":
        action_str += f"\n{player.name} folds"
    elif action == "call":
        all_in = amount >= player.chips
        status = " (all in)" if all_in else ""
        action_str += f"\n{player.name} calls ${amount}{status}"
    elif action == "raise":
        all_in = amount >= player.chips
        status = " (all in)" if all_in else ""
        action_str += f"\n{player.name} raises to ${amount}{status}"

    logging.info(action_str)


def collect_blinds_and_antes(
    players: List[Player],
    dealer_index: int,
    small_blind: int = 10,
    big_blind: int = 20,
    ante: int = 0,
) -> int:
    """
    Collect mandatory bets (blinds and antes) at the start of each hand.

    Args:
        players: List of active players
        dealer_index: Position of the dealer button
        small_blind: Small blind amount (default: 10)
        big_blind: Big blind amount (default: 20)
        ante: Ante amount (default: 0)

    Returns:
        int: Total amount collected
    """
    total_collected = 0

    # Collect antes
    for player in players:
        ante_amount = min(ante, player.chips)
        if ante_amount > 0:
            actual_ante = player.place_bet(ante_amount)
            total_collected += actual_ante
            if actual_ante < ante:
                logging.info(
                    f"{player.name} posts partial ante of ${actual_ante} (all in)"
                )
            else:
                logging.info(f"{player.name} posts ante of ${actual_ante}")

    # Collect blinds
    sb_pos = (dealer_index + 1) % len(players)
    bb_pos = (dealer_index + 2) % len(players)

    # Small blind
    sb_amount = min(small_blind, players[sb_pos].chips)
    actual_sb = players[sb_pos].place_bet(sb_amount)
    total_collected += actual_sb
    _log_blind_post("small", players[sb_pos], actual_sb, small_blind)

    # Big blind
    bb_amount = min(big_blind, players[bb_pos].chips)
    actual_bb = players[bb_pos].place_bet(bb_amount)
    total_collected += actual_bb
    _log_blind_post("big", players[bb_pos], actual_bb, big_blind)

    return total_collected


def _log_blind_post(
    blind_type: str, player: Player, amount: int, expected_amount: int
) -> None:
    """Helper to log blind postings consistently."""
    status = " (all in)" if player.chips == 0 else ""
    if amount < expected_amount:
        logging.info(
            f"{player.name} posts partial {blind_type} blind of ${amount}{status}"
        )
    else:
        logging.info(f"{player.name} posts {blind_type} blind of ${amount}{status}")


def handle_betting_round(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: dict,
    phase: str = "pre-draw",
) -> Tuple[int, Optional[List[SidePot]]]:
    """
    Handle a complete betting round.

    Args:
        players: List of active players
        pot: Current pot amount
        dealer_index: Position of dealer button
        game_state: Current game state
        phase: Betting phase ('pre-draw' or 'post-draw')

    Returns:
        Tuple[int, Optional[List[SidePot]]]: New pot amount and side pots if any
    """
    logging.info(f"\n--- {phase.title()} Betting ---")

    result = betting_round(players, pot, game_state)

    if isinstance(result, tuple):
        new_pot, side_pots = result
    else:
        new_pot, side_pots = result, None

    return new_pot, side_pots
