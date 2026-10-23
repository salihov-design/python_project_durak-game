import random
import unittest

from durak.cards import Card
from durak.engine import BOT, HUMAN, Game, IllegalMove


def make_game(human, bot, deck=(), trump="♠", attacker=HUMAN):
    g = Game(random.Random(1))
    g.hands = [list(human), list(bot)]
    g.deck = list(deck)
    g.trump = trump
    g.trump_card = Card(trump, 6)
    g.table = []
    g.discard = []
    g.taking = False
    g.result = None
    g.attacker = attacker
    return g


class SetupTests(unittest.TestCase):
    def test_initial_deal(self):
        g = Game(random.Random(5))
        self.assertEqual(len(g.hands[HUMAN]), 6)
        self.assertEqual(len(g.hands[BOT]), 6)
        self.assertEqual(len(g.deck), 24)
        self.assertEqual(g.trump, g.trump_card.suit)

    def test_beats(self):
        g = make_game([], [], trump="♠")
        self.assertTrue(g.beats(Card("♦", 9), Card("♦", 7)))
        self.assertFalse(g.beats(Card("♦", 7), Card("♦", 9)))
        self.assertTrue(g.beats(Card("♠", 6), Card("♦", 14)))
        self.assertFalse(g.beats(Card("♥", 14), Card("♦", 6)))
        self.assertFalse(g.beats(Card("♦", 14), Card("♠", 6)))
        self.assertTrue(g.beats(Card("♠", 10), Card("♠", 9)))


class RoundTests(unittest.TestCase):
    def test_attack_defend_finish_swaps_roles(self):
        g = make_game([Card("♦", 7), Card("♣", 9)], [Card("♦", 9), Card("♥", 6)])
        g.attack(Card("♦", 7))
        self.assertEqual(g.turn(), BOT)
        g.defend(Card("♦", 9))
        self.assertEqual(g.turn(), HUMAN)
        g.finish()
        self.assertEqual(g.attacker, BOT)
        self.assertEqual(len(g.discard), 2)
        self.assertEqual(g.table, [])

    def test_take_and_throw_in(self):
        g = make_game(
            [Card("♦", 7), Card("♣", 7), Card("♥", 12)],
            [Card("♥", 6), Card("♥", 8), Card("♣", 9)],
        )
        g.attack(Card("♦", 7))
        g.take()
        self.assertEqual(g.turn(), HUMAN)
        self.assertEqual(g.legal_attacks(), [Card("♣", 7)])
        g.attack(Card("♣", 7))
        self.assertEqual(g.table, [])
        self.assertEqual(len(g.hands[BOT]), 5)
        self.assertEqual(g.attacker, HUMAN)

    def test_attack_limit_by_defender_hand(self):
        g = make_game(
            [Card("♦", 7), Card("♣", 7), Card("♥", 7)],
            [Card("♥", 6), Card("♥", 8)],
        )
        g.attack(Card("♦", 7))
        g.take()
        g.attack(Card("♣", 7))
        self.assertEqual(g.table, [])
        self.assertEqual(len(g.hands[BOT]), 4)

    def test_illegal_moves(self):
        g = make_game([Card("♦", 7)], [Card("♦", 6), Card("♣", 9)])
        with self.assertRaises(IllegalMove):
            g.defend(Card("♦", 6))
        g.attack(Card("♦", 7))
        with self.assertRaises(IllegalMove):
            g.defend(Card("♦", 6))
        with self.assertRaises(IllegalMove):
            g.attack(Card("♦", 7))

    def test_cannot_finish_with_empty_table(self):
        g = make_game([Card("♦", 7)], [Card("♦", 9)])
        with self.assertRaises(IllegalMove):
            g.finish()

    def test_refill_attacker_first(self):
        deck = [Card("♣", 14), Card("♣", 13)]
        g = make_game(
            [Card("♦", 7), Card("♥", 6), Card("♥", 7), Card("♥", 8), Card("♥", 9), Card("♥", 10)],
            [Card("♦", 9), Card("♣", 6), Card("♣", 7), Card("♣", 8), Card("♣", 9), Card("♣", 10)],
            deck=deck,
        )
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        g.finish()
        self.assertIn(Card("♣", 13), g.hands[HUMAN])
        self.assertIn(Card("♣", 14), g.hands[BOT])


class ManualBitoTests(unittest.TestCase):
    def test_human_defender_must_confirm_bito(self):
        g = make_game([Card("♦", 9), Card("♣", 6)], [Card("♦", 7), Card("♥", 8)],
                      deck=[Card("♣", 10)] * 4, attacker=BOT)
        g.manual_bito = True
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        self.assertTrue(g.bito_called)
        self.assertEqual(len(g.table), 1)
        self.assertEqual(g.turn(), HUMAN)
        with self.assertRaises(IllegalMove):
            g.take()
        g.confirm_bito()
        self.assertEqual(g.table, [])
        self.assertEqual(g.attacker, HUMAN)
        self.assertFalse(g.bito_called)

    def test_bot_finish_waits_for_human(self):
        g = make_game([Card("♦", 9), Card("♣", 6)], [Card("♦", 7), Card("♥", 7)],
                      deck=[Card("♣", 10)] * 4, attacker=BOT)
        g.manual_bito = True
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        g.finish()
        self.assertTrue(g.bito_called)
        self.assertEqual(len(g.discard), 0)

    def test_human_attacker_closes_round_without_confirmation(self):
        g = make_game([Card("♦", 7), Card("♣", 9)], [Card("♦", 9), Card("♥", 6)],
                      deck=[Card("♣", 10)] * 4, attacker=HUMAN)
        g.manual_bito = True
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        g.finish()
        self.assertEqual(g.attacker, BOT)
        self.assertEqual(len(g.discard), 2)


class EndgameTests(unittest.TestCase):
    def test_draw(self):
        g = make_game([Card("♦", 7)], [Card("♦", 9)])
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        self.assertEqual(g.result, "draw")

    def test_attacker_wins_when_defender_takes(self):
        g = make_game([Card("♦", 7)], [Card("♥", 9), Card("♥", 10)])
        g.attack(Card("♦", 7))
        g.take()
        self.assertEqual(g.result, "human")

    def test_defender_wins_after_beating_last(self):
        g = make_game([Card("♦", 7), Card("♣", 8)], [Card("♦", 9)])
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        self.assertEqual(g.result, "bot")

    def test_no_result_while_deck_not_empty(self):
        g = make_game([Card("♦", 7)], [Card("♦", 9)], deck=[Card("♣", 6)] * 20)
        g.attack(Card("♦", 7))
        g.defend(Card("♦", 9))
        self.assertIsNone(g.result)


if __name__ == "__main__":
    unittest.main()
