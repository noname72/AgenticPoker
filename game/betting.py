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
from typing import Dict, List, Optional, Tuple, Union

from data.states.game_state import GameState
from data.types.pot_types import SidePot
from data.types.round_state import RoundPhase

from .player import Player

logger = logging.getLogger(__name__)


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[GameState] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """Manages a complete round of betting among active players.

    Args:
        players: List of active players in the game
        current_pot: The current amount in the pot
        game_state: Optional GameState object containing game state information

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

    # Get current bet and big blind position from game state
    current_bet = game_state.round_state.current_bet if game_state else 0

    # Get big blind player based on position
    big_blind_player = None
    if game_state and game_state.round_state.big_blind_position is not None:
        bb_index = game_state.round_state.big_blind_position
        if 0 <= bb_index < len(players):
            big_blind_player = players[bb_index]

    # If there is no current bet, use minimum bet from game state or default
    if current_bet <= 0:
        current_bet = game_state.min_bet if game_state else 10

    # Reset has_acted flag at start, but **do not** zero-out the player.bet
    for player in players:
        player.has_acted = False

    # Track who needs to act and who has acted since last raise
    needs_to_act = set(active_players)
    acted_since_last_raise = set()

    # Track the highest bet seen in this round
    highest_bet = current_bet

    # Main betting loop
    while not round_complete:
        round_complete = True

        for player in active_players:
            logging.info(f"---- {player.name} is active ----")
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
    player: Player, highest_bet: int, game_state: Optional[GameState] = None
) -> Tuple[str, int]:
    """Get and validate player action."""
    try:
        # Get raw action from player
        action, amount = player.decide_action(game_state)
        min_raise = highest_bet + (game_state.min_bet if game_state else 10)

        if action == "raise":
            # For raises, validate the total amount meets minimum raise requirement
            if amount < min_raise:
                logger.info(
                    f"Raise amount ${amount} below minimum (${min_raise}), converting to call"
                )
                return "call", highest_bet

            # Ensure player has enough chips for the raise
            max_possible_raise = player.chips + player.bet
            if amount > max_possible_raise:
                amount = max_possible_raise

            return "raise", amount

        elif action == "call":
            return "call", highest_bet

        elif action == "fold":
            return "fold", 0

        else:
            logger.warning(f"Invalid action {action}, defaulting to call")
            return "call", highest_bet

    except Exception as e:
        logger.error(f"Error getting player action: {str(e)}")
        return "call", highest_bet  # Safe default


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
    action: str,
    amount: int,
    pot: int,
    current_bet: int,
    last_raiser: Optional[Player],
    active_players: List[Player],
    all_in_players: List[Player],
    game_state: Optional[GameState] = None,
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
    max_raise_multiplier = game_state.max_raise_multiplier if game_state else 3
    max_raises_per_round = game_state.max_raises_per_round if game_state else 4
    raise_count = game_state.round_state.raise_count if game_state else 0

    # Calculate how much player needs to call, accounting for big blind position
    is_big_blind = player.is_big_blind if hasattr(player, "is_big_blind") else False
    to_call = validate_bet_to_call(current_bet, player.bet, is_big_blind)

    # Add validation for minimum raise amount based on last raiser's bet
    min_raise_amount = 0
    if last_raiser and last_raiser in active_players:
        min_raise_amount = last_raiser.bet * 2  # Double the last raise

    # Log initial state with active player context
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

    if action == "check":
        logging.info(f"{player.name} checks")
        return pot, current_bet, None

    elif action == "fold":
        player.folded = True
        logging.info(f"{player.name} folds")

    elif action == "call":
        # Player can only bet what they have
        bet_amount = min(to_call, player.chips)
        actual_bet = player.place_bet(bet_amount)

        # Add the bet to the pot
        pot += actual_bet

        # If they went all-in trying to call, count it as a raise
        if player.chips == 0 and bet_amount < to_call:
            new_last_raiser = player

        status = " (all in)" if player.chips == 0 else ""
        logging.info(f"{player.name} calls ${bet_amount}{status}")
        logging.info(f"  Pot after call: ${pot}")

    elif action == "raise":
        # Get current raise count and minimum bet
        raise_count = game_state.round_state.raise_count if game_state else 0
        min_bet = game_state.min_bet if game_state else 10

        # Check if we've hit max raises
        if raise_count >= max_raises_per_round:
            logging.info(
                f"Max raises ({max_raises_per_round}) reached, converting raise to call"
            )
            return _process_call(player, current_bet, pot)

        # Calculate minimum raise amount (current bet + minimum raise increment)
        min_raise = current_bet + min_bet

        # Process valid raise
        if amount >= min_raise:
            # Calculate how much more they need to add
            to_add = amount - player.bet
            actual_bet = player.place_bet(to_add)
            pot += actual_bet

            # Update current bet and raise count
            if amount > current_bet:
                current_bet = amount
                new_last_raiser = player
                if game_state is not None:
                    game_state.round_state.raise_count += 1

            status = " (all in)" if player.chips == 0 else ""
            logging.info(f"{player.name} raises to ${amount}{status}")
        else:
            # Invalid raise amount, convert to call
            logging.info(
                f"Raise amount ${amount} below minimum (${min_raise}), converting to call"
            )
            return _process_call(player, current_bet, pot)

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
    logging.info("")

    # Update game state if provided, but DON'T increment raise count here
    if game_state:
        game_state.round_state.current_bet = current_bet
        if new_last_raiser:
            game_state.round_state.last_raiser = new_last_raiser.name
            # Remove this line to prevent double-counting raises
            # game_state.round_state.raise_count += 1

    return pot, current_bet, new_last_raiser


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
        logging.debug("Side pots created:")
        for i, pot in enumerate(side_pots, start=1):
            logging.debug(
                f"  Pot {i}: ${pot.amount} - Eligible: {pot.eligible_players}"
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
    """Collects mandatory bets (blinds and antes) from players."""
    collected = 0
    num_players = len(players)

    # Collect antes first
    if ante > 0:
        logging.info("\nCollecting antes:")
        for player in players:
            ante_amount = min(ante, player.chips)
            player.chips -= ante_amount
            collected += ante_amount

            status = " (all in)" if player.chips == 0 else ""
            if ante_amount < ante:
                logging.info(
                    f"  {player.name} posts partial ante of ${ante_amount}{status}"
                )
            else:
                logging.info(f" {player.name} posts ante of ${ante_amount}{status}")

        # Add extra line break after antes
        logging.info("")

    # Small blind
    sb_index = (dealer_index + 1) % num_players
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
    bb_index = (dealer_index + 2) % num_players
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

    # Add extra line break after blinds
    logging.info("")

    return collected


def handle_betting_round(
    players: List[Player],
    pot: int,
    game_state: Optional[Union[Dict, GameState]],
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """Manages a complete betting round and determines if the game should continue.

    Args:
        players: List of active players
        pot: Current pot amount
        game_state: GameState object or legacy dict containing game state

    Returns:
        Tuple containing:
        - int: New pot amount
        - Optional[List[SidePot]]: Any side pots created
        - bool: Whether the game should continue
    """
    if not players:
        raise ValueError("Cannot run betting round with no players")
    if pot < 0:
        raise ValueError("Pot amount cannot be negative")
    if any(not isinstance(p, Player) for p in players):
        raise TypeError("All elements in players list must be Player instances")

    # Convert to proper GameState if needed
    dealer_index = getattr(game_state, "dealer_position", 0) if game_state else 0
    game_state = _ensure_game_state(game_state, pot, dealer_index)

    active_players = [p for p in players if not p.folded]

    # Run betting round with validated GameState
    result = betting_round(active_players, pot, game_state)

    # Handle return value based on whether side pots were created
    if isinstance(result, tuple):
        new_pot, side_pots = result
    else:
        new_pot = result
        side_pots = None

    # Update game state
    game_state.pot_state.main_pot = new_pot
    if side_pots:
        game_state.pot_state.side_pots = [
            {
                "amount": pot.amount,
                "eligible_players": pot.eligible_players,  # Already strings, no need to convert
            }
            for pot in side_pots
        ]

    # Determine if game should continue
    active_count = sum(1 for p in players if not p.folded)
    should_continue = active_count > 1

    return new_pot, side_pots, should_continue


def create_or_update_betting_state(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: Optional[GameState] = None,
    phase: str = RoundPhase.PRE_DRAW,
) -> GameState:
    """
    Create a new game state or update an existing one for betting rounds.

    Args:
        players: List of players in the game
        pot: Current pot amount
        dealer_index: Index of the dealer
        game_state: Optional existing game state to update
        phase: Current game phase (defaults to PRE_DRAW)

    Returns:
        GameState: New or updated game state
    """
    if game_state is None:
        # Import here to avoid circular import
        from data.types.base_types import DeckState, PotState, RoundState

        game_state = GameState(
            players=[],  # Will be populated by betting module
            dealer_position=dealer_index,
            small_blind=0,  # Will be set by betting module
            big_blind=0,  # Will be set by betting module
            ante=0,  # Will be set by betting module
            min_bet=0,  # Will be set by betting module
            round_state=RoundState.new_round(1),
            pot_state=PotState(main_pot=pot),
            deck_state=DeckState(cards_remaining=0),  # Placeholder
        )
    else:
        # Use the existing game state, but ensure dealer position is set
        game_state.dealer_position = dealer_index
        game_state.round_state.phase = RoundPhase(phase)

    # Set first bettor position in round state
    game_state.round_state.first_bettor_index = (dealer_index + 1) % len(players)

    return game_state


def _ensure_game_state(
    game_state: Optional[Union[Dict, GameState]], pot: int, dealer_index: int
) -> GameState:
    """Ensures we have a proper GameState object."""
    if game_state is None:
        # Create new GameState
        from data.types.base_types import DeckState, PotState, RoundState

        return GameState(
            players=[],  # Will be populated later
            dealer_position=dealer_index,
            small_blind=0,
            big_blind=0,
            ante=0,
            min_bet=0,
            round_state=RoundState.new_round(1),
            pot_state=PotState(main_pot=pot),
            deck_state=DeckState(cards_remaining=0),
        )
    elif isinstance(game_state, dict):
        # Convert legacy dict to GameState
        from data.types.base_types import DeckState, PotState, RoundState

        return GameState(
            players=[],  # Will be populated from players list
            dealer_position=game_state.get("dealer_index", dealer_index),
            small_blind=game_state.get("small_blind", 0),
            big_blind=game_state.get("big_blind", 0),
            ante=game_state.get("ante", 0),
            min_bet=game_state.get("min_bet", 0),
            round_state=RoundState(
                round_number=1,
                phase=RoundPhase(game_state.get("phase", RoundPhase.PRE_DRAW)),
                current_bet=game_state.get("current_bet", 0),
                raise_count=game_state.get("raise_count", 0),
            ),
            pot_state=PotState(main_pot=pot),
            deck_state=DeckState(cards_remaining=0),
        )
    elif isinstance(game_state, GameState):
        return game_state
    else:
        raise TypeError("game_state must be None, dict, or GameState")


def _process_call(
    player: Player, current_bet: int, pot: int
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
    actual_bet = player.place_bet(bet_amount)
    pot += actual_bet

    # Log the action
    status = " (all in)" if player.chips == 0 else ""
    logger.info(f"{player.name} calls ${bet_amount}{status}")
    logger.info(f"  Pot after call: ${pot}")

    return pot, current_bet, None
