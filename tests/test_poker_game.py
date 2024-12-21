import unittest
from unittest.mock import Mock, patch
import logging

from poker_game import PokerGame, GameConfig, PlayerConfig, PokerAction, GameStateError

class TestPokerGame(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        logging.disable(logging.CRITICAL)
        self.game = PokerGame()

    def tearDown(self):
        """Clean up after each test method."""
        logging.disable(logging.NOTSET)

    def test_game_initialization(self):
        """Test game initialization."""
        self.assertIsInstance(self.game.game_config, GameConfig)
        self.assertEqual(len(self.game.agents), 2)
        self.assertEqual(len(self.game.player_configs), 2)
        self.assertIn("GPT_Agent_1", self.game.agents)
        self.assertIn("GPT_Agent_2", self.game.agents)

    @patch('poker_game.NoLimitTexasHoldem')
    def test_handle_fold(self, mock_holdem):
        """Test fold action handling."""
        mock_table = Mock()
        mock_agent = Mock()
        
        self.game._handle_fold(mock_table, mock_agent)
        
        mock_table.fold.assert_called_once()

    @patch('poker_game.NoLimitTexasHoldem')
    def test_handle_call(self, mock_holdem):
        """Test call action handling."""
        mock_table = Mock()
        mock_table.street.min_completion_betting_or_raising_amount = 0
        mock_agent = Mock()
        
        self.game._handle_call(mock_table, mock_agent)
        
        mock_table.check_or_call.assert_called_once()

    @patch('poker_game.NoLimitTexasHoldem')
    def test_handle_raise(self, mock_holdem):
        """Test raise action handling."""
        mock_table = Mock()
        mock_table.can_complete_bet_or_raise_to.return_value = True
        mock_table.street.min_completion_betting_or_raising_amount = 100
        mock_table.bets = [50, 50]
        mock_agent = Mock()
        
        self.game._handle_raise(mock_table, mock_agent)
        
        mock_table.complete_bet_or_raise_to.assert_called_once()

    def test_fallback_action_selection(self):
        """Test fallback action selection logic."""
        mock_table = Mock()
        mock_table.can_check_or_call.return_value = True
        mock_table.can_complete_bet_or_raise_to.return_value = True
        mock_agent = Mock()

        # Test betting error fallback
        self.game._handle_fallback_action(mock_table, mock_agent, "Betting error")
        mock_table.fold.assert_called_once()

        # Reset mocks
        mock_table.reset_mock()

        # Test other error fallback (should use weighted random)
        with patch('random.choices') as mock_choices:
            mock_choices.return_value = [PokerAction.CALL]
            self.game._handle_fallback_action(mock_table, mock_agent, "Other error")
            mock_table.check_or_call.assert_called_once()

if __name__ == '__main__':
    unittest.main() 