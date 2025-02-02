import json
import logging
import re
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParserError(Exception):
    """Custom exception for parsing errors."""

    pass


def safe_regex_search(
    pattern: str, text: str, section: str = "unknown", flags: int = 0
) -> Optional[re.Match]:
    """
    Safely perform regex search with logging.

    Args:
        pattern: Regex pattern to search for
        text: Text to search in
        section: Name of the section being parsed (for logging)
        flags: Regex flags

    Returns:
        Optional[re.Match]: Match object if found, None otherwise
    """
    try:
        match = re.search(pattern, text, flags)
        if not match:
            logger.warning(f"No match found for pattern in {section} section")
        return match
    except re.error as e:
        logger.error(f"Regex error in {section} section: {str(e)}")
        return None


def parse_session_metadata(log_text: str) -> Dict[str, str]:
    """
    Extract session-level metadata from the log.

    Looks for session ID and start time in the format:
    New Poker Game Session Started - ID: <id>
    Started at: <timestamp>

    Args:
        log_text: Full log text

    Returns:
        Dict containing session_id and start_time
    """
    meta = {}
    try:
        session_match = safe_regex_search(
            r"New Poker Game Session Started - ID:\s*(\S+)\nStarted at:\s*([^\n]+)",
            log_text,
            "session metadata",
        )
        if session_match:
            meta["session_id"] = session_match.group(1)
            meta["start_time"] = session_match.group(2)
        else:
            logger.error("Failed to parse session metadata")
    except Exception as e:
        logger.error(f"Error parsing session metadata: {str(e)}")
    return meta


def parse_game_config(log_text: str) -> Dict[str, Any]:
    """
    Extract game configuration details.

    Parses the Game Configuration section for:
    - Starting chips
    - Blinds (small and big)
    - Ante

    Args:
        log_text: Full log text

    Returns:
        Dict containing game configuration parameters
    """
    config = {}
    try:
        config_section = safe_regex_search(
            r"==================================================\nGame Configuration\n==================================================\n(.*?)\n={10,}",
            log_text,
            "game configuration",
            re.DOTALL,
        )
        if config_section:
            content = config_section.group(1)

            # Parse starting chips
            starting_chips = safe_regex_search(
                r"Starting chips: \$(\d+)", content, "starting chips"
            )
            if starting_chips:
                config["starting_chips"] = int(starting_chips.group(1))

            # Parse blinds
            blinds = safe_regex_search(r"Blinds: \$(\d+)/\$(\d+)", content, "blinds")
            if blinds:
                config["blinds"] = {
                    "small": int(blinds.group(1)),
                    "big": int(blinds.group(2)),
                }

            # Parse ante
            ante = safe_regex_search(r"Ante: \$(\d+)", content, "ante")
            if ante:
                config["ante"] = int(ante.group(1))
        else:
            logger.error("Failed to parse game configuration section")
    except Exception as e:
        logger.error(f"Error parsing game configuration: {str(e)}")
    return config


def parse_players(log_text: str) -> Dict[str, Dict[str, int]]:
    """
    Extract player creation events and initial chip counts.

    Looks for lines in the format:
    New player created: <name> with $<amount> chips

    Args:
        log_text: Full log text

    Returns:
        Dict mapping player names to their initial chip counts
    """
    players = {}
    try:
        for match in re.finditer(
            r"New player created:\s*(\w+)\s*with\s*\$(\d+)\s*chips", log_text
        ):
            name = match.group(1)
            chips = int(match.group(2))
            players[name] = {"initial_chips": chips}
            logger.debug(f"Parsed player creation: {name} with {chips} chips")
    except Exception as e:
        logger.error(f"Error parsing player creation events: {str(e)}")
    return players


