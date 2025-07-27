# © 2025 kerem.ai · All rights reserved.

"""
A book for storing the bid and ask prices for a certain asset.
It stores the price and the total quantity at that price for
both bid and ask sides.
"""

from dataclasses import dataclass

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
                # Get the quantity at the price
                qty = self.bids.get(order.price, 0)

                # If the quantity is equal to the order quantity,
                # remove the price from the bids
                if qty == order.quantity:
                    self.bids.pop(order.price)
                else:
                    self.bids[order.price] = qty - order.quantity
            else:
                # Get the quantity at the price
                qty = self.asks.get(order.price, 0)

                # If the quantity is equal to the order quantity,
                # remove the price from the asks
                if qty == order.quantity:
                    self.asks.pop(order.price)
                else:
                    self.asks[order.price] = qty - order.quantity

    def get_sorted_bids(self, reverse: bool = False) -> list[tuple[float, int]]:
        """
        Get the sorted bids and the corresponding quantities
        in descending order if the reverse parameter is False.
        Otherwise, it returns the sorted bids in ascending order.

        Returns
        -------
        sorted_bids : list[tuple[float, int]]
            The sorted bids.
        """
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=not reverse)

        return sorted_bids

    def get_sorted_asks(self, reverse: bool = False) -> list[tuple[float, int]]:
        """
        Get the sorted asks and the corresponding quantities
        in ascending order if the reverse parameter is False.
        Otherwise, it returns the sorted asks in descending order.

        Returns
        -------
        sorted_asks : list[tuple[float, int]]
            The sorted asks.
        """
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0], reverse=reverse)

        return sorted_asks

    @property
    def best_bid(self) -> tuple[float, int] | None:
        """
        Get the best bid and the corresponding quantity.

        Returns
        -------
        best_bid : tuple[float, int] | None
            The best bid and the corresponding quantity.
            If there is no bid, it returns None.
        """
        sorted_bids = self.get_sorted_bids()

        if sorted_bids:
            return sorted_bids[0]
        else:
            return None

    @property
    def best_bid_price(self) -> float | None:
        """
        Get the best bid price.
        """
        return self.best_bid[0] if self.best_bid else None

    @property
    def best_ask(self) -> tuple[float, int] | None:
        """
        Get the best ask and the corresponding quantity.
        """
        sorted_asks = self.get_sorted_asks()

        if sorted_asks:
            return sorted_asks[0]
        else:
            return None

    @property
    def best_ask_price(self) -> float | None:
        """
        Get the best ask price.
        """
        return self.best_ask[0] if self.best_ask else None

    @property
    def mid_price(self) -> float | None:
        """
        Get the mid price.
        """
        if self.best_bid_price and self.best_ask_price:
            return (self.best_bid_price + self.best_ask_price) / 2
        else:
            return None


@dataclass
class PriceTable:
    """
    A table for storing the prices for a certain asset
    at a certain timestamp.
    """

    mid_price: float
    last_execution_price: float
    best_bid_price: float
