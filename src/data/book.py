# © 2025 kerem.ai · All rights reserved.

"""
A class for storing and processing the orders for a certain asset.
"""

from .order import Order


class OrderBook:
    """
    A book for storing the orders for a certain asset.
    It stores the orders for both bid and ask sides.
    It also stores the mold packages for each timestamp.
    """

    def __init__(self) -> None:
        self.bids: dict[int, Order] = {}
        self.asks: dict[int, Order] = {}
        self.molds: dict[str, list[str]] = {}

    def step(self, order: Order) -> Order:
        """
        Process one order and update the book.
        If the order's message type is "A", the order remains the same.
        Otherwise, the order's price and quantity fields are updated.
        After processing the order, the order's mold package is stored in the book.
        And the updated order is returned.

        Parameters
        ----------
        order : Order
            The order to process.

        Returns
        -------
        order : Order
            The updated order.
        """
        if order.side == "B":
            order = self.step_bid(order)
        else:
            order = self.step_ask(order)

        # Store the mold package of the order
        # after processing the order
        self.store_mold(order)

        return order

    def step_bid(self, order: Order) -> Order:
        """
        Process a bid order.
        If the order's message type is "A", its added to the bid book.
        If the order's message type is "E", its executed with the existing bid order.
        If the order's message type is "D", its deleted from the bid book.

        Parameters
        ----------
        order : Order
            The bid order to process.

        Returns
        -------
        order : Order
            The updated order.
        """
        if order.msg_type == "A":
            self.bids[order.order_id] = order
        elif order.msg_type == "E":
            order, is_completed = self.bids[order.order_id].execute(order)
            if is_completed:
                self.bids.pop(order.order_id)
        else:
            deleted_order = self.bids.pop(order.order_id)
            order = deleted_order.delete(order)

        return order

    def step_ask(self, order: Order) -> Order:
        """
        Process an ask order.
        If the order's message type is "A", its added to the ask book.
        If the order's message type is "E", its executed with the existing ask order.
        If the order's message type is "D", its deleted from the ask book.

        Parameters
        ----------
        order : Order
            The ask order to process.

        Returns
        -------
        order : Order
            The updated order.
        """
        if order.msg_type == "A":
            self.asks[order.order_id] = order
        elif order.msg_type == "E":
            order, is_completed = self.asks[order.order_id].execute(order)
            if is_completed:
                self.asks.pop(order.order_id)
        else:
            deleted_order = self.asks.pop(order.order_id)
            order = deleted_order.delete(order)

        return order

    def store_mold(self, order: Order) -> None:
        """
        Store the order's mold package in the book.
        If network_time of the order is not in the book,
        create a new list for that timestamp.
        Then, append the order's mold package to the list.
        Mold package is a string representation of the order.

        Example: "A-S-11.8-10000-7621969089429467559"
        """
        if order.network_time not in self.molds:
            self.molds[order.network_time] = []
        self.molds[order.network_time].append(str(order))