def parse_table_positions(section: str) -> Dict[str, Any]:
    """
    Extract table positions from a round section.

    Args:
        section: Round section text containing table positions

    Returns:
        Dict containing dealer, small_blind, big_blind and optional others list
    """
    positions = {}
    try:
        pos_match = safe_regex_search(
            r"Table positions:(.*?)(?=\n\n)", section, "table positions", re.DOTALL
        )
        if pos_match:
            content = pos_match.group(1)

            # For heads-up play (2 players), positions are different
            if "Position" not in content:  # Heads-up format
                dealer = safe_regex_search(r"Dealer: (\w+)", content)
                small_blind = safe_regex_search(r"Small Blind: (\w+)", content)

                if dealer:
                    positions["dealer"] = dealer.group(1)
                    # In heads-up, dealer is small blind
                    positions["small_blind"] = dealer.group(1)
                    # Find the other player for big blind
                    other_player = small_blind.group(1) if small_blind else None
                    if other_player:
                        positions["big_blind"] = other_player
            else:  # Regular format
                dealer = safe_regex_search(r"Dealer: (\w+)", content)
                small_blind = safe_regex_search(r"Small Blind: (\w+)", content)
                big_blind = safe_regex_search(r"Big Blind: (\w+)", content)

                if dealer:
                    positions["dealer"] = dealer.group(1)
                if small_blind:
                    positions["small_blind"] = small_blind.group(1)
                if big_blind:
                    positions["big_blind"] = big_blind.group(1)

                # Get other positions
                others = re.findall(r"Position \d+: (\w+)", content)
                if others:
                    positions["others"] = others

        else:
            logger.warning("No table positions found in section")
    except Exception as e:
        logger.error(f"Error parsing table positions: {str(e)}")
    return positions


def parse_betting_structure(section: str) -> Dict[str, int]:
    """
    Extract betting structure from a round section.

    Args:
        section: Round section text containing betting structure

    Returns:
        Dict containing small_blind, big_blind, ante and min_bet values
    """
    structure = {}
    try:
        struct_match = safe_regex_search(
            r"Betting structure:(.*?)(?=\n\n)", section, "betting structure", re.DOTALL
        )
        if struct_match:
            content = struct_match.group(1)

            for key, pattern in {
                "small_blind": r"Small blind: \$(\d+)",
                "big_blind": r"Big blind: \$(\d+)",
                "ante": r"Ante: \$(\d+)",
                "min_bet": r"Minimum bet: \$(\d+)",
            }.items():
                match = safe_regex_search(pattern, content, f"{key} value")
                if match:
                    structure[key] = int(match.group(1))
                else:
                    logger.warning(f"Missing {key} in betting structure")
        else:
            logger.warning("No betting structure found in section")
    except Exception as e:
        logger.error(f"Error parsing betting structure: {str(e)}")
    return structure


def parse_antes(section: str) -> List[Dict[str, Any]]:
    """
    Extract ante actions from a round section.

    Args:
        section: Round section text containing ante actions

    Returns:
        List of dicts containing player and amount for each ante
    """
    antes = []
    try:
        for match in re.finditer(r"(\w+) posts ante of \$(\d+)", section):
            try:
                antes.append({"player": match.group(1), "amount": int(match.group(2))})
            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing individual ante: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing antes: {str(e)}")
    return antes


