# © 2025 kerem.ai · All rights reserved.

"""
A parser for the order data.
It parses the order data from the given path, and yields the orders one by one.
If the row is not valid, None is yielded.
"""

from pathlib import Path
from typing import Generator

from .order import Order


class OrderParser:
    """
    A parser for the given order data.
    An order includes the following information:
    - network_time : The timestamp of the order when it is received by us.
    - bist_time : The timestamp of the order when it is received/sent by BIST.
    - msg_type : The type of the message, which can be "A", "D", or "E".
    - asset_name : The name of the asset, which is the ticker symbol.
    - side : The side of the order, which can be "B" or "S".
    - price : The price of the order.
    - que_loc : The location of the order in the order book.
    - qty : The quantity of the order.
    - order_id : The unique identifier of the order.

    It behaves like a generator, and reads the data row-by-row.
    Each valid row is converted to an Order object.
    Order objects are yielded one by one.
    """

    @classmethod
    def parse(cls, path: str | Path) -> Generator[Order | None, None, None]:
        """
        Parse the order data from the given path, and yield the orders one by one.
        If the row is not valid, None is yielded.
        """
        with open(path, "r") as file:
            while line := file.readline():
                yield cls.parse_order(line)
    
    @classmethod
    def parse_order(cls, order: str) -> Order | None:
        """
        Parse the order from the given string.
        If the order is not valid, None is returned.

        Parameters
        ----------
        order : str
            The order string to parse.

        Returns
        -------
        order : Order | None
            The parsed order.
            If the order is not valid, None is returned.
        """
        try:
            nt, bt, mt, an, sd, px, _, qty, oid = order.strip().split(",")
            return Order(
                network_time=nt,
                bist_time=bt,
                msg_type=mt,
                asset_name=an,
                side=sd,
                price=float(px),
                quantity=int(qty),
                order_id=int(oid),
            )
        except BaseException:
            return None
