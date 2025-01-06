import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import graphviz


class PhaseType(Enum):
    """Types of phases in the poker game."""

    BETTING = "betting"
    DEALING = "dealing"
    DECISION = "decision"
    EVALUATION = "evaluation"
    COLLECTION = "collection"


@dataclass
class Node:
    """Enhanced node representation with validation rules."""

    id: str
    label: str
    phase_type: PhaseType
    description: Optional[str] = None
    valid_actions: List[str] = field(default_factory=list)
    min_players: int = 2
    max_players: int = 10
    timeout_seconds: Optional[int] = None

    def validate(self) -> bool:
        """Validate node configuration."""
        return True


class GameFlowMetrics:
    """Collect and analyze game flow metrics."""

    def __init__(self):
        self.phase_durations: Dict[str, List[float]] = {}
        self.transition_counts: Dict[tuple, int] = {}
        self.player_actions: Dict[str, Dict[str, int]] = {}

    def record_phase_duration(self, phase_id: str, duration: float) -> None:
        """Record the duration of a phase."""
        if phase_id not in self.phase_durations:
            self.phase_durations[phase_id] = []
        self.phase_durations[phase_id].append(duration)

    def record_transition(self, from_phase: str, to_phase: str) -> None:
        """Record a phase transition."""
        key = (from_phase, to_phase)
        self.transition_counts[key] = self.transition_counts.get(key, 0) + 1


