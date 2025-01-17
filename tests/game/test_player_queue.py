import pytest
from game.player_queue import PlayerQueue
from game.player import Player


@pytest.fixture
def players():
    return [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]


def test_player_queue_initialization(players):
    queue = PlayerQueue(players)
    assert queue.players == players
    assert queue.index == 0


def test_get_next_player(players):
    queue = PlayerQueue(players)
    assert queue.get_next_player() == players[0]
    assert queue.get_next_player() == players[1]
    assert queue.get_next_player() == players[2]
    assert queue.get_next_player() == players[0]  # Circular order


def test_remove_player(players):
    queue = PlayerQueue(players)
    queue.remove_player(players[1])
    assert players[1] not in queue.players
    assert queue.get_next_player() == players[0]
    assert queue.get_next_player() == players[2]
    assert queue.get_next_player() == players[0]  # Circular order


def test_reset_queue(players):
    queue = PlayerQueue(players)
    queue.get_next_player()
    queue.get_next_player()
    queue.reset_queue()
    assert queue.index == 0
    assert queue.get_next_player() == players[0]


def test_is_round_complete(players):
    queue = PlayerQueue(players)
    assert not queue.is_round_complete()
    players[0].folded = True
    players[1].is_all_in = True
    assert queue.is_round_complete()
