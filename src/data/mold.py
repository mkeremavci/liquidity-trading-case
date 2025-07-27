# © 2025 kerem.ai · All rights reserved.

"""
A class for storing the mold packages after each order.
"""

from typing import Literal

from .order import Order


class MoldBook:
    """
    A book for storing the mold packages after each order.
    It stores packages for each timestamp.
    It uses the owner to determine which timestamp to use

    Parameters
    ----------
    owner : Literal["broker", "market"]
        The owner of the book.
        If the owner is "broker", the book is used by the broker,
        and network_time is used as the timestamp.
        If the owner is "market", the book is used by the market,
        and bist_time is used as the timestamp.
    """

    def __init__(self, owner: Literal["broker", "market"]) -> None:
        self.owner = owner
        self.packages: dict[str, list[Order]] = {}

        # Tracking the last execution prices
        self.current_timestamp: str = None
        self.last_timestamp: str = None
        self.last_exec_prices: dict[str, float] = {}

    def step(self, order: Order) -> bool:
        """
        Update the book with the incoming order.
        If the order message is received at a new timestamp,
        it returns True, otherwise it returns False.

        Parameters
        ----------
        order : Order
            The received order message.

        Returns
        -------
        is_new_timestamp : bool
            True if the order message is received at a new timestamp,
            False otherwise.
        """
        if self.owner == "broker":
            timestamp = order.get_network_time()
        else:
            timestamp = order.get_bist_time()

        if timestamp != self.current_timestamp:
            self.update_last_execution_price()
            self.packages[timestamp] = []
            self.current_timestamp = timestamp
            is_new_timestamp = True
        else:
            is_new_timestamp = False

        self.packages[timestamp].append(order)

        return is_new_timestamp

    @property
    def last_execution_price(self) -> float | None:
        """
        The last execution price.
        """
        return self.last_exec_prices.get(self.last_timestamp, None)

    def update_last_execution_price(self) -> None:
        """
        Update the last execution price.
        """
        # If no current timestamp is set, return
        if not self.current_timestamp:
            return

        # Get the executed orders and calculate the average price
        total_amount, total_qty = 0.0, 0

        for order in self.packages[self.current_timestamp]:
            if order.msg_type == "E":
                total_amount += order.price * order.quantity
                total_qty += order.quantity

        # If there are executed orders, update the last execution price
        # with the weighted average of the executed orders
        if total_qty > 0:
            self.last_exec_prices[self.current_timestamp] = total_amount / total_qty
        # If there are no executed orders, use the last execution price
        elif self.last_timestamp:
            self.last_exec_prices[self.current_timestamp] = self.last_exec_prices[
                self.last_timestamp
            ]
        else:
            self.last_exec_prices[self.current_timestamp] = None

        # Update the last timestamp
        self.last_timestamp = self.current_timestamp

    def get_mold_packages(self) -> dict[str, str]:
        """
        Get the mold packages for each timestamp in string format.

        Returns
        -------
        mold_packages : dict[str, str]
            The mold packages for each timestamp.
            The key is the timestamp and the value is the string representation of the orders.
        """
        return {
            timestamp: ";".join(str(order) for order in orders)
            for timestamp, orders in self.packages.items()
        }
