from __future__ import annotations

import random
from collections import Counter
from typing import List, Optional

from .cards import Card
from .engine import BOT, Game

EASY, NORMAL, HARD = "easy", "normal", "hard"
DIFFICULTIES = (EASY, NORMAL, HARD)
DIFFICULTY_NAMES = {EASY: "Лёгкий", NORMAL: "Обычный", HARD: "Сложный"}
MAX_THROWS = {EASY: 2, NORMAL: 4, HARD: 6}


class Bot:
    def __init__(self, player: int = BOT, difficulty: str = NORMAL,
                 rng: Optional[random.Random] = None) -> None:
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"неизвестный уровень: {difficulty}")
        self.player = player
        self.difficulty = difficulty
        self.rng = rng or random.Random()

    def act(self, game: Game) -> bool:
        if game.turn() != self.player:
            return False
        if self.player == game.attacker:
            self._attack(game)
        else:
            self._defend(game)
        return True

    @staticmethod
    def _value(game: Game, card: Card) -> int:
        return card.rank + (15 if card.suit == game.trump else 0)

    def _attack(self, game: Game) -> None:
        legal = game.legal_attacks()
        if not legal:
            game.finish()
            return
        if not game.table:
            game.attack(self._lead(game, legal))
            return
        if self._wants_more(game, legal):
            game.attack(self._pick_throw(game, legal))
        else:
            game.finish()

    def _lead(self, game: Game, legal: List[Card]) -> Card:
        if self.difficulty == EASY:
            return self.rng.choice(legal)
        counts = Counter(c.rank for c in game.hands[self.player])
        use_pairs = self.difficulty == HARD
        return min(legal, key=lambda c: (c.suit == game.trump, c.rank,
                                         -counts[c.rank] if use_pairs else 0))

    def _wants_more(self, game: Game, legal: List[Card]) -> bool:
        plain = [c for c in legal if c.suit != game.trump]
        if not plain:
            return False
        if game.taking:
            return True
        if self.difficulty == EASY and self.rng.random() < 0.5:
            return False
        return len(game.table) < MAX_THROWS[self.difficulty]

    def _pick_throw(self, game: Game, legal: List[Card]) -> Card:
        plain = [c for c in legal if c.suit != game.trump]
        return min(plain or legal, key=lambda c: self._value(game, c))

    def _defend(self, game: Game) -> None:
        options = game.legal_defends()
        if not options:
            game.take()
            return
        if self.difficulty == EASY:
            if self.rng.random() < 0.25:
                game.take()
            else:
                game.defend(self.rng.choice(options))
            return
        attack = game.unbeaten()[0].attack
        best = min(options, key=lambda c: self._value(game, c))
        if self._should_take(game, best, attack):
            game.take()
        else:
            game.defend(best)

    def _should_take(self, game: Game, best: Card, attack: Card) -> bool:
        if not game.deck:
            return False
        spends_trump = best.suit == game.trump and attack.suit != game.trump
        if not spends_trump or attack.rank > 10:
            return False
        if self.difficulty == NORMAL:
            return best.rank >= 11
        trumps_left = sum(1 for c in game.hands[self.player] if c.suit == game.trump)
        return trumps_left <= 1
