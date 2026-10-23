from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Tuple

from .bot import DIFFICULTIES, NORMAL
from .engine import Game

SAVE_PATH = Path.home() / ".durak_save.json"


def has_save() -> bool:
    return SAVE_PATH.exists()


def save_game(game: Game, difficulty: str) -> None:
    data = {"version": 1, "difficulty": difficulty, "game": game.to_dict()}
    tmp = SAVE_PATH.with_name(SAVE_PATH.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, SAVE_PATH)
    except OSError:
        pass


def load_game() -> Optional[Tuple[Game, str]]:
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        difficulty = data.get("difficulty", NORMAL)
        if difficulty not in DIFFICULTIES:
            difficulty = NORMAL
        game = Game.from_dict(data["game"])
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None
    if game.over:
        return None
    return game, difficulty


def clear_save() -> None:
    try:
        SAVE_PATH.unlink()
    except OSError:
        pass
