from datetime import datetime
from typing import Any, Dict, List

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


def transform_game_data(game_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Transform the entire game data into a collection of normalized DataFrames."""
    return {
        "rounds": transform_rounds(game_data),
        "actions": transform_actions(game_data),
        "showdowns": transform_showdowns(game_data),
    }


if __name__ == "__main__":
    import json

    # Read the parsed game data
    with open("parsed_game.json", "r", encoding="utf-8") as f:
        game_data = json.load(f)

    # Transform the data into DataFrames
    transformed_data = transform_game_data(game_data)

    # Save each DataFrame to a CSV file
    for name, df in transformed_data.items():
        df.to_csv(f"{name}.csv", index=False)
        print(f"Saved {name}.csv with {len(df)} rows")
