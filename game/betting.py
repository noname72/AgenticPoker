"""Poker betting round management and rules implementation.

This module handles all betting-related logic for a poker game, including:
"""

from typing import TYPE_CHECKING, Optional

from loggers.betting_logger import BettingLogger

from .player import Player

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
    if not game.table:
        raise ValueError("Cannot run betting round with no players")

    # Initialize pot to 0 if None
    if game.pot_manager.pot is None:
        game.pot_manager.pot = 0
    elif game.pot_manager.pot < 0:
        raise ValueError("Pot amount cannot be negative")

    # Run betting round with validated GameState
    betting_round(game)

    # Determine if game should continue
    active_count = sum(1 for p in game.table if not p.folded)
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

    game.table.reset_action_tracking()

    # Main betting loop
    while not round_complete:
        _process_betting_cycle(game, last_raiser)

        # Check if betting round should end
        round_complete = (
            game.table.is_round_complete() or game.table.all_players_acted()
        )

        if round_complete:
            BettingLogger.log_debug("Betting round is complete.")
        else:
            BettingLogger.log_debug("Betting round continues.")


def _process_betting_cycle(game: "Game", last_raiser: Optional[Player]) -> None:
    """Process a single cycle of betting for all active players."""

    while not game.table.is_round_complete():

        agent = game.table.get_next_player()
        if not agent:
            # No more active players, clear needs_to_act and end round
            game.table.needs_to_act.clear()
            break

        BettingLogger.log_player_turn(
            player_name=agent.name,
            hand=agent.hand.show() if hasattr(agent, "hand") else "Unknown",
            chips=agent.chips,
            current_bet=agent.bet,
            pot=game.pot_manager.pot,
            active_players=[p.name for p in game.table.players if not p.folded],
            last_raiser=last_raiser.name if last_raiser else None,
        )

        action_decision = agent.decide_action(game)
        agent.execute(action_decision, game)

        game.table.update(action_decision, agent)

        previous_last_raiser = last_raiser  #! needed???

        BettingLogger.log_debug(
            f"Previous Raiser: {previous_last_raiser}, Current Raiser: {last_raiser}"
        )

        BettingLogger.log_line_break()


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
    num_players = len(game.table)

    # Reset all player bets first
    for player in game.table:
        player.bet = 0

    # Collect antes
    if ante > 0:
        BettingLogger.log_collecting_antes()
        for player in game.table:
            ante_amount = min(ante, player.chips)
            collected += player.place_bet(ante_amount, game)
            BettingLogger.log_blind_or_ante(
                player.name, ante, ante_amount, is_ante=True
            )

    # Reset bets after antes
    for player in game.table:
        player.bet = 0

    # Small blind
    sb_index = (dealer_index + 1) % num_players
    sb_player = game.table[sb_index]
    sb_amount = min(small_blind, sb_player.chips)
    actual_sb = sb_player.place_bet(sb_amount, game)
    collected += actual_sb

    BettingLogger.log_blind_or_ante(
        sb_player.name, small_blind, actual_sb, is_small_blind=True
    )

    # Big blind
    bb_index = (dealer_index + 2) % num_players
    bb_player = game.table[bb_index]
    bb_amount = min(big_blind, bb_player.chips)
    actual_bb = bb_player.place_bet(bb_amount, game)
    collected += actual_bb

    BettingLogger.log_blind_or_ante(bb_player.name, big_blind, actual_bb)

    BettingLogger.log_line_break()
    return collected
