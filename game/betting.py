"""
Betting module for poker game implementation.

This module handles all betting-related functionality including:
- Managing betting rounds
- Processing player actions (fold, call, raise)
- Handling all-in situations and side pots
- Collecting blinds and antes
- Validating bets and raises

The module provides functions to manage the complete betting workflow in a poker game,
with support for:
- Multiple betting rounds
- Side pot calculations
- Blind and ante collection
- Bet validation and limits
- Minimum raise enforcement
- Last raiser restrictions
- Detailed logging of all betting actions
- Showdown situation detection

Key features:
- Enforces minimum raise amounts (double the last raise)
- Prevents players from raising twice consecutively unless they're the last active player
- Tracks and validates betting sequences
- Handles partial calls and all-in situations
- Creates side pots automatically when needed
- Provides detailed logging of betting actions and game state
- Supports customizable betting limits and raise restrictions
"""

import logging
from typing import List, Optional, Tuple, Union

from .player import Player
from .types import SidePot


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[dict] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """Manages a complete round of betting among active players.

    Handles the full betting sequence including:
    - Processing each player's actions (fold/call/raise)
    - Tracking betting order and amounts
    - Managing all-in situations
    - Creating side pots when necessary
    - Enforcing betting rules and limits

    Args:
        players: List of active players in the game
        current_pot: The current amount in the pot
        game_state: Optional dictionary containing game state information like:
            - current_bet: Current bet amount
            - max_raise_multiplier: Maximum raise multiplier (default 3)
            - max_raises_per_round: Maximum raises allowed per round (default 4)
            - raise_count: Current number of raises in this round

    Returns:
        Either:
        - int: The new pot amount (if no side pots were created)
        - Tuple[int, List[SidePot]]: The new pot amount and list of side pots
    """
    pot = current_pot
    active_players = [p for p in players if not p.folded]
    all_in_players: List[Player] = []
    round_complete = False
    last_raiser = None

    # Create a copy of game state at the start
    current_game_state = {} if game_state is None else game_state.copy()

    # Get current bet from game state if provided
    current_bet = current_game_state.get("current_bet", 0)

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


def _get_action_and_amount(
    player: Player, current_bet: int, game_state: Optional[dict]
) -> Tuple[str, int]:
    """Retrieves and validates a player's betting action and amount.

    Gets the player's decision through their decide_action method if available,
    otherwise defaults to calling. Validates and normalizes the action and amount
    to ensure they're legal.

    Args:
        player: The player making the decision
        current_bet: Current bet amount to match
        game_state: Optional game state information for decision making

    Returns:
        Tuple containing:
        - str: The action ('fold', 'call', or 'raise')
        - int: The bet amount (total bet for raises, amount to call for calls)
    """
    try:
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
    except Exception as e:
        logging.error(f"Error getting action from {player.name}: {e}")
        # Default to calling in case of error
        return "call", current_bet


def validate_bet_to_call(current_bet: int, player_bet: int) -> int:
    """Calculates the amount a player needs to add to call the current bet.

    Args:
        current_bet: The current bet amount that needs to be matched
        player_bet: The amount the player has already bet in this round

    Returns:
        int: The additional amount the player needs to bet to call.
            Always returns non-negative value.
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
        game_state: Optional game state information

    Returns:
        Tuple containing:
        - int: Updated pot amount
        - int: New current bet amount
        - Optional[Player]: New last raiser (if any)
    """
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

    # Add validation for minimum raise amount based on last raiser's bet
    min_raise_amount = 0
    if last_raiser and last_raiser in active_players:
        min_raise_amount = last_raiser.bet * 2  # Double the last raise

    # Log initial state with active player context
    logging.info(f"\n{player.name}'s turn:")
    logging.info(
        f"  Active players: {[p.name for p in active_players if not p.folded]}"
    )
    logging.info(f"  Last raiser: {last_raiser.name if last_raiser else 'None'}")
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
        # Validate raise against minimum raise amount
        if amount < min_raise_amount:
            action = "call"
            amount = current_bet
            logging.info(
                f"Raise amount ${amount} below minimum (${min_raise_amount}), converting to call"
            )
        else:
            # Check if this player is allowed to raise based on position and active players
            can_raise = True
            if last_raiser:
                # Prevent same player from raising twice in a row unless they're the only active player
                active_non_folded = [
                    p for p in active_players if not p.folded and p.chips > 0
                ]
                if player == last_raiser and len(active_non_folded) > 1:
                    can_raise = False
                    logging.info(f"{player.name} cannot raise twice in a row")

            if not can_raise:
                action = "call"
                amount = current_bet

        # For raises, amount represents the total bet they want to make
        total_wanted_bet = amount

        # Calculate the actual amount they can bet
        max_raise = current_bet * max_raise_multiplier
        max_possible_bet = min(player.chips + player.bet, max_raise)
        actual_total_bet = min(total_wanted_bet, max_possible_bet)

        # If we've already hit the max raises, treat as a call
        if raise_count >= max_raises_per_round:
            bet_amount = min(to_call, player.chips)
            actual_bet = player.place_bet(bet_amount)
            pot += actual_bet
            logging.info(f"{player.name} calls ${bet_amount} (max raises reached)")
        else:
            # Valid raise or all-in
            to_add = min(actual_total_bet - player.bet, player.chips)
            actual_bet = player.place_bet(to_add)
            pot += actual_bet

            # For raises, update current bet if it's higher
            if actual_total_bet > current_bet:
                current_bet = actual_total_bet
                new_last_raiser = player
                # Increment raise count in the game state
                if game_state is not None:
                    game_state["raise_count"] = raise_count + 1
            elif player.chips == 0:
                # All-in below current bet still counts as a raise
                new_last_raiser = player
                if game_state is not None:
                    game_state["raise_count"] = raise_count + 1

            status = " (all in)" if player.chips == 0 else ""
            if actual_total_bet < total_wanted_bet:
                logging.info(
                    f"{player.name} raises to ${actual_total_bet}{status} (capped at {max_raise_multiplier}x)"
                )
            else:
                logging.info(f"{player.name} raises to ${actual_total_bet}{status}")

    # Update all-in status considering active players
    if player.chips == 0 and not player.folded:
        if player not in all_in_players:
            all_in_players.append(player)
            # Check if this creates a showdown situation
            active_with_chips = [
                p for p in active_players if not p.folded and p.chips > 0
            ]
            if len(active_with_chips) <= 1:
                logging.info("Showdown situation: Only one player with chips remaining")

    # Log updated state
    logging.info(f"  Pot after action: ${pot}")
    logging.info(f"  {player.name}'s remaining chips: ${player.chips}")

    return pot, current_bet, new_last_raiser


