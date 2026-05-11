from decimal import Decimal

class BondingCurve:
    """
    Implements a simple bonding curve math.
    Price increases as supply increases.
    """
    def __init__(self, initial_price: Decimal = Decimal("0.00001"), slope: Decimal = Decimal("0.0000000001")):
        self.initial_price = initial_price
        self.slope = slope

    def get_price(self, supply: Decimal) -> Decimal:
        """P = initial_price + slope * supply"""
        return self.initial_price + (self.slope * supply)

    def calculate_cost(self, current_supply: Decimal, amount_to_buy: Decimal) -> Decimal:
        """
        Calculates the XRP cost for buying 'amount_to_buy' tokens.
        Integrate(P) from supply to supply + amount.
        """
        # Cost = initial_price * amount + 0.5 * slope * ((supply + amount)^2 - supply^2)
        p1 = self.initial_price * amount_to_buy
        p2 = Decimal("0.5") * self.slope * ((current_supply + amount_to_buy)**2 - current_supply**2)
        return p1 + p2

    def calculate_refund(self, current_supply: Decimal, amount_to_sell: Decimal) -> Decimal:
        """Calculates the XRP refund for selling tokens."""
        # Refund = Integrate(P) from supply - amount to supply
        p1 = self.initial_price * amount_to_sell
        p2 = Decimal("0.5") * self.slope * (current_supply**2 - (current_supply - amount_to_sell)**2)
        return p1 + p2