class GameFlowVisualizer:
    """Visualizes the poker game flow as a directed graph."""

    def __init__(self):
        self.dot = graphviz.Digraph(comment="Poker Game Flow")
        self.setup_styling()
        self.metrics = GameFlowMetrics()
        self.nodes = {}  # Store nodes for reference

    def setup_styling(self) -> None:
        """Configure the graph styling."""
        self.dot.attr(rankdir="LR")

        # Define node styling for different phase types
        self.style_configs = {
            PhaseType.BETTING: {
                "shape": "rectangle",
                "style": "filled",
                "fillcolor": "lightblue",
                "color": "navy",
            },
            PhaseType.DEALING: {
                "shape": "diamond",
                "style": "filled",
                "fillcolor": "lightgreen",
                "color": "darkgreen",
            },
            PhaseType.DECISION: {
                "shape": "ellipse",
                "style": "filled",
                "fillcolor": "lightyellow",
                "color": "orange",
            },
            PhaseType.EVALUATION: {
                "shape": "hexagon",
                "style": "filled",
                "fillcolor": "lightpink",
                "color": "red",
            },
            PhaseType.COLLECTION: {
                "shape": "rectangle",
                "style": "filled,rounded",
                "fillcolor": "lightgrey",
                "color": "darkgrey",
            },
        }

    def create_game_flow(self) -> None:
        """Create the complete game flow graph with phase clusters."""
        # Set main graph attributes
        self.dot.attr(compound="true")
        self.dot.attr(ranksep="0.75")  # Increase vertical spacing
        self.dot.attr(nodesep="0.5")  # Increase horizontal spacing

        # Store nodes for edge creation
        self.nodes = {}

        # Create a subgraph for the main game flow
        with self.dot.subgraph(name="cluster_main") as main:
            # Create clusters for each major phase
            with self.dot.subgraph(name="cluster_pre_draw") as pre_draw:
                pre_draw.attr(label="Pre-Draw Phase", style="rounded", color="navy")
                # Add pre-draw nodes
                pre_draw_nodes = {
                    "ante": Node("ante", "Post Ante", PhaseType.COLLECTION),
                    "blinds": Node("blinds", "Post Blinds", PhaseType.COLLECTION),
                    "deal_initial": Node(
                        "deal_initial", "Deal Initial Cards", PhaseType.DEALING
                    ),
                    "pre_draw_betting": Node(
                        "pre_draw_betting", "Pre-Draw Betting", PhaseType.BETTING
                    ),
                }
                for node in pre_draw_nodes.values():
                    self.add_node(node)
                    self.nodes[node.id] = node

            with self.dot.subgraph(name="cluster_draw") as draw:
                draw.attr(label="Draw Phase", style="rounded", color="darkgreen")
                # Add draw phase nodes
                draw_nodes = {
                    "discard": Node("discard", "Discard Cards", PhaseType.DECISION),
                    "draw": Node("draw", "Draw New Cards", PhaseType.DEALING),
                }
                for node in draw_nodes.values():
                    self.add_node(node)
                    self.nodes[node.id] = node

            with self.dot.subgraph(name="cluster_post_draw") as post_draw:
                post_draw.attr(label="Post-Draw Phase", style="rounded", color="navy")
                # Add post-draw nodes
                post_draw_nodes = {
                    "post_draw_betting": Node(
                        "post_draw_betting", "Post-Draw Betting", PhaseType.BETTING
                    )
                }
                for node in post_draw_nodes.values():
                    self.add_node(node)
                    self.nodes[node.id] = node

            with self.dot.subgraph(name="cluster_showdown") as showdown:
                showdown.attr(label="Showdown Phase", style="rounded", color="darkred")
                # Add showdown nodes
                showdown_nodes = {
                    "reveal": Node("reveal", "Reveal Hands", PhaseType.EVALUATION),
                    "evaluate": Node(
                        "evaluate", "Evaluate Hands", PhaseType.EVALUATION
                    ),
                    "distribute": Node(
                        "distribute", "Distribute Pot", PhaseType.COLLECTION
                    ),
                }
                for node in showdown_nodes.values():
                    self.add_node(node)
                    self.nodes[node.id] = node

        # Add betting actions (legend) at the top
        self.add_betting_actions("pre_draw_betting")

        # Define edges between nodes
        edges = [
            ("ante", "blinds"),
            ("blinds", "deal_initial"),
            ("deal_initial", "pre_draw_betting"),
            ("pre_draw_betting", "discard"),
            ("discard", "draw"),
            ("draw", "post_draw_betting"),
            ("post_draw_betting", "reveal"),
            ("reveal", "evaluate"),
            ("evaluate", "distribute"),
        ]

        # Add all edges to the graph
        for start, end in edges:
            self.add_edge(start, end)

        # Add conditional transitions
        self.add_state_transitions()

    def add_node(self, node: Node) -> None:
        """Add a node with tooltip and hover information."""
        style = self.style_configs[node.phase_type]
        self.dot.node(
            node.id,
            node.label,
            tooltip=node.description or node.label,
            href=f"#{node.id}",  # Enable clickable nodes
            **style,
        )
        if node.description:
            self.dot.node(f"{node.id}_desc", node.description, shape="note")
            self.dot.edge(node.id, f"{node.id}_desc", style="dotted")

    def add_edge(self, start_id: str, end_id: str, label: str = "", **attrs) -> None:
        """Add an edge between nodes with optional styling attributes.

        Args:
            start_id: ID of the starting node
            end_id: ID of the ending node
            label: Optional label for the edge
            **attrs: Additional graphviz edge attributes (color, style, etc.)
        """
        self.dot.edge(start_id, end_id, label, **attrs)

    def add_betting_actions(self, parent_id: str) -> None:
        """Add available player actions for betting phases."""
        # Only add actions legend for pre-draw betting (to avoid duplication)
        if parent_id == "pre_draw_betting":
            actions = ["Check", "Bet", "Call", "Raise", "Fold"]
            with self.dot.subgraph(name="cluster_actions") as s:
                s.attr(label="Available Actions", style="dotted")
                # Set rank direction to LR for horizontal layout
                s.attr(rankdir="LR")

                # Create nodes in a horizontal line
                prev_action = None
                for action in actions:
                    node_id = f"action_{action.lower()}"
                    s.node(node_id, action, shape="ellipse")
                    if prev_action:
                        # Add invisible edge to force horizontal layout
                        s.edge(prev_action, node_id, style="invis")
                    prev_action = node_id

                # Force same rank for all action nodes
                s.attr(rank="same")

    def add_state_transitions(self) -> None:
        """Add conditional transitions between states."""
        transitions = {
            "pre_draw_betting": {
                "all_fold": ("distribute", "red", "All players fold"),
                "all_call": ("discard", "blue", "All players call"),
                "timeout": ("distribute", "red", "Time limit reached"),
            },
            "post_draw_betting": {
                "all_fold": ("distribute", "red", "All players fold"),
                "all_call": ("reveal", "blue", "All players call"),
                "timeout": ("reveal", "red", "Time limit reached"),
            },
        }

        for state, conditions in transitions.items():
            for condition, (target, color, tooltip) in conditions.items():
                self.add_edge(
                    state,
                    target,
                    label=condition,
                    color=color,
                    style="dashed",
                    penwidth="2.0",
                    fontsize="10",
                    tooltip=tooltip,
                )

    def render(self, filename: str = "poker_game_flow", format: str = "png") -> None:
        """Render the graph to a file."""
        self.dot.render(filename, format=format, cleanup=True)

    def export_configuration(self, filepath: Path) -> None:
        """Export the current graph configuration to JSON."""
        config = {
            "nodes": {
                node.id: {
                    "label": node.label,
                    "phase_type": node.phase_type.value,
                    "description": node.description,
                    "valid_actions": node.valid_actions,
                }
                for node in self.nodes.values()
            },
            "edges": self.edges,
            "style_configs": {k.value: v for k, v in self.style_configs.items()},
        }

        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def from_configuration(cls, filepath: Path) -> "GameFlowVisualizer":
        """Create a new visualizer from a configuration file."""
        with open(filepath) as f:
            config = json.load(f)

        visualizer = cls()
        # Load configuration...
        return visualizer


class InteractiveGameFlow(GameFlowVisualizer):
    """Interactive version of the game flow visualizer."""

    def __init__(self, update_interval: float = 1.0):
        super().__init__()
        self.update_interval = update_interval
        self.active_phase: Optional[str] = None

    def highlight_active_phase(self, phase_id: str) -> None:
        """Highlight the currently active phase."""
        if self.active_phase:
            # Reset previous highlight
            self.update_node_style(self.active_phase)

        # Highlight new active phase
        self.active_phase = phase_id
        self.update_node_style(phase_id, style={"penwidth": "3.0", "color": "gold"})

    def update_node_style(self, node_id: str, style: Optional[Dict] = None) -> None:
        """Update the style of a node."""
        node = self.nodes[node_id]
        new_style = {**self.style_configs[node.phase_type]}
        if style:
            new_style.update(style)
        self.dot.node(node_id, node.label, **new_style)


def generate_game_flow_diagram() -> None:
    """Generate and save the game flow diagram."""
    visualizer = GameFlowVisualizer()
    visualizer.create_game_flow()
    visualizer.render("poker_game_flow")


if __name__ == "__main__":
    generate_game_flow_diagram()