def parse_hand_evaluation(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse hand evaluation details.

    Args:
        text: Text containing hand evaluation in either inline or detailed format

    Returns:
        Dict containing hand description, rank and tiebreakers, or None if not found
    """
    try:
        # Try the inline format first
        eval_match = safe_regex_search(
            r"- (.*?) \[Rank: (.*?), Tiebreakers: \[(.*?)\]\]",
            text,
            "inline hand evaluation",
        )
        if not eval_match:
            # Try the showdown format
            eval_match = safe_regex_search(
                r"Hand: (.*?)\n.*?Rank: (.*?)\n.*?Tiebreakers: \[(.*?)\]",
                text,
                "detailed hand evaluation",
                re.DOTALL,
            )

        if eval_match:
            try:
                return {
                    "hand": eval_match.group(1),
                    "rank": eval_match.group(2),
                    "tiebreakers": [int(x) for x in eval_match.group(3).split(", ")],
                }
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing hand evaluation values: {str(e)}")
                return None
    except Exception as e:
        logger.error(f"Error parsing hand evaluation: {str(e)}")
    return None


def parse_betting_actions(
    section: str, phase: str = "pre_draw"
) -> List[Dict[str, Any]]:
    """Extract betting actions from a betting section."""
    actions = []
    try:
        for active_section in re.finditer(
            r"---- (\w+) is active ----(.*?)(?=----|\n\n====|\Z)", section, re.DOTALL
        ):
            try:
                player = active_section.group(1)
                content = active_section.group(2)

                # Extract required information
                hand_match = safe_regex_search(
                    r"Hand: (.*?)\n", content, f"{phase} hand"
                )
                chips_match = safe_regex_search(
                    r"Player chips: \$(\d+)", content, "chips"
                )
                bet_match = safe_regex_search(
                    r"Player current bet: \$(\d+)", content, "current bet"
                )
                pot_match = safe_regex_search(r"Current pot: \$(\d+)", content, "pot")

                if all([hand_match, chips_match, bet_match, pot_match]):
                    action = {
                        "player": player,
                        "hand": [
                            card.strip() for card in hand_match.group(1).split(",")
                        ],
                        "evaluation": parse_hand_evaluation(content),
                        "chips": int(chips_match.group(1)),
                        "current_bet": int(bet_match.group(1)),
                        "pot": int(pot_match.group(1)),
                    }

                    # Parse strategy if present (but don't warn if missing)
                    strategy_match = re.search(
                        r"\[Strategy\] New Plan: approach=(.*?) reasoning='(.*?)'",
                        content,
                    )
                    if strategy_match:
                        action["strategy"] = {
                            "plan": strategy_match.group(1),
                            "reasoning": strategy_match.group(2),
                        }

                    # Try multiple action patterns without warnings
                    action_info = None

                    # Pattern 1: [Action] Action: type - reasoning
                    match = re.search(
                        r"\[Action\] Action: (\w+)\s*-\s*(.*?)(?:\n|$)", content
                    )
                    if match:
                        action_info = {
                            "type": match.group(1).lower(),
                            "reasoning": match.group(2).strip(),
                        }

                    # Pattern 2: [Action] Action: type amount - reasoning
                    if not action_info:
                        match = re.search(
                            r"\[Action\] Action: (\w+)\s+(\d+)\s*-\s*(.*?)(?:\n|$)",
                            content,
                        )
                        if match:
                            action_info = {
                                "type": match.group(1).lower(),
                                "amount": int(match.group(2)),
                                "reasoning": match.group(3).strip(),
                            }

                    # Pattern 3: Player executes: ACTION
                    if not action_info:
                        match = re.search(r"(\w+) executes: (\w+)", content)
                        if match:
                            action_info = {
                                "type": match.group(2).lower(),
                                "reasoning": match.group(2).upper(),
                            }

                    if action_info:
                        action["action"] = {
                            "type": action_info["type"],
                            "amount": action_info.get("amount", None),
                            "reasoning": action_info["reasoning"],
                        }

                        # Set default amount for calls to 0
                        if (
                            action_info["type"] == "call"
                            and action["action"]["amount"] is None
                        ):
                            action["action"]["amount"] = 0

                        actions.append(action)
                    else:
                        logger.error(
                            f"Could not parse action for player {player} in {phase}"
                        )

            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing individual action in {phase}: {str(e)}")

    except Exception as e:
        logger.error(f"Error parsing betting actions in {phase}: {str(e)}")
    return actions


def parse_draw_phase(section: str) -> List[Dict[str, Any]]:
    """
    Extract draw phase actions.

    Args:
        section: Draw phase section text

    Returns:
        List of dicts containing player draw actions and deck information
    """
    draws = []
    try:
        for match in re.finditer(
            r"Draw phase: (\w+) discarding (\d+) cards\nDeck status.*?: (\d+)", section
        ):
            try:
                draws.append(
                    {
                        "player": match.group(1),
                        "cards_discarded": int(match.group(2)),
                        "deck_remaining": int(match.group(3)),
                    }
                )
            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing individual draw action: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing draw phase: {str(e)}")
    return draws


def parse_showdown(section: str) -> Dict[str, Any]:
    """
    Extract showdown information.

    Args:
        section: Showdown section text

    Returns:
        Dict containing players' hands, evaluations and results
    """
    showdown = {"players": [], "result": {}}
    try:
        # Parse player hands and evaluations
        for player_section in re.finditer(
            r"(\w+) shows:.*?(?=\n\n|\Z)", section, re.DOTALL
        ):
            try:
                content = player_section.group(0)

                # Extract player name and hand
                hand_match = safe_regex_search(
                    r"(\w+) shows: (.*?)\n", content, "showdown hand"
                )
                if hand_match:
                    player = {
                        "player": hand_match.group(1),
                        "hand": [
                            card.strip() for card in hand_match.group(2).split(",")
                        ],
                    }

                    # Look for hand evaluation in both formats
                    eval_match = safe_regex_search(
                        r"- (.*?) \[Rank: (.*?), Tiebreakers: \[(.*?)\]\]",
                        content,
                        "showdown evaluation",
                    )
                    if not eval_match:
                        eval_match = safe_regex_search(
                            r"Hand: (.*?)\n.*?Rank: (.*?)\n.*?Tiebreakers: \[(.*?)\]",
                            content,
                            "detailed showdown evaluation",
                            re.DOTALL,
                        )

                    if eval_match:
                        player["evaluation"] = {
                            "hand": eval_match.group(1),
                            "rank": eval_match.group(2),
                            "tiebreakers": [
                                int(x) for x in eval_match.group(3).split(", ")
                            ],
                        }
                    else:
                        # Try to find evaluation in the hand evaluation section
                        name = player["player"]
                        eval_section = safe_regex_search(
                            rf"{name}'s hand evaluation:.*?Hand: (.*?)\n.*?Rank: (.*?)\n.*?Tiebreakers: \[(.*?)\]",
                            section,
                            f"{name}'s hand evaluation",
                            re.DOTALL,
                        )
                        if eval_section:
                            player["evaluation"] = {
                                "hand": eval_section.group(1),
                                "rank": eval_section.group(2),
                                "tiebreakers": [
                                    int(x) for x in eval_section.group(3).split(", ")
                                ],
                            }

                    showdown["players"].append(player)
            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing individual showdown hand: {str(e)}")

        # Parse results
        winner_match = safe_regex_search(
            r"(\w+) wins \$(\d+)", section, "showdown winner"
        )
        if winner_match:
            showdown["result"]["winner"] = winner_match.group(1)
            showdown["result"]["pot"] = int(winner_match.group(2))

            # Parse chip changes
            showdown["result"]["chip_changes"] = {}
            for change in re.finditer(r"(\w+) (gains|loses) \$(\d+)", section):
                try:
                    amount = int(change.group(3))
                    showdown["result"]["chip_changes"][change.group(1)] = (
                        amount if change.group(2) == "gains" else -amount
                    )
                except (IndexError, ValueError) as e:
                    logger.error(f"Error parsing chip change: {str(e)}")
        else:
            logger.warning("No winner found in showdown")

    except Exception as e:
        logger.error(f"Error parsing showdown: {str(e)}")
    return showdown


def parse_rounds(log_text: str) -> List[Dict[str, Any]]:
    """
    Extract round sections and details from the log.

    Args:
        log_text: Full log text

    Returns:
        List of dicts containing round-by-round data including:
        - Round number
        - Starting stacks
        - Table positions
        - Betting structure
        - Antes
        - Pre-draw actions
        - Draw phase
        - Post-draw actions
        - Showdown
        - Eliminations
    """
    rounds = []
    try:
        round_sections = re.split(r"={10,}\s*Round\s*(\d+)\s*={10,}", log_text)

        for i in range(1, len(round_sections), 2):
            try:
                round_num = int(round_sections[i])
                round_content = round_sections[i + 1]

                round_data = {
                    "round_number": round_num,
                    "starting_stacks": {},
                    "table_positions": parse_table_positions(round_content),
                    "betting_structure": parse_betting_structure(round_content),
                    "antes": parse_antes(round_content),
                }

                # Parse starting stacks
                stacks_section = safe_regex_search(
                    r"Starting stacks.*?(?=\n\n)",
                    round_content,
                    f"starting stacks round {round_num}",
                    re.DOTALL,
                )
                if stacks_section:
                    for line in re.findall(
                        r"\s*(\w+):\s*\$(\d+)", stacks_section.group()
                    ):
                        try:
                            name, chips = line
                            round_data["starting_stacks"][name] = int(chips)
                        except (ValueError, IndexError) as e:
                            logger.error(
                                f"Error parsing stack amount in round {round_num}: {str(e)}"
                            )
                else:
                    logger.warning(f"No starting stacks found for round {round_num}")

                # Only look for sections if they exist in the content
                if "Pre-draw betting" in round_content:
                    pre_draw_section = safe_regex_search(
                        r"====== Pre-draw betting ======(.*?)====== Pre-draw betting Complete ======",
                        round_content,
                        f"pre-draw betting round {round_num}",
                        re.DOTALL,
                    )
                    if pre_draw_section:
                        round_data["pre_draw_actions"] = parse_betting_actions(
                            pre_draw_section.group(1)
                        )

                if "Draw Phase" in round_content:
                    draw_section = safe_regex_search(
                        r"====== Draw Phase ======(.*?)====== Draw Phase Complete ======",
                        round_content,
                        f"draw phase round {round_num}",
                        re.DOTALL,
                    )
                    if draw_section:
                        round_data["draw_phase"] = parse_draw_phase(
                            draw_section.group(1)
                        )

                if "Post-draw betting" in round_content:
                    post_draw_section = safe_regex_search(
                        r"====== Post-draw betting ======(.*?)====== Post-draw betting Complete ======",
                        round_content,
                        f"post-draw betting round {round_num}",
                        re.DOTALL,
                    )
                    if post_draw_section:
                        round_data["post_draw_actions"] = parse_betting_actions(
                            post_draw_section.group(1), "post_draw"
                        )

                if "Showdown" in round_content:
                    showdown_section = safe_regex_search(
                        r"====== Showdown ======(.*?)====== Showdown Complete ======",
                        round_content,
                        f"showdown round {round_num}",
                        re.DOTALL,
                    )
                    if showdown_section:
                        round_data["showdown"] = parse_showdown(
                            showdown_section.group(1)
                        )

                # Parse eliminations
                eliminations = re.findall(r"(\w+) is eliminated", round_content)
                if eliminations:
                    round_data["eliminations"] = eliminations

                rounds.append(round_data)
                logger.debug(f"Successfully parsed round {round_num}")

            except Exception as e:
                logger.error(f"Error parsing round {i//2 + 1}: {str(e)}")

    except Exception as e:
        logger.error(f"Error parsing rounds: {str(e)}")
    return rounds


def parse_final_standings(log_text: str) -> List[Dict[str, Any]]:
    """
    Extract final standings from the log.

    Args:
        log_text: Full log text

    Returns:
        List of dicts containing final player rankings, chips, and elimination status
    """
    standings = []
    try:
        standings_section = safe_regex_search(
            r"Final Standings:(.*?)(?=\n\n|$)", log_text, "final standings", re.DOTALL
        )
        if standings_section:
            for line in standings_section.group(1).strip().split("\n"):
                try:
                    match = re.match(
                        r"\d+\.\s+(\w+):\s*\$(\d+)(?:\s+\((eliminated)\))?",
                        line.strip(),
                    )
                    if match:
                        standing = {
                            "rank": len(standings) + 1,
                            "player": match.group(1),
                            "chips": int(match.group(2)),
                        }
                        if match.group(3):
                            standing["status"] = "eliminated"
                        standings.append(standing)
                except (IndexError, ValueError) as e:
                    logger.error(f"Error parsing standing line '{line}': {str(e)}")
        else:
            logger.warning("No final standings section found")
    except Exception as e:
        logger.error(f"Error parsing final standings: {str(e)}")
    return standings


def parse_log(log_text: str) -> Dict[str, Any]:
    """
    Parse the entire poker game log and return structured data.

    The returned dictionary contains:
    - Session metadata (ID, start time)
    - Game configuration (chips, blinds, ante)
    - Player information
    - Round-by-round data
    - Final standings

    Args:
        log_text: Complete poker game log text

    Returns:
        Dict containing structured game data

    Raises:
        ParserError: If critical parsing errors occur
    """
    try:
        data = {"session": {}}

        # Session metadata
        data["session"].update(parse_session_metadata(log_text))
        if not data["session"]:
            raise ParserError("Failed to parse session metadata")

        # Game configuration
        data["session"]["game_config"] = parse_game_config(log_text)
        if not data["session"]["game_config"]:
            raise ParserError("Failed to parse game configuration")

        # Players
        data["session"]["players"] = parse_players(log_text)
        if not data["session"]["players"]:
            raise ParserError("Failed to parse player information")

        # Rounds
        data["session"]["rounds"] = parse_rounds(log_text)

        # Final standings
        data["session"]["final_standings"] = parse_final_standings(log_text)
        if not data["session"]["final_standings"]:
            logger.warning("No final standings found in log")

        return data

    except ParserError as e:
        logger.error(f"Critical parsing error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing log: {str(e)}")
        raise ParserError(f"Failed to parse log: {str(e)}")


if __name__ == "__main__":
    try:
        # Configure logging for the script
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename="parser.log",
        )

        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logging.getLogger("").addHandler(console)

        logger.info("Starting log parsing")

        with open("poker_game.log", "r", encoding="utf-8") as f:
            log_text = f.read()

        structured_data = parse_log(log_text)

        # Save the JSON to a file with proper formatting
        with open("parsed_game.json", "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)

        logger.info("Successfully parsed log and saved JSON output")

    except Exception as e:
        logger.error(f"Failed to parse poker game log: {str(e)}")
        raise
