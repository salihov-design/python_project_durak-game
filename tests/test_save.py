import json
import random
import unittest

from durak.engine import Game


class SaveTests(unittest.TestCase):
    def test_round_trip_through_json(self):
        g = Game(random.Random(7))
        rng = random.Random(3)
        for _ in range(12):
            if g.over:
                break
            if g.turn() == g.attacker:
                options = g.legal_attacks()
                if options and g.table:
                    g.attack(rng.choice(options))
                elif options:
                    g.attack(options[0])
                else:
                    g.finish()
            else:
                options = g.legal_defends()
                if options:
                    g.defend(options[0])
                else:
                    g.take()
        data = json.loads(json.dumps(g.to_dict()))
        g2 = Game.from_dict(data)
        self.assertEqual(g2.to_dict(), g.to_dict())
        self.assertEqual(g2.turn(), g.turn())


if __name__ == "__main__":
    unittest.main()
