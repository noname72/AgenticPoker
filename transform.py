from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


def transform_rounds(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform round-level data into a flat DataFrame."""
    rounds = []
    session = game_data["session"]
    session_id = session["session_id"]

    for round_data in session["rounds"]:
        round_dict = {
            "session_id": session_id,
            "round_number": round_data["round_number"],
            "dealer": round_data["table_positions"].get("dealer"),
            "small_blind": round_data["table_positions"].get("small_blind"),
            "big_blind": round_data["table_positions"].get("big_blind"),
            "small_blind_amount": round_data["betting_structure"].get("small_blind"),
            "big_blind_amount": round_data["betting_structure"].get("big_blind"),
            "ante_amount": round_data["betting_structure"].get("ante"),
        }

        # Add starting stacks for each player
        for player, chips in round_data["starting_stacks"].items():
            round_dict[f"{player}_starting_stack"] = chips

        # Add showdown info if available
        if "showdown" in round_data and "result" in round_data["showdown"]:
            round_dict["winner"] = round_data["showdown"]["result"].get("winner")
            round_dict["pot_size"] = round_data["showdown"]["result"].get("pot")

        rounds.append(round_dict)

    return pd.DataFrame(rounds)


def transform_actions(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform action-level data into a flat DataFrame."""
    actions = []
    session = game_data["session"]
    session_id = session["session_id"]

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        # Process pre-draw actions
        if "pre_draw_actions" in round_data:
            for action in round_data["pre_draw_actions"]:
                action_dict = {
                    "session_id": session_id,
                    "round_number": round_num,
                    "phase": "pre_draw",
                    "player": action["player"],
                    "chips_before": action["chips"],
                    "current_bet": action["current_bet"],
                    "pot_size": action["pot"],
                    "action_type": action["action"]["type"],
                    "action_amount": action["action"]["amount"],
                    "action_reasoning": action["action"]["reasoning"],
                }

                # Add hand evaluation if available
                if action.get("evaluation"):
                    action_dict.update(
                        {
                            "hand_type": action["evaluation"]["hand"],
                            "hand_rank": action["evaluation"]["rank"],
                            "hand_tiebreakers": str(
                                action["evaluation"]["tiebreakers"]
                            ),
                        }
                    )

                # Add strategy if available
                if "strategy" in action:
                    action_dict.update(
                        {
                            "strategy_plan": action["strategy"]["plan"],
                            "strategy_reasoning": action["strategy"]["reasoning"],
                        }
                    )

                actions.append(action_dict)

        # Process post-draw actions
        if "post_draw_actions" in round_data:
            for action in round_data["post_draw_actions"]:
                action_dict = {
                    "session_id": session_id,
                    "round_number": round_num,
                    "phase": "post_draw",
                    "player": action["player"],
                    "chips_before": action["chips"],
                    "current_bet": action["current_bet"],
                    "pot_size": action["pot"],
                    "action_type": action["action"]["type"],
                    "action_amount": action["action"]["amount"],
                    "action_reasoning": action["action"]["reasoning"],
                }

                if action.get("evaluation"):
                    action_dict.update(
                        {
                            "hand_type": action["evaluation"]["hand"],
                            "hand_rank": action["evaluation"]["rank"],
                            "hand_tiebreakers": str(
                                action["evaluation"]["tiebreakers"]
                            ),
                        }
                    )

                if "strategy" in action:
                    action_dict.update(
                        {
                            "strategy_plan": action["strategy"]["plan"],
                            "strategy_reasoning": action["strategy"]["reasoning"],
                        }
                    )

                actions.append(action_dict)

    return pd.DataFrame(actions)


def transform_showdowns(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform showdown-level data into a flat DataFrame."""
    showdowns = []
    session = game_data["session"]
    session_id = session["session_id"]

    for round_data in session["rounds"]:
        if "showdown" in round_data:
            showdown_data = round_data["showdown"]

            # Process each player's showdown hand
            for player_data in showdown_data["players"]:
                showdown_dict = {
                    "session_id": session_id,
                    "round_number": round_data["round_number"],
                    "player": player_data["player"],
                    "shown_hand": ", ".join(player_data["hand"]),
                }

                # Add hand evaluation if available
                if player_data.get("evaluation"):
                    showdown_dict.update(
                        {
                            "hand_type": player_data["evaluation"]["hand"],
                            "hand_rank": player_data["evaluation"]["rank"],
                            "hand_tiebreakers": str(
                                player_data["evaluation"]["tiebreakers"]
                            ),
                        }
                    )

                # Add result information
                if "result" in showdown_data:
                    showdown_dict.update(
                        {
                            "is_winner": player_data["player"]
                            == showdown_data["result"]["winner"],
                            "pot_size": showdown_data["result"]["pot"],
                            "chip_change": showdown_data["result"]["chip_changes"].get(
                                player_data["player"], 0
                            ),
                        }
                    )

                showdowns.append(showdown_dict)

    return pd.DataFrame(showdowns)


def _get_hand_rank(hand_type: str) -> int:
    """Convert hand type to numeric rank for comparison."""
    hand_ranks = {
        "High Card": 1,
        "One Pair": 2,
        "Two Pair": 3,
        "Three of a Kind": 4,
        "Straight": 5,
        "Flush": 6,
        "Full House": 7,
        "Four of a Kind": 8,
        "Straight Flush": 9,
        "Royal Flush": 10,
    }
    return hand_ranks.get(hand_type, 0)


def transform_player_trajectories(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform player chip trajectories into a time series DataFrame."""
    trajectories = []
    session = game_data["session"]
    players = list(session["players"].keys())

    # Initialize starting stacks
    current_stacks = {
        player: info["initial_chips"] for player, info in session["players"].items()
    }

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        # Record starting stacks for this round
        for player in players:
            trajectories.append(
                {
                    "round_number": round_num,
                    "phase": "start",
                    "player": player,
                    "chips": current_stacks.get(player, 0),
                }
            )

        # Update stacks based on showdown results
        if "showdown" in round_data and "result" in round_data["showdown"]:
            for player, change in round_data["showdown"]["result"][
                "chip_changes"
            ].items():
                current_stacks[player] = current_stacks.get(player, 0) + change
                trajectories.append(
                    {
                        "round_number": round_num,
                        "phase": "end",
                        "player": player,
                        "chips": current_stacks[player],
                    }
                )

    return pd.DataFrame(trajectories)


def transform_player_actions(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform player action statistics into a DataFrame."""
    action_stats = []
    session = game_data["session"]

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        for phase in ["pre_draw_actions", "post_draw_actions"]:
            if phase in round_data:
                for action in round_data[phase]:
                    bet_amount = action["action"].get("amount", 0)
                    # Only calculate ratio for actual bets/raises
                    bet_to_pot_ratio = (
                        bet_amount / action["pot"]
                        if bet_amount
                        and action["pot"] > 0
                        and action["action"]["type"] == "raise"
                        else 0
                    )

                    action_stats.append(
                        {
                            "round_number": round_num,
                            "phase": phase.replace("_actions", ""),
                            "player": action["player"],
                            "action_type": action["action"]["type"],
                            "bet_amount": (
                                bet_amount if bet_amount else None
                            ),  # Convert 0 to None for folds
                            "pot_size": action["pot"],
                            "bet_to_pot_ratio": bet_to_pot_ratio,
                        }
                    )

    return pd.DataFrame(action_stats)


def transform_hand_distributions(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform hand type distributions into a DataFrame."""
    hands = []
    session = game_data["session"]

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        # Process hands from actions
        for phase in ["pre_draw_actions", "post_draw_actions"]:
            if phase in round_data:
                for action in round_data[phase]:
                    if "evaluation" in action:
                        # Extract the base hand type (e.g., "One Pair" from "One Pair, 8s")
                        hand_type = action["evaluation"]["rank"]
                        hands.append(
                            {
                                "round_number": round_num,
                                "phase": phase.replace("_actions", ""),
                                "player": action["player"],
                                "hand_type": action["evaluation"]["hand"],
                                "hand_rank": _get_hand_rank(
                                    hand_type
                                ),  # Use rank instead of full hand description
                                "won_hand": False,  # Will update based on showdown
                            }
                        )

        # Update winner from showdown
        if "showdown" in round_data and "result" in round_data["showdown"]:
            winner = round_data["showdown"]["result"]["winner"]
            for hand in hands:
                if (
                    hand["round_number"] == round_num
                    and hand["player"] == winner
                    and hand["phase"] == "post_draw"
                ):
                    hand["won_hand"] = True

    return pd.DataFrame(hands)


def transform_betting_stats(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform betting statistics into a DataFrame."""
    betting_stats = []
    session = game_data["session"]

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        # Calculate pot sizes and betting patterns
        if "showdown" in round_data and "result" in round_data["showdown"]:
            final_pot = round_data["showdown"]["result"]["pot"]

            # Get maximum bet for the round
            max_bet = 0
            for phase in ["pre_draw_actions", "post_draw_actions"]:
                if phase in round_data:
                    for action in round_data[phase]:
                        if action["action"]["type"] == "raise":
                            max_bet = max(max_bet, action["action"].get("amount", 0))

            betting_stats.append(
                {
                    "round_number": round_num,
                    "final_pot": final_pot,
                    "max_bet": max_bet,
                    "num_players_in_showdown": len(round_data["showdown"]["players"]),
                    "winner": round_data["showdown"]["result"]["winner"],
                }
            )

    return pd.DataFrame(betting_stats)


def transform_player_stats(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform aggregate player statistics into a DataFrame."""
    player_stats = defaultdict(
        lambda: {
            "total_hands_played": 0,
            "hands_won": 0,
            "total_profit_loss": 0,
            "num_folds": 0,
            "num_calls": 0,
            "num_raises": 0,
            "total_amount_bet": 0,
            "largest_pot_won": 0,
        }
    )

    session = game_data["session"]

    # Initialize players
    for player in session["players"]:
        player_stats[player]

    for round_data in session["rounds"]:
        # Count actions
        for phase in ["pre_draw_actions", "post_draw_actions"]:
            if phase in round_data:
                for action in round_data[phase]:
                    player = action["player"]
                    action_type = action["action"]["type"]
                    player_stats[player]["total_hands_played"] += 1

                    if action_type == "fold":
                        player_stats[player]["num_folds"] += 1
                    elif action_type == "call":
                        player_stats[player]["num_calls"] += 1
                    elif action_type == "raise":
                        player_stats[player]["num_raises"] += 1
                        player_stats[player]["total_amount_bet"] += action[
                            "action"
                        ].get("amount", 0)

        # Update showdown results
        if "showdown" in round_data and "result" in round_data["showdown"]:
            winner = round_data["showdown"]["result"]["winner"]
            pot_size = round_data["showdown"]["result"]["pot"]

            player_stats[winner]["hands_won"] += 1
            player_stats[winner]["largest_pot_won"] = max(
                player_stats[winner]["largest_pot_won"], pot_size
            )

            # Update profit/loss
            for player, change in round_data["showdown"]["result"][
                "chip_changes"
            ].items():
                player_stats[player]["total_profit_loss"] += change

    # Convert to DataFrame
    stats_list = [{"player": player, **stats} for player, stats in player_stats.items()]

    return pd.DataFrame(stats_list)


def transform_position_stats(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform position-based statistics into a DataFrame."""
    position_stats = []
    session = game_data["session"]

    for round_data in session["rounds"]:
        round_num = round_data["round_number"]
        positions = round_data["table_positions"]

        # Track outcomes for each position
        for player in session["players"].keys():
            position = None
            # Determine player's position
            if positions.get("dealer") == player:
                position = "dealer"
            elif positions.get("small_blind") == player:
                position = "small_blind"
            elif positions.get("big_blind") == player:
                position = "big_blind"
            elif "others" in positions and player in positions["others"]:
                position = f"position_{positions['others'].index(player) + 1}"

            if position:
                # Calculate chip change for the round
                chip_change = 0
                if "showdown" in round_data and "result" in round_data["showdown"]:
                    chip_change = round_data["showdown"]["result"]["chip_changes"].get(
                        player, 0
                    )

                # Calculate win status
                won_round = False
                if "showdown" in round_data and "result" in round_data["showdown"]:
                    won_round = round_data["showdown"]["result"]["winner"] == player

                position_stats.append(
                    {
                        "round_number": round_num,
                        "player": player,
                        "position": position,
                        "chip_change": chip_change,
                        "won_round": won_round,
                        "num_players": len(round_data["starting_stacks"]),
                        "initial_stack": round_data["starting_stacks"].get(player, 0),
                    }
                )

    return pd.DataFrame(position_stats)


def transform_elimination_stats(game_data: Dict[str, Any]) -> pd.DataFrame:
    """Transform elimination statistics into a DataFrame."""
    eliminations = []
    session = game_data["session"]

    # Track when players were eliminated
    eliminated_players = set()
    for round_data in session["rounds"]:
        round_num = round_data["round_number"]

        if "eliminations" in round_data:
            for player in round_data["eliminations"]:
                if player not in eliminated_players:
                    # Get position at elimination
                    position = None
                    positions = round_data["table_positions"]
                    if positions.get("dealer") == player:
                        position = "dealer"
                    elif positions.get("small_blind") == player:
                        position = "small_blind"
                    elif positions.get("big_blind") == player:
                        position = "big_blind"
                    elif "others" in positions and player in positions["others"]:
                        position = f"position_{positions['others'].index(player) + 1}"

                    eliminations.append(
                        {
                            "player": player,
                            "elimination_round": round_num,
                            "position_at_elimination": position,
                            "num_players_remaining": len(round_data["starting_stacks"]),
                            "final_rank": next(
                                (
                                    s["rank"]
                                    for s in session["final_standings"]
                                    if s["player"] == player
                                ),
                                None,
                            ),
                        }
                    )
                    eliminated_players.add(player)

    # Add entries for winners (non-eliminated players)
    for player in session["players"]:
        if player not in eliminated_players:
            eliminations.append(
                {
                    "player": player,
                    "elimination_round": None,
                    "position_at_elimination": None,
                    "num_players_remaining": 1,
                    "final_rank": next(
                        (
                            s["rank"]
                            for s in session["final_standings"]
                            if s["player"] == player
                        ),
                        None,
                    ),
                }
            )

    return pd.DataFrame(eliminations)


def transform_game_data(game_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Transform the entire game data into a collection of normalized DataFrames."""
    transformed = {
        "rounds": transform_rounds(game_data),
        "actions": transform_actions(game_data),
        "showdowns": transform_showdowns(game_data),
        "trajectories": transform_player_trajectories(game_data),
        "action_stats": transform_player_actions(game_data),
        "hand_distributions": transform_hand_distributions(game_data),
        "betting_stats": transform_betting_stats(game_data),
        "player_stats": transform_player_stats(game_data),
        "position_stats": transform_position_stats(game_data),
        "elimination_stats": transform_elimination_stats(game_data),
    }

    # Clean up NaN values before converting to JSON
    for df in transformed.values():
        # Replace NaN with None (which becomes null in JSON)
        df.replace({float("nan"): None}, inplace=True)

    return transformed


if __name__ == "__main__":
    import json

    # Read the parsed game data
    with open("parsed_game.json", "r", encoding="utf-8") as f:
        game_data = json.load(f)

    # Transform the data into DataFrames
    transformed_data = transform_game_data(game_data)

    # Convert each DataFrame to a dictionary format
    json_data = {
        name: df.to_dict(orient="records") for name, df in transformed_data.items()
    }

    # Save all data to a single JSON file
    with open("transformed_game.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved transformed_game.json with data for {len(json_data)} tables")
