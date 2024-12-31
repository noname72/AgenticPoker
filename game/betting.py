import logging
from typing import List, Optional, Tuple, Union

from .player import Player
from .types import SidePot


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[dict] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """
    Execute a betting round among active players.

    Args:
        players: The list of players in the hand.
        current_pot: The current size of the pot before this betting round.
        game_state: An optional dictionary of information about the current game state.

    Returns:
        Either an integer (the pot) if no side pots are created, or a tuple of (pot, list_of_side_pots).
    """

    # Filter out players who already folded
    active_players = [p for p in players if not p.folded]

    logging.debug(f"Starting betting round with pot: ${current_pot}")
    logging.debug(f"Active players: {[p.name for p in active_players]}")

    # If no one is active, there is nothing more to do
    if not active_players:
        return current_pot

    # Initialize betting-related variables
    all_in_players = []
    pot = current_pot
    current_bet = 0
    round_complete = False
    last_raiser = None
    last_raise_cycle = -1  # Track which cycle the last raise occurred
    current_cycle = 0      # Track current betting cycle

    # Reset bets this round
    for player in active_players:
        player.bet = 0

    # Use existing current_bet from game_state if available
    if game_state and "current_bet" in game_state:
        current_bet = game_state["current_bet"]

    # If there is no current bet, define a minimum bet (e.g., 10)
    if current_bet <= 0:
        current_bet = 10

    # Reset has_acted flag for all players at start of round
    for player in players:
        player.has_acted = False

    # Track who needs to act and who has acted since last raise
    needs_to_act = set(active_players)
    acted_since_last_raise = set()
    
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
            action, amount = _get_action_and_amount(player, current_bet, game_state)
            
            # Process the action
            pot, current_bet, new_last_raiser = _process_player_action(
                player,
                action,
                amount,
                pot,
                current_bet,
                last_raiser,
                active_players,
                all_in_players,
            )
            
            # Handle raise
            if action == "raise" and new_last_raiser:
                last_raiser = new_last_raiser
                # Reset acted_since_last_raise set
                acted_since_last_raise = {player}
                # Everyone except the raiser needs to act again
                needs_to_act = set(p for p in active_players if p != player and not p.folded)
            else:
                # Add player to acted set and remove from needs_to_act
                acted_since_last_raise.add(player)
                needs_to_act.discard(player)
                
            # Check if betting round should continue
            active_non_folded = set(p for p in active_players if not p.folded)
            all_acted = acted_since_last_raise == active_non_folded
            
            # If everyone has acted since last raise, give last raiser final chance
            if all_acted and last_raiser and not last_raiser.folded:
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
    others_have_acted = len(players_acted_this_cycle) == len([p for p in active_players if not p.folded and p != player])
    
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

    # Negative or nonsensical raise/call amounts get sanitized to 0 or the current bet
    if action == "raise" and amount < current_bet:
        # If the raise isn't large enough, turn it into a call
        action, amount = "call", current_bet
    amount = max(amount, 0)

    return action, amount


def _process_player_action(
    player: Player,
    action: str,
    amount: int,
    pot: int,
    current_bet: int,
    last_raiser: Optional[Player],
    active_players: List[Player],
    all_in_players: List[Player],
) -> Tuple[int, int, Optional[Player]]:
    """
    Handle the player's action (fold, call, raise).
    Returns (pot, current_bet, new_last_raiser)
    """
    new_last_raiser = None

    if action == "fold":
        player.folded = True
    
    elif action in ("call", "raise"):
        to_call = max(current_bet - player.bet, 0)
        
        if action == "call":
            bet_amount = min(to_call, player.chips)
        else:  # raise
            bet_amount = min(amount, player.chips)
            if bet_amount > current_bet:
                current_bet = bet_amount
                new_last_raiser = player
            else:
                bet_amount = min(to_call, player.chips)
        
        actual_bet = player.place_bet(bet_amount)
        pot += actual_bet
        
        if player.chips == 0:
            all_in_players.append(player)
    
    # Remove folded players from active list
    active_players[:] = [p for p in active_players if not p.folded]
    
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

    side_pots = []
    previous_bet = 0

    # Calculate main pot first (everyone can win this)
    min_bet = min(p.bet for p in active_players)
    if min_bet > 0:
        eligible = active_players[:]  # Everyone in active_players is eligible
        side_pots.append(SidePot(min_bet * len(eligible), eligible))
        previous_bet = min_bet

    # Now handle each all-in player's contribution above the previous pot
    for all_in_player in all_in_players:
        bet_difference = all_in_player.bet - previous_bet
        if bet_difference > 0:
            # Find who is eligible for this pot
            eligible = [p for p in active_players if p.bet >= all_in_player.bet]
            pot_amount = bet_difference * len(eligible)
            if pot_amount > 0:
                side_pots.append(SidePot(pot_amount, eligible))
        previous_bet = all_in_player.bet

    # Finally, if any players bet more than the highest all-in,
    # create one last side pot for that excess.
    remaining_players = [p for p in active_players if p.chips > 0]
    if remaining_players:
        max_bet = max(p.bet for p in remaining_players)
        if max_bet > previous_bet:
            pot_amount = (max_bet - previous_bet) * len(remaining_players)
            side_pots.append(SidePot(pot_amount, remaining_players))

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