def calculate_side_pots(
    active_players: List[Player], all_in_players: List[Player]
) -> List[SidePot]:
    """Creates side pots when one or more players are all-in.

    Calculates multiple pots based on different all-in amounts:
    1. Sorts all-in players by their total bet
    2. Creates separate pots for each distinct all-in amount
    3. Determines eligible players for each pot
    4. Calculates the amount in each pot

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


def collect_blinds_and_antes(players, dealer_index, small_blind, big_blind, ante):
    """Collects mandatory bets (blinds and antes) from players.

    Processes the collection of:
    1. Antes from all players (if any)
    2. Small blind from player after dealer
    3. Big blind from player after small blind

    Handles partial payments when players don't have enough chips
    and tracks all-in situations.

    Args:
        players: List of players in the game
        dealer_index: Position of dealer button
        small_blind: Small blind amount
        big_blind: Big blind amount
        ante: Ante amount (0 for no ante)

    Returns:
        int: Total amount collected from all players
    """
    collected = 0
    num_players = len(players)

    # Collect antes first
    if ante > 0:
        logging.info("\nCollecting antes...")
        for player in players:
            ante_amount = min(ante, player.chips)
            actual_bet = player.place_bet(ante_amount)
            collected += actual_bet

            status = " (all in)" if player.chips == 0 else ""
            if actual_bet < ante:
                logging.info(
                    f"{player.name} posts partial ante of ${actual_bet}{status}"
                )
            else:
                logging.info(f"{player.name} posts ante of ${actual_bet}{status}")

    # Collect blinds
    sb_index = (dealer_index + 1) % num_players
    bb_index = (dealer_index + 2) % num_players

    # Small blind
    sb_player = players[sb_index]
    sb_amount = min(small_blind, sb_player.chips)
    actual_sb = sb_player.place_bet(sb_amount)
    collected += actual_sb

    status = " (all in)" if sb_player.chips == 0 else ""
    if actual_sb < small_blind:
        logging.info(
            f"{sb_player.name} posts partial small blind of ${actual_sb}{status}"
        )
    else:
        logging.info(f"{sb_player.name} posts small blind of ${actual_sb}{status}")

    # Big blind
    bb_player = players[bb_index]
    bb_amount = min(big_blind, bb_player.chips)
    actual_bb = bb_player.place_bet(bb_amount)
    collected += actual_bb

    status = " (all in)" if bb_player.chips == 0 else ""
    if actual_bb < big_blind:
        logging.info(
            f"{bb_player.name} posts partial big blind of ${actual_bb}{status}"
        )
    else:
        logging.info(f"{bb_player.name} posts big blind of ${actual_bb}{status}")

    return collected


def handle_betting_round(
    players: List[Player],
    pot: int,
    game_state: Optional[dict],
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """Manages a complete betting round and determines if the game should continue.

    Coordinates the entire betting process including:
    - Running the betting round
    - Managing side pots
    - Determining if the game should continue

    Args:
        players: List of active players
        pot: Current pot amount
        game_state: Optional game state information

    Returns:
        Tuple containing:
        - int: New pot amount
        - Optional[List[SidePot]]: Any side pots created
        - bool: Whether the game should continue (False if only one player remains)
    """
    if not players:
        raise ValueError("Cannot run betting round with no players")
    if pot < 0:
        raise ValueError("Pot amount cannot be negative")
    if any(not isinstance(p, Player) for p in players):
        raise TypeError("All elements in players list must be Player instances")

    active_players = [p for p in players if not p.folded]

    # Run betting round
    result = betting_round(active_players, pot, game_state)

    # Handle return value based on whether side pots were created
    if isinstance(result, tuple):
        new_pot, side_pots = result
    else:
        new_pot = result
        side_pots = None

    # Determine if game should continue
    active_count = sum(1 for p in players if not p.folded)
    should_continue = active_count > 1

    return new_pot, side_pots, should_continue
