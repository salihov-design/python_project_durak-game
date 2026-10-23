from __future__ import annotations

from dataclasses import dataclass
from typing import List

SUITS = ("♠", "♥", "♦", "♣")
RANKS = tuple(range(6, 15))

_RANK_LABELS = {11: "В", 12: "Д", 13: "К", 14: "Т"}


@dataclass(frozen=True)
class Card:
    suit: str
    rank: int

    @property
    def rank_label(self) -> str:
        return _RANK_LABELS.get(self.rank, str(self.rank))

    @property
    def is_red(self) -> bool:
        return self.suit in ("♥", "♦")

    def __str__(self) -> str:
        return f"{self.rank_label}{self.suit}"


def make_deck() -> List[Card]:
    return [Card(suit, rank) for suit in SUITS for rank in RANKS]


def card_to_list(card: Card) -> list:
    return [card.suit, card.rank]


def card_from_list(data) -> Card:
    suit, rank = data
    return Card(str(suit), int(rank))
