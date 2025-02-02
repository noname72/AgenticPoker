from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats


def analyze_action_frequencies(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze the frequency and distribution of player actions.

    Returns DataFrame with columns:
    - player
    - total_actions
    - raise_count
    - call_count
    - fold_count
    - raise_percentage
    - aggression_ratio (raises / (calls + folds))
    """
    actions_df = data["actions"]

    # Group by player and action type
    action_counts = (
        actions_df.groupby("player")["action_type"].value_counts().unstack(fill_value=0)
    )

    # Calculate total actions and percentages
    results = []
    for player in action_counts.index:
        total_actions = action_counts.loc[player].sum()
        raise_count = action_counts.loc[player].get("raise", 0)
        call_count = action_counts.loc[player].get("call", 0)
        fold_count = action_counts.loc[player].get("fold", 0)

        # Calculate percentages and ratios
        raise_percentage = (
            (raise_count / total_actions * 100) if total_actions > 0 else 0
        )
        aggression_ratio = (
            raise_count / (call_count + fold_count)
            if (call_count + fold_count) > 0
            else np.inf
        )

        results.append(
            {
                "player": player,
                "total_actions": total_actions,
                "raise_count": raise_count,
                "call_count": call_count,
                "fold_count": fold_count,
                "raise_percentage": round(raise_percentage, 2),
                "aggression_ratio": round(aggression_ratio, 2),
            }
        )

    return pd.DataFrame(results)


def analyze_betting_patterns(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze betting amounts and patterns for each player.

    Returns DataFrame with columns:
    - player
    - avg_bet_size
    - median_bet_size
    - max_bet_size
    - avg_bet_to_pot_ratio
    - total_amount_bet
    """
    actions_df = data["actions"]

    # Filter for actions with actual bets
    betting_actions = actions_df[actions_df["action_amount"].notna()]

    results = []
    for player in actions_df["player"].unique():
        player_bets = betting_actions[betting_actions["player"] == player]

        if len(player_bets) > 0:
            results.append(
                {
                    "player": player,
                    "avg_bet_size": round(player_bets["action_amount"].mean(), 2),
                    "median_bet_size": round(player_bets["action_amount"].median(), 2),
                    "max_bet_size": player_bets["action_amount"].max(),
                    "avg_bet_to_pot_ratio": round(
                        player_bets["action_amount"].sum()
                        / player_bets["pot_size"].sum(),
                        3,
                    ),
                    "total_amount_bet": player_bets["action_amount"].sum(),
                }
            )
        else:
            results.append(
                {
                    "player": player,
                    "avg_bet_size": 0,
                    "median_bet_size": 0,
                    "max_bet_size": 0,
                    "avg_bet_to_pot_ratio": 0,
                    "total_amount_bet": 0,
                }
            )

    return pd.DataFrame(results)


def analyze_hand_distributions(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze the distribution of hand types and their relationship with betting behavior.

    Returns DataFrame with columns:
    - player
    - hand_type
    - count
    - win_rate
    - avg_bet_size
    - avg_pot_size
    """
    hands_df = data["hand_distributions"]
    actions_df = data["actions"]

    # Merge hands with actions to get betting information
    merged_df = pd.merge(
        hands_df,
        actions_df[["player", "round_number", "phase", "action_amount", "pot_size"]],
        on=["player", "round_number", "phase"],
        how="left",
    )

    results = []
    for player in hands_df["player"].unique():
        player_hands = merged_df[merged_df["player"] == player]

        for hand_type in player_hands["hand_type"].unique():
            hand_instances = player_hands[player_hands["hand_type"] == hand_type]

            results.append(
                {
                    "player": player,
                    "hand_type": hand_type,
                    "count": len(hand_instances),
                    "win_rate": round(hand_instances["won_hand"].mean() * 100, 2),
                    "avg_bet_size": round(hand_instances["action_amount"].mean(), 2),
                    "avg_pot_size": round(hand_instances["pot_size"].mean(), 2),
                }
            )

    return pd.DataFrame(results)


def analyze_player_performance(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze overall player performance metrics.

    Returns DataFrame with columns:
    - player
    - total_hands_played
    - hands_won
    - win_rate
    - profit_loss
    - avg_roi
    - largest_pot_won
    """
    player_stats = data["player_stats"]
    outcomes = data["round_outcomes"]

    results = []
    for player in player_stats["player"].unique():
        player_outcomes = outcomes[outcomes["player"] == player]
        player_data = player_stats[player_stats["player"] == player].iloc[0]

        results.append(
            {
                "player": player,
                "total_hands_played": player_data["total_hands_played"],
                "hands_won": player_data["hands_won"],
                "win_rate": round(
                    player_data["hands_won"] / player_data["total_hands_played"] * 100,
                    2,
                ),
                "profit_loss": player_data["total_profit_loss"],
                "avg_roi": round(player_outcomes["roi"].mean(), 2),
                "largest_pot_won": player_data["largest_pot_won"],
            }
        )

    return pd.DataFrame(results)


def analyze_win_rates(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze detailed win rates and profitability metrics for each player.

    Returns DataFrame with columns:
    - player
    - overall_win_rate
    - avg_profit_per_round
    - profit_variance
    - survival_round
    """
    rounds_df = data["rounds"]
    outcomes_df = data["round_outcomes"]
    eliminations_df = data["elimination_stats"]

    results = []
    for player in outcomes_df["player"].unique():
        player_outcomes = outcomes_df[outcomes_df["player"] == player]
        player_elim = eliminations_df[eliminations_df["player"] == player].iloc[0]

        # Calculate overall win rate
        total_rounds = len(player_outcomes)
        wins = len(player_outcomes[player_outcomes["is_winner"]])

        results.append(
            {
                "player": player,
                "overall_win_rate": round(
                    (wins / total_rounds * 100) if total_rounds > 0 else 0,
                    2,
                ),
                "avg_profit_per_round": round(player_outcomes["chip_change"].mean(), 2),
                "profit_variance": round(player_outcomes["chip_change"].var(), 2),
                "survival_round": player_elim["elimination_round"] or len(rounds_df),
            }
        )

    return pd.DataFrame(results)


def analyze_roi_metrics(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze return on investment metrics for different betting actions.

    Returns DataFrame with columns:
    - player
    - overall_roi
    - raise_roi
    - call_roi
    - risk_reward_ratio
    """
    outcomes_df = data["round_outcomes"]
    actions_df = data["actions"]

    results = []
    for player in outcomes_df["player"].unique():
        player_outcomes = outcomes_df[outcomes_df["player"] == player]

        # Calculate overall ROI
        overall_roi = player_outcomes["roi"].mean()

        # Calculate ROI by action type using round number to match actions with outcomes
        player_actions = actions_df[actions_df["player"] == player]

        # Join actions with outcomes to get ROI for each action type
        merged_df = pd.merge(
            player_actions,
            player_outcomes[["round_number", "roi"]],
            on="round_number",
            how="left",
        )

        raise_roi = merged_df[merged_df["action_type"] == "raise"]["roi"].mean()
        call_roi = merged_df[merged_df["action_type"] == "call"]["roi"].mean()

        # Calculate risk-reward ratio (total winnings / total losses)
        wins = player_outcomes[player_outcomes["chip_change"] > 0]["chip_change"].sum()
        losses = abs(
            player_outcomes[player_outcomes["chip_change"] < 0]["chip_change"].sum()
        )

        results.append(
            {
                "player": player,
                "overall_roi": round(overall_roi if not pd.isna(overall_roi) else 0, 2),
                "raise_roi": round(raise_roi if not pd.isna(raise_roi) else 0, 2),
                "call_roi": round(call_roi if not pd.isna(call_roi) else 0, 2),
                "risk_reward_ratio": round(wins / losses if losses > 0 else np.inf, 2),
            }
        )

    return pd.DataFrame(results)


def analyze_elimination_patterns(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze patterns in player eliminations and their correlation with playing style.

    Returns DataFrame with columns:
    - player
    - elimination_round
    - final_rank
    - avg_aggression_pre_elimination
    - avg_stack_percentage
    - big_blind_rounds_remaining
    """
    eliminations_df = data["elimination_stats"]
    actions_df = data["actions"]
    trajectories_df = data["trajectories"]

    results = []
    for player in eliminations_df["player"].unique():
        player_elim = eliminations_df[eliminations_df["player"] == player].iloc[0]
        player_actions = actions_df[actions_df["player"] == player]
        player_trajectory = trajectories_df[trajectories_df["player"] == player]

        # Calculate pre-elimination metrics
        elim_round = player_elim["elimination_round"]
        if elim_round:
            pre_elim_actions = player_actions[
                player_actions["round_number"] < elim_round
            ]
            pre_elim_trajectory = player_trajectory[
                player_trajectory["round_number"] < elim_round
            ]
        else:
            pre_elim_actions = player_actions
            pre_elim_trajectory = player_trajectory

        # Calculate average aggression (raises / total actions)
        total_actions = len(pre_elim_actions)
        raise_actions = len(
            pre_elim_actions[pre_elim_actions["action_type"] == "raise"]
        )

        # Calculate average stack as percentage of total chips in play
        if len(pre_elim_trajectory) > 0:
            avg_stack_pct = (
                pre_elim_trajectory["chips"].mean()
                / pre_elim_trajectory.groupby("round_number")["chips"]
                .transform("sum")
                .mean()
                * 100
            )

            # Get final stack from the last row
            final_stack = pre_elim_trajectory.iloc[-1]["chips"]
        else:
            avg_stack_pct = 0
            final_stack = 0

        # Estimate how many rounds until player would be blinded out
        big_blind_amount = 100  # This should be fetched from game config
        big_blind_rounds = final_stack / big_blind_amount if final_stack > 0 else 0

        results.append(
            {
                "player": player,
                "elimination_round": elim_round,
                "final_rank": player_elim["final_rank"],
                "avg_aggression_pre_elimination": round(
                    raise_actions / total_actions * 100 if total_actions > 0 else 0, 2
                ),
                "avg_stack_percentage": round(avg_stack_pct, 2),
                "big_blind_rounds_remaining": round(big_blind_rounds, 1),
            }
        )

    return pd.DataFrame(results)


def analyze_aggressiveness_index(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate various aggressiveness metrics for each player.

    Returns DataFrame with columns:
    - player
    - raise_to_action_ratio
    - avg_raise_to_stack
    - continuation_bet_frequency
    - avg_raise_size
    - steal_attempt_rate
    """
    actions_df = data["actions"]
    trajectories_df = data["trajectories"]

    results = []
    for player in actions_df["player"].unique():
        player_actions = actions_df[actions_df["player"] == player]
        player_trajectory = trajectories_df[trajectories_df["player"] == player]

        # Calculate basic action counts
        total_actions = len(player_actions)
        raise_actions = len(player_actions[player_actions["action_type"] == "raise"])

        # Get raise amounts and corresponding stack sizes
        raise_moves = player_actions[player_actions["action_type"] == "raise"]
        if len(raise_moves) > 0:
            avg_raise = raise_moves["action_amount"].mean()
            # Match raises with player's stack size at the time
            raise_stacks = pd.merge(
                raise_moves[["round_number", "action_amount"]],
                player_trajectory[["round_number", "chips"]],
                on="round_number",
                how="left",
            )
            avg_raise_to_stack = (
                raise_stacks["action_amount"] / raise_stacks["chips"]
            ).mean() * 100
        else:
            avg_raise = 0
            avg_raise_to_stack = 0

        # Calculate steal attempt rate (raises when in late position)
        late_position_raises = len(
            player_actions[
                (player_actions["action_type"] == "raise")
                & (player_actions["current_bet"] <= 100)  # Only initial betting rounds
            ]
        )
        total_opportunities = len(player_actions[player_actions["current_bet"] <= 100])

        results.append(
            {
                "player": player,
                "raise_to_action_ratio": round(
                    raise_actions / total_actions if total_actions > 0 else 0, 3
                ),
                "avg_raise_to_stack": round(avg_raise_to_stack, 2),
                "avg_raise_size": round(avg_raise, 2),
                "steal_attempt_rate": round(
                    (
                        late_position_raises / total_opportunities
                        if total_opportunities > 0
                        else 0
                    ),
                    3,
                ),
            }
        )

    return pd.DataFrame(results)


def analyze_positional_impact(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze how position affects player behavior and outcomes.

    Returns DataFrame with columns:
    - player
    - position
    - win_rate
    - avg_profit
    - raise_frequency
    - avg_bet_size
    """
    position_stats = data["position_stats"]

    results = []
    for player in position_stats["player"].unique():
        player_positions = position_stats[position_stats["player"] == player]

        for position in ["dealer", "small_blind", "big_blind"]:
            position_data = player_positions[player_positions["position"] == position]

            if len(position_data) > 0:
                results.append(
                    {
                        "player": player,
                        "position": position,
                        "win_rate": round(position_data["won_round"].mean() * 100, 2),
                        "avg_profit": round(position_data["chip_change"].mean(), 2),
                        "hands_played": len(position_data),
                        "avg_stack_percentage": round(
                            position_data["initial_stack"].mean()
                            / position_data["num_players"].mean()
                            / 1000
                            * 100,  # Assuming 1000 starting stack
                            2,
                        ),
                    }
                )

    return pd.DataFrame(results)


def analyze_chip_trajectory(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze how players' chip stacks change over time.

    Returns DataFrame with columns:
    - player
    - max_stack_achieved
    - min_stack_achieved
    - avg_stack_growth_rate
    - volatility
    - recovery_rate
    - time_to_peak
    """
    trajectories_df = data["trajectories"]

    results = []
    for player in trajectories_df["player"].unique():
        player_trajectory = trajectories_df[trajectories_df["player"] == player]

        # Sort by round number to analyze progression
        player_trajectory = player_trajectory.sort_values("round_number")

        # Calculate stack changes
        stack_changes = player_trajectory["chips"].diff()

        # Calculate metrics
        max_stack = player_trajectory["chips"].max()
        min_stack = player_trajectory["chips"].min()

        # Calculate average rate of stack change per round
        avg_growth_rate = stack_changes.mean()

        # Calculate volatility (standard deviation of stack changes)
        volatility = stack_changes.std()

        # Find time to reach peak stack
        time_to_peak = player_trajectory[player_trajectory["chips"] == max_stack][
            "round_number"
        ].iloc[0]

        # Calculate recovery rate (average positive change after losses)
        recovery_rate = stack_changes[stack_changes > 0].mean()

        results.append(
            {
                "player": player,
                "max_stack_achieved": round(max_stack, 2),
                "min_stack_achieved": round(min_stack, 2),
                "avg_stack_growth_rate": round(avg_growth_rate, 2),
                "volatility": round(volatility, 2),
                "recovery_rate": round(
                    recovery_rate if not pd.isna(recovery_rate) else 0, 2
                ),
                "time_to_peak": round(time_to_peak, 1),
            }
        )

    return pd.DataFrame(results)


def analyze_statistical_significance(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Perform statistical tests to analyze significant differences between players.

    Returns DataFrame with columns:
    - comparison
    - metric
    - test_type
    - statistic
    - p_value
    - significant
    """
    actions_df = data["actions"]
    outcomes_df = data["round_outcomes"]
    players = actions_df["player"].unique()

    results = []

    # Helper function for running tests
    def run_test(data1, data2, metric_name, test_type="t-test"):
        if len(data1) < 2 or len(data2) < 2:
            return None, None

        if test_type == "t-test":
            statistic, p_value = stats.ttest_ind(data1, data2, nan_policy="omit")
        elif test_type == "mann_whitney":
            statistic, p_value = stats.mannwhitneyu(
                data1, data2, alternative="two-sided"
            )

        return statistic, p_value

    # Compare metrics between each pair of players
    for i, player1 in enumerate(players):
        for player2 in players[i + 1 :]:
            # Test bet sizes
            p1_bets = actions_df[
                (actions_df["player"] == player1)
                & (actions_df["action_amount"].notna())
            ]["action_amount"]
            p2_bets = actions_df[
                (actions_df["player"] == player2)
                & (actions_df["action_amount"].notna())
            ]["action_amount"]

            stat, p_val = run_test(p1_bets, p2_bets, "bet_sizes")
            if stat is not None:
                results.append(
                    {
                        "comparison": f"{player1} vs {player2}",
                        "metric": "bet_sizes",
                        "test_type": "mann_whitney",
                        "statistic": round(stat, 3),
                        "p_value": round(p_val, 3),
                        "significant": p_val < 0.05,
                    }
                )

            # Test ROI
            p1_roi = outcomes_df[outcomes_df["player"] == player1]["roi"]
            p2_roi = outcomes_df[outcomes_df["player"] == player2]["roi"]

            stat, p_val = run_test(p1_roi, p2_roi, "roi")
            if stat is not None:
                results.append(
                    {
                        "comparison": f"{player1} vs {player2}",
                        "metric": "roi",
                        "test_type": "t-test",
                        "statistic": round(stat, 3),
                        "p_value": round(p_val, 3),
                        "significant": p_val < 0.05,
                    }
                )

            # Test chip changes
            p1_chips = outcomes_df[outcomes_df["player"] == player1]["chip_change"]
            p2_chips = outcomes_df[outcomes_df["player"] == player2]["chip_change"]

            stat, p_val = run_test(p1_chips, p2_chips, "chip_changes")
            if stat is not None:
                results.append(
                    {
                        "comparison": f"{player1} vs {player2}",
                        "metric": "chip_changes",
                        "test_type": "t-test",
                        "statistic": round(stat, 3),
                        "p_value": round(p_val, 3),
                        "significant": p_val < 0.05,
                    }
                )

    return pd.DataFrame(results)


def analyze_correlations(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Analyze correlations between various game metrics.

    Returns DataFrame with columns:
    - variable_1
    - variable_2
    - correlation
    - p_value
    - sample_size
    """
    # Combine relevant metrics from different DataFrames
    actions_df = data["actions"]
    outcomes_df = data["round_outcomes"]

    # Create a merged DataFrame for correlation analysis
    merged_df = pd.merge(
        actions_df,
        outcomes_df[["player", "round_number", "chip_change", "roi"]],
        on=["player", "round_number"],
        how="left",
    )

    # Variables to analyze (using only available columns)
    variables = {
        "action_amount": "Bet Size",
        "pot_size": "Pot Size",
        "chips_before": "Starting Stack",
        "chip_change": "Chip Change",
        "roi": "ROI",
    }

    results = []

    # Calculate correlations between all pairs of variables
    for var1 in variables:
        for var2 in variables:
            if var1 >= var2:  # Avoid duplicate comparisons
                continue

            # Get non-null values for both variables
            mask = merged_df[[var1, var2]].notna().all(axis=1)
            data1 = merged_df[mask][var1]
            data2 = merged_df[mask][var2]

            if len(data1) > 1:  # Need at least 2 points for correlation
                correlation, p_value = stats.pearsonr(data1, data2)

                results.append(
                    {
                        "variable_1": variables[var1],
                        "variable_2": variables[var2],
                        "correlation": round(correlation, 3),
                        "p_value": round(p_value, 3),
                        "sample_size": len(data1),
                    }
                )

    return pd.DataFrame(results)


def analyze_player_clusters(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Perform cluster analysis on player behaviors and strategies.

    Returns Dict containing:
    - feature_matrix: DataFrame of normalized player features
    - clusters: DataFrame of cluster assignments and characteristics
    - cluster_performance: DataFrame of performance metrics by cluster
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    # Collect features for clustering
    actions_df = data["actions"]
    outcomes_df = data["round_outcomes"]
    player_stats = data["player_stats"]

    # Create feature matrix
    features = []
    for player in player_stats["player"].unique():
        player_actions = actions_df[actions_df["player"] == player]
        player_outcomes = outcomes_df[outcomes_df["player"] == player]

        # Calculate features
        total_actions = len(player_actions)
        raise_actions = len(player_actions[player_actions["action_type"] == "raise"])
        call_actions = len(player_actions[player_actions["action_type"] == "call"])

        # Betting behavior features
        betting_actions = player_actions[player_actions["action_amount"].notna()]
        avg_bet = (
            betting_actions["action_amount"].mean() if len(betting_actions) > 0 else 0
        )
        bet_to_pot = (
            (betting_actions["action_amount"] / betting_actions["pot_size"]).mean()
            if len(betting_actions) > 0
            else 0
        )

        # Performance features
        win_rate = len(player_outcomes[player_outcomes["is_winner"]]) / len(
            player_outcomes
        )
        avg_roi = player_outcomes["roi"].mean()

        features.append(
            {
                "player": player,
                "aggression_ratio": (
                    raise_actions / total_actions if total_actions > 0 else 0
                ),
                "call_frequency": (
                    call_actions / total_actions if total_actions > 0 else 0
                ),
                "avg_bet_size": avg_bet,
                "avg_bet_to_pot": bet_to_pot,
                "win_rate": win_rate,
                "avg_roi": avg_roi,
            }
        )

    feature_df = pd.DataFrame(features)
    player_names = feature_df["player"]

    # Normalize features
    scaler = StandardScaler()
    feature_matrix = scaler.fit_transform(feature_df.drop("player", axis=1))
    feature_matrix = pd.DataFrame(
        feature_matrix, columns=feature_df.columns[1:], index=player_names
    )

    # For small datasets, use fixed number of clusters
    n_players = len(player_names)
    if n_players <= 3:
        best_k = 2
    else:
        best_k = min(3, n_players - 1)

    # Perform clustering
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(feature_matrix)

    # Create cluster profile DataFrame
    cluster_profiles = []
    for i in range(best_k):
        cluster_mask = clusters == i
        cluster_features = feature_matrix[cluster_mask]

        profile = {
            "cluster": i,
            "size": sum(cluster_mask),
            "avg_aggression": cluster_features["aggression_ratio"].mean(),
            "avg_bet_size": cluster_features["avg_bet_size"].mean(),
            "avg_win_rate": cluster_features["win_rate"].mean(),
            "avg_roi": cluster_features["avg_roi"].mean(),
            "players": ", ".join(player_names[cluster_mask]),
        }

        # Determine cluster style based on features
        if profile["avg_aggression"] > 0.4:
            style = "Aggressive"
        elif profile["avg_aggression"] < 0.2:
            style = "Passive"
        else:
            style = "Balanced"

        if profile["avg_roi"] > 0.5:
            style += " (Profitable)"
        elif profile["avg_roi"] < -0.5:
            style += " (Unprofitable)"

        profile["playing_style"] = style
        cluster_profiles.append(profile)

    # Analyze cluster performance
    cluster_performance = []
    for i in range(best_k):
        cluster_players = set(player_names[clusters == i])
        cluster_outcomes = outcomes_df[outcomes_df["player"].isin(cluster_players)]

        performance = {
            "cluster": i,
            "avg_profit_per_round": round(cluster_outcomes["chip_change"].mean(), 2),
            "win_rate": round(
                len(cluster_outcomes[cluster_outcomes["is_winner"]])
                / len(cluster_outcomes)
                * 100,
                2,
            ),
            "avg_roi": round(cluster_outcomes["roi"].mean(), 2),
            "survival_rate": round(
                sum(
                    1
                    for p in cluster_players
                    if data["elimination_stats"][
                        data["elimination_stats"]["player"] == p
                    ]["elimination_round"].iloc[0]
                    is None
                )
                / len(cluster_players)
                * 100,
                2,
            ),
        }
        cluster_performance.append(performance)

    return {
        "feature_matrix": feature_matrix,
        "clusters": pd.DataFrame(cluster_profiles),
        "cluster_performance": pd.DataFrame(cluster_performance),
    }


def generate_analysis_report(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Generate a comprehensive analysis report containing all metrics.
    """
    report = {
        "action_frequencies": analyze_action_frequencies(data),
        "betting_patterns": analyze_betting_patterns(data),
        "hand_distributions": analyze_hand_distributions(data),
        "player_performance": analyze_player_performance(data),
        "win_rates": analyze_win_rates(data),
        "roi_metrics": analyze_roi_metrics(data),
        "elimination_patterns": analyze_elimination_patterns(data),
        "aggressiveness_index": analyze_aggressiveness_index(data),
        "positional_impact": analyze_positional_impact(data),
        "chip_trajectory": analyze_chip_trajectory(data),
        "statistical_tests": analyze_statistical_significance(data),
        "correlations": analyze_correlations(data),
    }

    # Add clustering analysis
    clustering_results = analyze_player_clusters(data)
    report.update(
        {
            "player_features": clustering_results["feature_matrix"],
            "player_clusters": clustering_results["clusters"],
            "cluster_performance": clustering_results["cluster_performance"],
        }
    )

    return report


if __name__ == "__main__":
    # Load the transformed game data
    with open("transformed_game.json", "r") as f:
        import json

        game_data = json.load(f)

    # Convert JSON data to DataFrames
    data = {key: pd.DataFrame(value) for key, value in game_data.items()}

    # Generate analysis report
    report = generate_analysis_report(data)

    # Convert all DataFrames in the report to dictionaries/lists for JSON serialization
    json_report = {}
    for key, df in report.items():
        # Convert DataFrame to records
        records = df.to_dict(orient="records")

        # Replace non-JSON-serializable values
        for record in records:
            for k, v in record.items():
                if pd.isna(v):
                    record[k] = None
                elif v == float("inf") or v == float("-inf"):
                    record[k] = None
                elif isinstance(v, float) and np.isinf(v):
                    record[k] = None

        json_report[key] = records

    # Save to JSON file
    with open("analysis_report.json", "w") as f:
        json.dump(json_report, f, indent=2)
