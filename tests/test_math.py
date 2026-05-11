import unittest
from decimal import Decimal
from launchpad.curve import BondingCurve
from copytrader.engine import ExecutionEngine

class TestFeeForgeMath(unittest.TestCase):
    def setUp(self):
        self.curve = BondingCurve()

    def test_bonding_curve_cost(self):
        # Initial price: 0.00001, Slope: 0.0000000001
        # Buying 1,000,000 tokens starting at 0 supply
        cost = self.curve.calculate_cost(Decimal("0"), Decimal("1000000"))
        # Expected: 0.00001 * 1M + 0.5 * 1e-10 * (1M)^2
        # = 10 + 0.5 * 1e-10 * 1e12 = 10 + 0.5 * 100 = 10 + 50 = 60 XRP
        self.assertEqual(cost, Decimal("60"))

    def test_bonding_curve_price_increase(self):
        p0 = self.curve.get_price(Decimal("0"))
        p1 = self.curve.get_price(Decimal("1000000"))
        self.assertGreater(p1, p0)
        self.assertEqual(p1, Decimal("0.00011")) # 1e-5 + 1e-10 * 1e6 = 1e-5 + 1e-4 = 0.00011

    def test_copy_trader_scaling(self):
        engine = ExecutionEngine(None) # Session not needed for scale_amount
        
        # Scale XRP (drops as string)
        leader_gets = "100000000" # 100 XRP
        follower_pct = Decimal("10")
        mirror_gets = engine._scale_amount(leader_gets, follower_pct)
        self.assertEqual(mirror_gets, "10000000") # 10 XRP
        
        # Scale Token dict
        leader_pays = {"currency": "USD", "issuer": "r...", "value": "100"}
        mirror_pays = engine._scale_amount(leader_pays, follower_pct)
        self.assertEqual(mirror_pays["value"], "10.0")

if __name__ == "__main__":
    unittest.main()
