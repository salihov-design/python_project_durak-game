from __future__ import annotations

import random
from typing import List, Optional

from .cards import SUITS, Card, card_from_list, card_to_list, make_deck

HUMAN = 0
BOT = 1
NAMES = {HUMAN: "Вы", BOT: "Бот"}

HAND_SIZE = 6
MAX_ATTACKS = 6


class IllegalMove(Exception):
    pass


class Pair:
    __slots__ = ("attack", "defense")

    def __init__(self, attack: Card) -> None:
        self.attack = attack
        self.defense: Optional[Card] = None


class Game:
    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()
        self.deck: List[Card] = make_deck()
        self.rng.shuffle(self.deck)
        self.trump_card: Card = self.deck[0]
        self.trump: str = self.trump_card.suit

        self.hands: List[List[Card]] = [[], []]
        for _ in range(HAND_SIZE):
            for player in (HUMAN, BOT):
                self.hands[player].append(self.deck.pop())

        self.table: List[Pair] = []
        self.discard: List[Card] = []
        self.taking = False
        self.manual_bito = False
        self.bito_called = False
        self.result: Optional[str] = None
        self.last_event = ""

        self.attacker = self._first_attacker()
        self._sort_hands()

    def _first_attacker(self) -> int:
        best = None
        for player in (HUMAN, BOT):
            for card in self.hands[player]:
                if card.suit == self.trump and (best is None or card.rank < best[1]):
                    best = (player, card.rank)
        if best is not None:
            self.last_event = f"{NAMES[best[0]]}: младший козырь, первый ход"
            return best[0]
        first = self.rng.choice((HUMAN, BOT))
        self.last_event = f"Козырей нет, первый ход по жребию: {NAMES[first]}"
        return first

    def _sort_hands(self) -> None:
        def key(card: Card):
            return (card.suit == self.trump, SUITS.index(card.suit), card.rank)

        for hand in self.hands:
            hand.sort(key=key)

    @property
    def defender(self) -> int:
        return 1 - self.attacker

    @property
    def over(self) -> bool:
        return self.result is not None

    def unbeaten(self) -> List[Pair]:
        return [pair for pair in self.table if pair.defense is None]

    def table_ranks(self) -> set:
        ranks = set()
        for pair in self.table:
            ranks.add(pair.attack.rank)
            if pair.defense is not None:
                ranks.add(pair.defense.rank)
        return ranks

    def beats(self, defense: Card, attack: Card) -> bool:
        if defense.suit == attack.suit:
            return defense.rank > attack.rank
        return defense.suit == self.trump

    def turn(self) -> Optional[int]:
        if self.over:
            return None
        if self.taking:
            return self.attacker
        if self.unbeaten() or self.bito_called:
            return self.defender
        return self.attacker

    def legal_attacks(self) -> List[Card]:
        if self.over or self.turn() != self.attacker:
            return []
        hand = self.hands[self.attacker]
        if not self.table:
            return list(hand)
        if len(self.table) >= MAX_ATTACKS:
            return []
        if len(self.unbeaten()) >= len(self.hands[self.defender]):
            return []
        ranks = self.table_ranks()
        return [card for card in hand if card.rank in ranks]

    def legal_defends(self) -> List[Card]:
        if self.over or self.taking or self.bito_called or self.turn() != self.defender:
            return []
        attack = self.unbeaten()[0].attack
        return [card for card in self.hands[self.defender] if self.beats(card, attack)]

    def attack(self, card: Card) -> None:
        if self.over or self.turn() != self.attacker:
            raise IllegalMove("Сейчас не ход атакующего")
        if card not in self.legal_attacks():
            if self.table:
                raise IllegalMove("Подкидывать можно только карты тех же достоинств, что на столе")
            raise IllegalMove("Этой картой нельзя ходить")
        player = self.attacker
        self.hands[player].remove(card)
        self.table.append(Pair(card))
        self.last_event = f"{NAMES[player]}: ход {card}"
        self._after_action()

    def defend(self, card: Card) -> None:
        if self.over or self.turn() != self.defender or self.taking or self.bito_called:
            raise IllegalMove("Сейчас не ход защитника")
        if card not in self.legal_defends():
            raise IllegalMove("Эта карта не бьёт")
        pair = self.unbeaten()[0]
        player = self.defender
        self.hands[player].remove(card)
        pair.defense = card
        self.last_event = f"{NAMES[player]}: {card} бьёт {pair.attack}"
        self._after_action()

    def take(self) -> None:
        if self.over or self.taking or self.bito_called or self.turn() != self.defender:
            raise IllegalMove("Сейчас нельзя взять карты")
        self.taking = True
        self.last_event = f"{NAMES[self.defender]}: беру"
        self._after_action()

    def finish(self) -> None:
        if self.over or self.turn() != self.attacker or not self.table:
            raise IllegalMove("Сейчас нельзя завершить раунд")
        self._call_bito()

    def confirm_bito(self) -> None:
        if self.over or not self.bito_called or self.turn() != self.defender:
            raise IllegalMove("Сейчас нельзя отправить карты в бито")
        self._end_round()

    def _after_action(self) -> None:
        if self.over:
            return
        if self.turn() == self.attacker and self.table and not self.legal_attacks():
            self._call_bito()

    def _call_bito(self) -> None:
        if self.manual_bito and self.defender == HUMAN and not self.taking:
            self.bito_called = True
            self.last_event = f"{NAMES[self.defender]}: отбились, подтвердите «Бито»"
            return
        self._end_round()

    def _end_round(self) -> None:
        attacker, defender = self.attacker, self.defender
        cards: List[Card] = []
        for pair in self.table:
            cards.append(pair.attack)
            if pair.defense is not None:
                cards.append(pair.defense)

        if self.taking:
            self.hands[defender].extend(cards)
            self.last_event = f"{NAMES[defender]}: взято карт — {len(cards)}"
        else:
            self.discard.extend(cards)
            self.attacker = defender
            self.last_event = "Бито"

        self.table = []
        self.taking = False
        self.bito_called = False

        for player in (attacker, defender):
            hand = self.hands[player]
            while len(hand) < HAND_SIZE and self.deck:
                hand.append(self.deck.pop())

        self._sort_hands()
        self._check_over()

    def to_dict(self) -> dict:
        return {
            "trump": self.trump,
            "trump_card": card_to_list(self.trump_card),
            "deck": [card_to_list(c) for c in self.deck],
            "hands": [[card_to_list(c) for c in hand] for hand in self.hands],
            "table": [
                [card_to_list(p.attack), card_to_list(p.defense) if p.defense is not None else None]
                for p in self.table
            ],
            "discard": [card_to_list(c) for c in self.discard],
            "attacker": self.attacker,
            "taking": self.taking,
            "result": self.result,
            "last_event": self.last_event,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Game":
        game = cls.__new__(cls)
        game.rng = random.Random()
        game.trump = data["trump"]
        game.trump_card = card_from_list(data["trump_card"])
        game.deck = [card_from_list(c) for c in data["deck"]]
        game.hands = [[card_from_list(c) for c in hand] for hand in data["hands"]]
        game.table = []
        for attack, defense in data["table"]:
            pair = Pair(card_from_list(attack))
            if defense is not None:
                pair.defense = card_from_list(defense)
            game.table.append(pair)
        game.discard = [card_from_list(c) for c in data["discard"]]
        game.attacker = data["attacker"]
        game.taking = data["taking"]
        game.manual_bito = False
        game.bito_called = False
        game.result = data["result"]
        game.last_event = data["last_event"]
        return game

    def _check_over(self) -> None:
        if self.deck:
            return
        human_empty = not self.hands[HUMAN]
        bot_empty = not self.hands[BOT]
        if human_empty and bot_empty:
            self.result = "draw"
        elif human_empty:
            self.result = "human"
        elif bot_empty:
            self.result = "bot"
