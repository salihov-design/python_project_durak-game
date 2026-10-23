import random
import unittest

from durak.bot import DIFFICULTIES, Bot
from durak.cards import Card
from durak.engine import BOT, HUMAN, Game


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


class BotSimulationTests(unittest.TestCase):
    def test_all_difficulties_finish_games_and_keep_cards(self):
        for difficulty in DIFFICULTIES:
            for seed in range(150):
                game = Game(random.Random(seed))
                human = Bot(HUMAN, "normal", random.Random(seed))
                bot = Bot(BOT, difficulty, random.Random(seed))
                steps = 0
                while not game.over:
                    acted = human.act(game) or bot.act(game)
                    self.assertTrue(acted, f"{difficulty}/{seed}: партия зависла")
                    steps += 1
                    self.assertLess(steps, 3000, f"{difficulty}/{seed}: слишком долго")
                    total = (len(game.deck) + len(game.hands[HUMAN]) + len(game.hands[BOT])
                             + len(game.discard)
                             + sum(1 + (p.defense is not None) for p in game.table))
                    self.assertEqual(total, 36)
                self.assertIn(game.result, {"human", "bot", "draw"})

    def test_bot_throws_second_card_in_same_round(self):
        g = make_game(
            human=[Card("♦", 9), Card("♣", 6)],
            bot=[Card("♦", 7), Card("♥", 7), Card("♣", 9)],
            deck=[Card("♣", 10)] * 4,
            attacker=BOT,
        )
        bot = Bot(BOT, "normal", random.Random(0))
        bot.act(g)
        g.defend(Card("♦", 9))
        bot.act(g)
        self.assertEqual(len(g.table), 2)
        self.assertEqual(g.table[1].attack, Card("♥", 7))

    def test_bot_takes_when_it_must_spend_last_trumps_on_small_card(self):
        g = make_game(
            human=[Card("♥", 7), Card("♣", 6)],
            bot=[Card("♠", 12)],
            deck=[Card("♣", 10)] * 4,
            attacker=HUMAN,
        )
        g.attack(Card("♥", 7))
        bot = Bot(BOT, "hard", random.Random(0))
        bot.act(g)
        self.assertIn(Card("♥", 7), g.hands[BOT])
        self.assertIn(Card("♠", 12), g.hands[BOT])
        self.assertIn(Card("♥", 7), g.hands[BOT])


if __name__ == "__main__":
    unittest.main()
