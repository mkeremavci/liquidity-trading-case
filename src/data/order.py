# © 2025 kerem.ai · All rights reserved.

"""
"Order" class for a single order in a market.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator


def parse_timestamp(timestamp: str) -> str:
    """
    Parse the timestamp from integer timestamp to ISO 8601 format.
    It converts timestamp string to floating point number and
    then to ISO 8601 format.

    Parameters
    ----------
    timestamp : str
        The timestamp string to parse.

    Returns
    -------
    timestamp : str
        The parsed timestamp in ISO 8601 format.
    """
    return datetime.fromtimestamp(float(timestamp) / 1e9).isoformat()


class Order(BaseModel):
    """
    Order class for a single order in a market.

    Parameters
    ----------
    network_time : str
        The timestamp of the order in network time.
    bist_time : str
        The timestamp of the order in BIST time.
    msg_type : Literal["A", "D", "E"]
        The type of the message, which can be "A", "D", or "E".
    asset_name : str
        The name of the asset, which is the ticker symbol.
    side : Literal["B", "S"]
        The side of the order, which can be "B" or "S".
    price : float
        The price of the order.
    quantity : int
        The quantity of the order.
    order_id : int
        The unique identifier of the order.
    """

    network_time: Annotated[str, BeforeValidator(parse_timestamp)]
    bist_time: Annotated[str, BeforeValidator(parse_timestamp)]
    msg_type: Literal["A", "D", "E"]
    asset_name: str
    side: Literal["B", "S"]
    price: float
    quantity: int
    order_id: int

    def __str__(self) -> str:
        """
        String representation of the order.
        """
        return f"{self.msg_type}-{self.side}-{self.price}-{self.quantity}-{self.order_id}"

    def __lt__(self, other: "Order") -> bool:
        """
        Compare the orders by price and bist_time, respectively.
        If the prices are equal, it compares the bist_time.
        Otherwise, it compares the price.
        """
        if self.price == other.price:
            return self.bist_time < other.bist_time
        return self.price < other.price

    def __gt__(self, other: "Order") -> bool:
        """
        Compare the orders by price and bist_time, respectively.
        If the prices are equal, it compares the bist_time.
        Otherwise, it compares the price.
        """
        if self.price == other.price:
            return self.bist_time > other.bist_time
        return self.price > other.price

    def execute(self, order: "Order") -> tuple["Order", bool]:
        """
        Take "execute" action the order, and return the message order
        with the executed order's price.
        If the order is fully completed, it returns True for the second return value.
        Otherwise (i.e., there is remaining quantity), it returns False.

        Parameters
        ----------
        order : Order
            The order containing the "execute" message.

        Returns
        -------
        order : Order
            The message order with the executed order's price.
        is_completed : bool
            Whether the order is completed.
            In other words, after executing the order, no quantity is left.
        """
        order.price = self.price
        self.quantity -= order.quantity

        return order, self.quantity == 0

    def delete(self, order: "Order") -> "Order":
        """
        Take "delete" action the order, and return the message order
        with the deleted order's price and quantity.

        Parameters
        ----------
        order : Order
            The order containing the "delete" message.

        Returns
        -------
        order : Order
            The message order with the deleted order's price and quantity.
        """
        order.price = self.price
        order.quantity = self.quantity

        return order
