# © 2025 kerem.ai · All rights reserved.

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field


def parse_timestamp(timestamp: str | datetime) -> datetime:
    """
    Parse the timestamp from integer timestamp to datetime object.
    It converts timestamp string to floating point number and
    then to datetime object.

    Parameters
    ----------
    timestamp : str
        The timestamp string to parse.

    Returns
    -------
    timestamp : datetime
        The parsed timestamp.
    """
    if isinstance(timestamp, datetime):
        return timestamp
    return datetime.fromtimestamp(float(timestamp) / 1e9)


class Order(BaseModel):
    """
    Order class for a single order in a market.

    Parameters
    ----------
    network_time : datetime
        The timestamp of the order in network time.
    bist_time : datetime
        The timestamp of the order in BIST time.
    msg_type : Literal["A", "D", "E", "C"]
        The type of the message, which can be "A", "D", "E", or "C".
        "A" stands for an order is added.
        "D" stands for an order is deleted.
        "E" stands for an order is executed.
        "C" stands for a cancel request.
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

    network_time: Annotated[datetime, BeforeValidator(parse_timestamp)]
    bist_time: Annotated[datetime, BeforeValidator(parse_timestamp)]
    msg_type: Literal["A", "D", "E", "C"]
    asset_name: str
    side: Literal["B", "S"]
    price: float
    quantity: int
    order_id: int = Field(default_factory=lambda: uuid.uuid1().int >> 64)

    def __str__(self) -> str:
        """
        String representation of the order.
        """
        return (
            f"{self.msg_type}-{self.side}-{self.price}-{self.quantity}-{self.order_id}"
        )
