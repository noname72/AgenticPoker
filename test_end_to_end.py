"""
Below is one possible approach for building an end-to-end test that collects logs from a simulation run and validates the resulting gameplay sequence. The heart of this approach is to run your simulation in a controlled environment, capture all logs (or structured data produced by your logging system), and then parse and compare them to expected outcomes. The comparison can be as strict or as permissive as you like (e.g., exact string matches vs. partial or pattern-based matches).

────────────────────────────────────────────────────────────────────────
1) Decide on a log data format
────────────────────────────────────────────────────────────────────────
• You can use unstructured text logs, as shown in your example. Then you'd parse them (e.g., by regex or line-by-line checks) to verify correctness.  
• Another option is to log in JSON or some structured format. This makes it easier to parse out fields (like pot sizes, chip stacks, actions).

────────────────────────────────────────────────────────────────────────
2) Expose a hook or function to run a "test simulation"
────────────────────────────────────────────────────────────────────────
• If you already have main.py or some other entry point that runs a poker game, add an option or environment variable that says "run in test mode and dump logs to a file" (or return them as a string in memory).  
• Alternatively, from your test code, you can directly call the classes/functions that simulate the game, intercepting the logs via a custom logger.

────────────────────────────────────────────────────────────────────────
3) Capture logs during the run
────────────────────────────────────────────────────────────────────────
• Python's logging library can be configured in many ways. For a test, you can attach a custom handler that stores log records in a list:  
  – For example, a StringIO-based handler or a custom class that appends all log lines to a list in memory.  
• Once the simulation completes, you'll have a full transcript of what happened.

────────────────────────────────────────────────────────────────────────
4) Parse the captured logs and compare to expected values
────────────────────────────────────────────────────────────────────────
• The simplest approach is to store an "expected outcome" text file (or JSON file) in your repo and compare the newly produced logs to that file.  
• You could do a line-by-line match, diff, or more advanced partial checking (such as ignoring dynamic random values like suit distributions if needed).

Notes on this approach:  
• run_simulation(test_mode=True, seed=12345) is just an example. Your game might let you pass in test arguments to make the run deterministic (so pot amounts, card deals, etc. are known in advance).  
• We attach our ListHandler to the root logger. If your game uses a specialized logger (e.g., logging.getLogger("myPokerGame")), then you should attach to that logger instead.  
• We simply turn all captured records into one big string. You can parse line by line if you'd prefer.  

────────────────────────────────────────────────────────────────────────
6) Comparing final state or partial values
────────────────────────────────────────────────────────────────────────
Instead of text logs, you might want to:  
• Expose final game state objects (like each player's final chip stack, final pot sizes, and so on). You can do direct comparisons to an expected state.  
• If you need partial validation—for example, "we only care that the pot was ≥ 600 but ≤ 610"—then parse that out.  

────────────────────────────────────────────────────────────────────────
7) Handling randomness
────────────────────────────────────────────────────────────────────────
Poker is inherently random, but for testing, we usually fix the seed. Ensure that:  
• Your deck and any random decisions use a known seed so that "Alice gets the same initial hand" each run.  
• That way, the logs remain consistent across runs.  

────────────────────────────────────────────────────────────────────────
8) Summary
────────────────────────────────────────────────────────────────────────
1. Decide how to log your game (text vs. JSON).  
2. Provide an easy way to run a single simulation or multiple rounds in "test mode."  
3. Capture the logs with a custom logging handler (or store them in your code directly).  
4. Parse and compare to your expected logs (or partial checks).  
5. Run as part of your CI pipeline or local tests.

This should let you verify end-to-end that the betting sequences, pot sizes, and actions match the logic you expect. If anything slips out of spec (like a pot calculation error or players skipping turns), the test will fail and you'll be able to inspect the logs to see how it diverged.

"""

import io
import logging
import unittest
from unittest.mock import patch

from game.game import AgenticPoker
from config import GameConfig
from game.agents import Agent, RandomAgent
from agents.agent import Agent
from agents.random_agent import RandomAgent



