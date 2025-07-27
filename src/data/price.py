# © 2025 kerem.ai · All rights reserved.

"""
A book for storing the bid and ask prices for a certain asset.
It stores the price and the total quantity at that price for
both bid and ask sides.
"""

from .order import Order


class PriceBook:
    """
    A book for storing the bid and ask prices for a certain asset.
    It stores the price and the total quantity at that price for
    both bid and ask sides.
    """

    def __init__(self) -> None:
        self.bids: dict[float, int] = {}
        self.asks: dict[float, int] = {}

    def step(self, order: Order) -> None:
        """
        Process one order and update the book.

        Parameters
        ----------
        order : Order
            The order to process.
        """
        if order.msg_type == "A":
            if order.side == "B":
                qty = self.bids.get(order.price, 0)
                self.bids[order.price] = qty + order.quantity
            else:
                qty = self.asks.get(order.price, 0)
                self.asks[order.price] = qty + order.quantity
        else:
            if order.side == "B":
                qty = self.bids.get(order.price, 0)
                self.bids[order.price] = qty - order.quantity
            else:
                qty = self.asks.get(order.price, 0)
                self.asks[order.price] = qty - order.quantity

    @property
    def best_prices(self) -> dict[str, float | int]:
        """
        Best bid and ask prices and the corresponding quantities.
        """
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])

        num_bid_prices = len(self.bids)
        num_ask_prices = len(self.asks)

        best_prices = {}

        for i in range(3):
            # Add i'th best bid price if it exists
            if i < num_bid_prices:
                best_prices[f"bid{i+1}_price"] = sorted_bids[i][0]
                best_prices[f"bid{i+1}_quantity"] = sorted_bids[i][1]
            else:
                best_prices[f"bid{i+1}_price"] = 0.0
                best_prices[f"bid{i+1}_quantity"] = 0

            # Add i'th best ask price if it exists
            if i < num_ask_prices:
                best_prices[f"ask{i+1}_price"] = sorted_asks[i][0]
                best_prices[f"ask{i+1}_quantity"] = sorted_asks[i][1]
            else:
                best_prices[f"ask{i+1}_price"] = 0.0
                best_prices[f"ask{i+1}_quantity"] = 0

        return best_prices
