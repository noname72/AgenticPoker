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
from game.config import GameConfig
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
    @classmethod
    def setUpClass(cls):
        """Run once before all tests to set up shared game state."""
        # Prepare a custom log handler
        cls.log_handler = ListHandler()
        cls.log_handler.setLevel(logging.DEBUG)

        # Store original handlers
        cls.logger = logging.getLogger()
        cls.original_handlers = cls.logger.handlers[:]
        cls.logger.handlers = [cls.log_handler]

        # Create players
        cls.players = [
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

        # Create game config with non-zero ante
        config = GameConfig(
            starting_chips=1000,
            small_blind=10,
            big_blind=20,
            ante=5,  # Add a non-zero ante
            min_bet=20,
        )

        # Create and run game instance
        cls.game = AgenticPoker(cls.players, config=config)
        cls.game.play_game(max_rounds=1)

        # Print logs for debugging
        print("\nCaptured Logs:")
        print("=" * 50)
        for log in cls.log_handler.records:
            print(log)
        print("=" * 50)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Restore original handlers
        cls.logger.handlers = cls.original_handlers

        # Clean up AI agents
        if hasattr(cls, "game") and cls.game.table:
            for player in cls.game.table.players:
                if hasattr(player, "memory"):
                    player.memory = None
                if hasattr(player, "current_plan"):
                    player.current_plan = None

    def test_basic_game_flow(self):
        """Test basic game flow and player actions.

        Assumptions:
        - At least two players (Alice and Bob) participate in the game
        - The game table is properly initialized
        - Players remain in the game until at least one action is taken
        """
        self.assertTrue(
            any("Alice" in log for log in self.log_handler.records),
            "Should see actions from Alice",
        )
        self.assertTrue(
            any("Bob" in log for log in self.log_handler.records),
            "Should see actions from Bob",
        )
        self.assertIsNotNone(self.game.table, "Game should have a table")
        self.assertTrue(len(self.game.table.players) > 0, "Should have players")

    def test_betting_actions(self):
        """Test betting actions and mandatory bets.

        Assumptions:
        - Game is configured with non-zero ante (5 chips)
        - Small blind (10 chips) and big blind (20 chips) are enforced
        - Players have enough chips to post mandatory bets
        - At least one betting action (FOLD/CALL/RAISE) occurs
        """
        self.assertTrue(
            any("posts ante" in log for log in self.log_handler.records)
            or any("Collecting antes" in log for log in self.log_handler.records),
            "Should see ante collection when ante > 0",
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

    def test_game_phases(self):
        """Test that all game phases occur in correct order.

        Assumptions:
        - Game always includes pre-draw betting phase
        - Draw phase and post-draw betting only occur if hand doesn't end early
        - Hand ends early if all but one player folds
        - Showdown phase always occurs (even with early winner)
        """
        self.assertTrue(
            any(
                "====== Pre-draw betting ======" in log
                for log in self.log_handler.records
            ),
            "Should see pre-draw betting phase",
        )

        hand_ended_early = (
            len(
                [
                    log
                    for log in self.log_handler.records
                    if "wins" in log and "all others folded" in log
                ]
            )
            > 0
        )

        if not hand_ended_early:
            self.assertTrue(
                any(
                    "====== Draw Phase ======" in log
                    for log in self.log_handler.records
                ),
                "Should see draw phase when hand doesn't end early",
            )
            self.assertTrue(
                any(
                    "====== Post-draw betting ======" in log
                    for log in self.log_handler.records
                ),
                "Should see post-draw betting phase when hand doesn't end early",
            )

        self.assertTrue(
            any("====== Showdown ======" in log for log in self.log_handler.records),
            "Should see showdown phase",
        )

    def test_hand_evaluation(self):
        """Test hand evaluation and winner determination.

        Assumptions:
        - Each player's hand is evaluated and logged
        - At least one player wins chips from the pot
        - Hand rankings are properly logged (High Card through Three of a Kind)
        - Winner determination is logged with amount won
        """
        self.assertTrue(
            any("hand:" in log.lower() for log in self.log_handler.records),
            "Should see hand evaluations",
        )
        self.assertTrue(
            any("wins $" in log for log in self.log_handler.records),
            "Should see pot being awarded to winner",
        )
        self.assertTrue(
            any("High Card" in log for log in self.log_handler.records)
            or any("One Pair" in log for log in self.log_handler.records)
            or any("Two Pair" in log for log in self.log_handler.records)
            or any("Three of a Kind" in log for log in self.log_handler.records),
            "Should see poker hand rankings",
        )

    def test_game_completion(self):
        """Test game completion and final standings.

        Assumptions:
        - Game ends after configured max_rounds (1)
        - Final standings are logged showing all players
        - Game state is properly cleaned up after completion
        """
        self.assertTrue(
            any("Game ended" in log for log in self.log_handler.records),
            "Game should end after max rounds",
        )
        self.assertTrue(
            any("Final Standings:" in log for log in self.log_handler.records),
            "Should see final standings",
        )

    def test_player_positions(self):
        """Test player positions and roles.

        Assumptions:
        - Players are in fixed positions for this test:
          * Alice is Dealer
          * Bob is Small Blind
          * Charlie is Big Blind
        - Position information is logged at start of hand
        """
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

    def test_chip_tracking(self):
        """Test chip tracking and accounting.

        Assumptions:
        - All players start with 1000 chips
        - Starting stacks are logged before betting
        - Final standings include chip counts in format "N. Name: $amount"
        - Chip totals remain constant (no chips created/destroyed)
        """
        self.assertTrue(
            any("Starting stacks" in log for log in self.log_handler.records),
            "Should see initial chip counts",
        )

        # Look for final standings with numbered entries and dollar amounts
        final_standings_found = False
        for log in self.log_handler.records:
            if "Final Standings:" in log:
                next_logs = self.log_handler.records[
                    self.log_handler.records.index(
                        log
                    ) : self.log_handler.records.index(log)
                    + 5
                ]
                if any(
                    log.strip().startswith(str(i)) and ": $" in log
                    for i in range(1, 5)
                    for log in next_logs
                ):
                    final_standings_found = True
                    break

        self.assertTrue(
            final_standings_found,
            "Should see final standings with numbered entries and chip counts",
        )

    def test_deck_management(self):
        """Test deck management and card dealing.

        Assumptions:
        - New deck is shuffled at start of hand
        - Card remaining count is logged
        - If hand doesn't end early:
          * Draw phase occurs with discards
          * Remaining cards are tracked after draws
        """
        self.assertTrue(
            any("Cards remaining" in log for log in self.log_handler.records),
            "Should track remaining cards",
        )

        hand_ended_early = (
            len(
                [
                    log
                    for log in self.log_handler.records
                    if "wins" in log and "all others folded" in log
                ]
            )
            > 0
        )

        if not hand_ended_early:
            self.assertTrue(
                any(
                    "Draw phase" in log and "discarding" in log
                    for log in self.log_handler.records
                ),
                "Should see card discards during draw phase",
            )

    def test_betting_structure(self):
        """Test betting structure configuration.

        Assumptions:
        - Game config includes:
          * Small blind: 10 chips
          * Big blind: 20 chips
          * Ante: 5 chips
          * Minimum bet: 20 chips
        - Betting structure is logged under "Betting structure:" header
        """
        # Look for the betting structure section and verify all components
        betting_structure_found = False
        for log in self.log_handler.records:
            if "Betting structure:" in log:
                next_logs = self.log_handler.records[
                    self.log_handler.records.index(
                        log
                    ) : self.log_handler.records.index(log)
                    + 5
                ]
                betting_structure_found = all(
                    any(f"{term}:" in line for line in next_logs)
                    for term in ["Small blind", "Big blind", "Ante", "Minimum bet"]
                )
                if betting_structure_found:
                    break

        self.assertTrue(
            betting_structure_found,
            "Should see complete betting structure with all components",
        )

    def test_player_tracking(self):
        """Test player tracking and AI strategy logging.

        Assumptions:
        - Active players are tracked and logged each betting round
        - AI players (Alice, Bob, Charlie) log their strategy decisions
        - AI players log their actions with reasoning
        - Random player (Randy) takes actions without strategy logging
        """
        self.assertTrue(
            any("Active players:" in log for log in self.log_handler.records),
            "Should track active players",
        )
        self.assertTrue(
            any(
                "[Strategy]" in log or "[Action]" in log
                for log in self.log_handler.records
            ),
            "Should see AI strategy decisions",
        )


if __name__ == "__main__":
    unittest.main()
