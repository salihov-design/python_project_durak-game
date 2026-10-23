from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import pygame

from .cards import Card

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cards")
_SUIT_ORDER = {"♣": 0, "♥": 1, "♦": 2, "♠": 3}


def card_file(card: Card) -> str:
    return f"{_SUIT_ORDER[card.suit] * 9 + (card.rank - 6):02d}.png"


class Sprites:
    def __init__(self, size: Tuple[int, int]) -> None:
        self.size = size
        self._cache: Dict[str, Optional[pygame.Surface]] = {}

    def _load(self, name: str) -> Optional[pygame.Surface]:
        if name not in self._cache:
            path = os.path.join(ASSET_DIR, name)
            surf = None
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                surf = pygame.transform.smoothscale(img, self.size)
            self._cache[name] = surf
        return self._cache[name]

    def card(self, card: Card) -> Optional[pygame.Surface]:
        return self._load(card_file(card))

    def back(self) -> Optional[pygame.Surface]:
        return self._load("back.png")
