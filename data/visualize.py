import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Read the JSON data
with open("transformed_game.json", "r") as f:
    data = json.load(f)

# Set style for better visualizations
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


def create_chip_stack_evolution():
    # Extract trajectories data
    trajectories = pd.DataFrame(data["trajectories"])

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Plot lines for each player
    for player in trajectories["player"].unique():
        player_data = trajectories[trajectories["player"] == player]
        plt.plot(
            player_data["round_number"],
            player_data["chips"],
            marker="o",
            label=player,
            linewidth=2,
        )

    plt.title("Chip Stack Evolution Over Time", fontsize=14, pad=20)
    plt.xlabel("Round Number", fontsize=12)
    plt.ylabel("Chip Stack", fontsize=12)
    plt.legend(title="Players", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.7)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save the plot
    plt.savefig("chip_stack_evolution.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_cumulative_profit_loss():
    # Extract round outcomes data
    outcomes = pd.DataFrame(data["round_outcomes"])

    # Create a DataFrame with cumulative profits for each player
    cumulative_profits = pd.DataFrame()

    for player in outcomes["player"].unique():
        player_data = outcomes[outcomes["player"] == player]
        cumulative = player_data["chip_change"].cumsum()
        cumulative.index = player_data["round_number"]
        cumulative_profits[player] = cumulative

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Plot lines for each player
    for player in cumulative_profits.columns:
        plt.plot(
            cumulative_profits.index,
            cumulative_profits[player],
            marker="o",
            label=player,
            linewidth=2,
        )

    plt.title("Cumulative Profit/Loss Over Time", fontsize=14, pad=20)
    plt.xlabel("Round Number", fontsize=12)
    plt.ylabel("Cumulative Profit/Loss", fontsize=12)
    plt.legend(title="Players", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.7)

    # Add a horizontal line at y=0 to show break-even point
    plt.axhline(y=0, color="black", linestyle="--", alpha=0.3)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save the plot
    plt.savefig("cumulative_profit_loss.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_bet_size_distribution():
    # Extract actions data
    actions_df = pd.DataFrame(data["actions"])

    # Filter for actions with actual bets (raises)
    bet_actions = actions_df[actions_df["action_amount"].notna()]

    plt.figure(figsize=(12, 6))

    # Create box plots for each player
    sns.boxplot(x="player", y="action_amount", data=bet_actions)

    # Add individual points for better visualization
    sns.swarmplot(
        x="player", y="action_amount", data=bet_actions, color="0.25", alpha=0.5
    )

    plt.title("Distribution of Bet Sizes by Player", fontsize=14, pad=20)
    plt.xlabel("Player", fontsize=12)
    plt.ylabel("Bet Size", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig("bet_size_distribution.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_action_frequency():
    # Extract player stats data instead of action stats
    actions_df = pd.DataFrame(data["player_stats"])

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Set the positions for the bars
    bar_width = 0.25
    players = actions_df["player"].unique()
    x = np.arange(len(players))

    # Plot bars for each action type using the correct column names
    plt.bar(x - bar_width, actions_df["num_raises"], bar_width, label="Raises")
    plt.bar(x, actions_df["num_calls"], bar_width, label="Calls")
    plt.bar(x + bar_width, actions_df["num_folds"], bar_width, label="Folds")

    plt.title("Action Frequency by Player", fontsize=14, pad=20)
    plt.xlabel("Player", fontsize=12)
    plt.ylabel("Number of Actions", fontsize=12)
    plt.xticks(x, players)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig("action_frequency.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_hand_type_distribution():
    # Extract hand distributions data
    hands_df = pd.DataFrame(data["hand_distributions"])

    # Create the plot
    plt.figure(figsize=(14, 6))

    # Group by hand type and count occurrences
    hand_counts = hands_df.groupby(["player", "hand_type"]).size().unstack(fill_value=0)

    # Create the stacked bar chart
    hand_counts.plot(kind="bar", stacked=True)

    plt.title("Distribution of Hand Types by Player", fontsize=14, pad=20)
    plt.xlabel("Player", fontsize=12)
    plt.ylabel("Number of Hands", fontsize=12)
    plt.legend(title="Hand Types", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.7)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig("hand_type_distribution.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_hand_strength_vs_bet():
    # Extract actions data
    actions_df = pd.DataFrame(data["actions"])

    # Create a hand rank mapping (higher number = stronger hand)
    hand_rank_map = {
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

    # Extract hand rank from hand_type (take first part before comma)
    actions_df["hand_rank"] = actions_df["hand_type"].apply(
        lambda x: hand_rank_map.get(x.split(",")[0].strip(), 0) if pd.notna(x) else 0
    )

    # Filter for actions with actual bets
    bet_actions = actions_df[actions_df["action_amount"].notna()]

    plt.figure(figsize=(12, 8))

    # Create scatter plot with different colors for each player
    for player in bet_actions["player"].unique():
        player_data = bet_actions[bet_actions["player"] == player]
        plt.scatter(
            player_data["hand_rank"],
            player_data["action_amount"],
            label=player,
            alpha=0.6,
            s=100,
        )

    plt.title("Hand Strength vs Bet Amount", fontsize=14, pad=20)
    plt.xlabel("Hand Strength", fontsize=12)
    plt.ylabel("Bet Amount", fontsize=12)

    # Set x-axis ticks to show hand types
    plt.xticks(
        range(1, 11),
        [
            "High Card",
            "One Pair",
            "Two Pair",
            "Three Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four Kind",
            "Straight Flush",
            "Royal Flush",
        ],
        rotation=45,
    )

    plt.legend(title="Players", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig("hand_strength_vs_bet.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_roi_analysis():
    # Extract round outcomes data
    outcomes = pd.DataFrame(data["round_outcomes"])

    plt.figure(figsize=(12, 8))

    # Create scatter plot with different colors for each player
    for player in outcomes["player"].unique():
        player_data = outcomes[outcomes["player"] == player]

        # Calculate size of points based on pot size (normalized)
        sizes = (player_data["pot_size"] / player_data["pot_size"].max() * 300) + 50

        plt.scatter(
            player_data["amount_risked"],
            player_data["roi"],
            label=player,
            alpha=0.6,
            s=sizes,
        )

    plt.title("ROI vs Amount Risked", fontsize=14, pad=20)
    plt.xlabel("Amount Risked", fontsize=12)
    plt.ylabel("ROI (%)", fontsize=12)

    # Add a horizontal line at ROI = 0
    plt.axhline(y=0, color="black", linestyle="--", alpha=0.3)

    plt.legend(
        title="Players\n(Point size = Pot size)",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
    )
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig("roi_analysis.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_position_action_heatmap():
    # Extract position stats data
    position_df = pd.DataFrame(data["position_stats"])

    # Create a pivot table for the heatmap
    # First, calculate total actions for each position
    position_df["total_actions"] = (
        1  # Each row represents one position-round combination
    )

    # Create pivot table
    heatmap_data = pd.pivot_table(
        position_df,
        values="total_actions",
        index="position",
        columns="player",
        aggfunc="sum",
        fill_value=0,
    )

    # Create the plot
    plt.figure(figsize=(10, 6))

    # Create heatmap
    sns.heatmap(
        heatmap_data,
        annot=True,  # Show numbers in cells
        fmt="g",  # Format as general number
        cmap="YlOrRd",  # Yellow to Orange to Red color scheme
        cbar_kws={"label": "Number of Actions"},
    )

    plt.title("Action Frequency by Position and Player", fontsize=14, pad=20)
    plt.xlabel("Player", fontsize=12)
    plt.ylabel("Position", fontsize=12)

    plt.tight_layout()
    plt.savefig("position_action_heatmap.png", bbox_inches="tight", dpi=300)
    plt.close()


def create_bet_position_heatmap():
    # Extract actions data
    actions_df = pd.DataFrame(data["actions"])

    # Filter for actions with actual bets
    bet_actions = actions_df[actions_df["action_amount"].notna()]

    # Calculate average bet size for each round and position
    avg_bets = pd.pivot_table(
        bet_actions,
        values="action_amount",
        index="round_number",
        columns="player",
        aggfunc="mean",
        fill_value=0,
    )

    # Create the plot
    plt.figure(figsize=(12, 8))

    # Create heatmap
    sns.heatmap(
        avg_bets,
        annot=True,  # Show numbers in cells
        fmt=".0f",  # Format as integer
        cmap="YlOrRd",  # Yellow to Orange to Red color scheme
        cbar_kws={"label": "Average Bet Size"},
    )

    plt.title("Average Bet Size by Round and Player", fontsize=14, pad=20)
    plt.xlabel("Player", fontsize=12)
    plt.ylabel("Round Number", fontsize=12)

    plt.tight_layout()
    plt.savefig("bet_position_heatmap.png", bbox_inches="tight", dpi=300)
    plt.close()


if __name__ == "__main__":
    create_chip_stack_evolution()
    create_cumulative_profit_loss()
    create_bet_size_distribution()
    create_action_frequency()
    create_hand_type_distribution()
    create_hand_strength_vs_bet()
    create_roi_analysis()
    create_position_action_heatmap()
    create_bet_position_heatmap()