class ListHandler(logging.Handler):
    """
    Logging handler that stores log messages in a list for analysis.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


class EndToEndTestCase(unittest.TestCase):
    def setUp(self):
        # Prepare a custom log handler
        self.log_handler = ListHandler()
        self.log_handler.setLevel(logging.DEBUG)

        # Store original handlers
        self.logger = logging.getLogger()
        self.original_handlers = self.logger.handlers[:]
        self.logger.handlers = [self.log_handler]

        # Create players
        self.players = [
            Agent(
                "Alice",
                chips=1000,
                strategy_style="Aggressive Bluffer",
                use_reasoning=True,
                use_reflection=True,
                use_planning=True,
                use_opponent_modeling=True,
                session_id="test_session",
            ),
            Agent(
                "Bob",
                chips=1000,
                strategy_style="Calculated and Cautious",
                use_reasoning=True,
                use_reflection=False,
                use_planning=False,
                use_opponent_modeling=True,
                session_id="test_session",
            ),
            Agent(
                "Charlie",
                chips=1000,
                strategy_style="Chaotic and Unpredictable",
                use_reasoning=False,
                use_reflection=False,
                use_planning=False,
                use_opponent_modeling=False,
                session_id="test_session",
            ),
            RandomAgent(
                "Randy",
                chips=1000,
            ),
        ]

        # Create game config
        config = GameConfig(
            starting_chips=1000,
            small_blind=50,
            big_blind=100,
            ante=10,
            session_id="test_session",
            max_raise_multiplier=3,
            max_raises_per_round=4,
            min_bet=100,
        )

        # Create game instance with players and config
        self.game = AgenticPoker(self.players, config=config)

    def tearDown(self):
        """Clean up after each test."""
        # Restore original handlers
        self.logger.handlers = self.original_handlers

        # Clean up AI agents
        if hasattr(self, 'game') and self.game.table:
            for player in self.game.table.players:
                if hasattr(player, "memory"):
                    player.memory = None
                if hasattr(player, "current_plan"):
                    player.current_plan = None

    def test_game_flow(self):
        """Test a single round of poker gameplay."""
        # Run one round of the game
        self.game.play_game(max_rounds=1)

        # Get all logs
        all_logs = "\n".join(self.log_handler.records)

        # Print logs for debugging
        print("\nCaptured Logs:")
        print("=" * 50)
        for log in self.log_handler.records:
            print(log)
        print("=" * 50)

        # Basic game flow checks
        self.assertTrue(
            any("Alice" in log for log in self.log_handler.records),
            "Should see actions from Alice",
        )
        self.assertTrue(
            any("Bob" in log for log in self.log_handler.records),
            "Should see actions from Bob",
        )

        # Verify basic game state
        self.assertIsNotNone(self.game.table, "Game should have a table")
        self.assertTrue(len(self.game.table.players) > 0, "Should have players")

        # More specific betting checks
        betting_actions = [
            log
            for log in self.log_handler.records
            if any(
                action in log
                for action in [
                    "executes: FOLD",
                    "executes: CALL",
                    "executes: RAISE",
                    "posts ante",
                    "posts small blind",
                    "posts big blind",
                ]
            )
        ]

        print("\nFound Betting Actions:")
        for action in betting_actions:
            print(f"- {action}")

        # Verify betting occurred with more specific checks
        self.assertTrue(
            any("Collecting antes" in log for log in self.log_handler.records),
            "Should see ante collection",
        )
        self.assertTrue(
            any("posts small blind" in log for log in self.log_handler.records),
            "Should see small blind placement",
        )
        self.assertTrue(
            any("posts big blind" in log for log in self.log_handler.records),
            "Should see big blind placement",
        )
        self.assertTrue(
            any(
                "executes: FOLD" in log
                or "executes: CALL" in log
                or "executes: RAISE" in log
                for log in self.log_handler.records
            ),
            "Should see betting actions in logs",
        )

        # Verify game phases
        self.assertTrue(
            any(
                "====== Pre-draw betting ======" in log
                for log in self.log_handler.records
            ),
            "Should see pre-draw betting phase",
        )
        self.assertTrue(
            any("====== Draw Phase ======" in log for log in self.log_handler.records),
            "Should see draw phase",
        )
        self.assertTrue(
            any(
                "====== Post-draw betting ======" in log
                for log in self.log_handler.records
            ),
            "Should see post-draw betting phase",
        )
        self.assertTrue(
            any("====== Showdown ======" in log for log in self.log_handler.records),
            "Should see showdown phase",
        )

        # Verify hand evaluation
        self.assertTrue(
            any("hand:" in log.lower() for log in self.log_handler.records),
            "Should see hand evaluations",
        )

        # Verify winner determination
        self.assertTrue(
            any("wins $" in log for log in self.log_handler.records),
            "Should see pot being awarded to winner",
        )

        # Verify game completion
        self.assertTrue(
            any("Game ended" in log for log in self.log_handler.records),
            "Game should end after max rounds",
        )
        self.assertTrue(
            any("Final Standings:" in log for log in self.log_handler.records),
            "Should see final standings",
        )

        # Verify player positions
        self.assertTrue(
            any("Dealer: Alice" in log for log in self.log_handler.records),
            "Should see dealer position",
        )
        self.assertTrue(
            any("Small Blind: Bob" in log for log in self.log_handler.records),
            "Should see small blind position",
        )
        self.assertTrue(
            any("Big Blind: Charlie" in log for log in self.log_handler.records),
            "Should see big blind position",
        )

        # Verify hand evaluations and rankings
        self.assertTrue(
            any("High Card" in log for log in self.log_handler.records)
            or any("One Pair" in log for log in self.log_handler.records)
            or any("Two Pair" in log for log in self.log_handler.records)
            or any("Three of a Kind" in log for log in self.log_handler.records),
            "Should see poker hand rankings",
        )

        # Verify chip tracking
        self.assertTrue(
            any("Starting stacks" in log for log in self.log_handler.records),
            "Should see initial chip counts",
        )
        self.assertTrue(
            any(
                "Final Standings" in log and "$" in log
                for log in self.log_handler.records
            ),
            "Should see final chip counts",
        )

        # Verify deck management
        self.assertTrue(
            any("Cards remaining" in log for log in self.log_handler.records),
            "Should track remaining cards",
        )
        self.assertTrue(
            any(
                "Draw phase" in log and "discarding" in log
                for log in self.log_handler.records
            ),
            "Should see card discards during draw phase",
        )

        # Verify betting structure
        self.assertTrue(
            any(
                all(
                    term in log
                    for term in ["small blind", "big blind", "ante", "minimum bet"]
                )
                for log in self.log_handler.records
            ),
            "Should see complete betting structure",
        )

        # Verify active player tracking
        self.assertTrue(
            any("Active players:" in log for log in self.log_handler.records),
            "Should track active players",
        )

        # Verify strategy logging (for AI players)
        self.assertTrue(
            any(
                "[Strategy]" in log or "[Action]" in log
                for log in self.log_handler.records
            ),
            "Should see AI strategy decisions",
        )


if __name__ == "__main__":
    unittest.main()
