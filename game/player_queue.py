class PlayerQueue:
    def __init__(self, players):
        self.players = players
        self.index = 0

    def get_next_player(self):
        if not self.players:
            return None
        player = self.players[self.index]
        self.index = (self.index + 1) % len(self.players)
        return player

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
            if self.index >= len(self.players):
                self.index = 0

    def reset_queue(self):
        self.index = 0

    def is_round_complete(self):
        return all(player.folded or player.is_all_in for player in self.players)
