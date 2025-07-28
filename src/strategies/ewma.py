# © 2025 kerem.ai · All rights reserved.

import math
from datetime import timedelta
from typing import Literal

from src.backtest import Agent, LOBSnapshot
from src.data import Order

from . import STRATEGIES


@STRATEGIES.register("basic-ewma")
class BasicEWMAAgent(Agent):
    """
    An agent that uses a basic EWMA strategy.
    It cannot use cancel orders.
    It determines whether to place a bid or an ask based on the EWMA
    of the mid-price.

    Parameters
    ----------
    beta : float
        The beta parameter for the EWMA.
        Default is 0.9.
    margin : gloat
        The percentage margin to use around the EWMA price.
        If you want to set a margin of 10% around the EWMA price,
        you should set the margin to 0.1.
        Default is 0.0.
    pricing : Literal["aggressive", "conservative"]
        The pricing strategy to use.
        Default is "aggressive".
    fixed_quantity : int | None
        The fixed quantity to use.
        Default is None.
    proportional_quantity : float | None
        The proportional quantity to use.
        Default is None.
    """

    def __init__(
        self,
        beta: float = 0.9,
        margin: float = 0.0,
        wait_time: float = 0.0,
        pricing: Literal["aggressive", "conservative", "mid"] = "aggressive",
        fixed_quantity: int | None = None,
        proportional_quantity: float | None = None,
        **kwargs,
    ) -> None:
        # Initialize the agent
        Agent.__init__(self, **kwargs)

        self.beta = beta
        self.margin = margin
        self.ewma_price = None

        self.wait_time = timedelta(seconds=wait_time)
        self.last_order_time = None

        # Initialize the pricing strategy
        assert pricing in [
            "aggressive",
            "conservative",
            "mid",
        ], "Invalid pricing strategy"
        self.pricing = pricing

        # Initialize the strategy on how to calculate the quantity
        self.fixed_quantity = fixed_quantity
        self.proportional_quantity = proportional_quantity

        if not self.proportional_quantity and not self.fixed_quantity:
            self.proportional_quantity = 1.0

    def strategy(self, book: LOBSnapshot, latency: timedelta) -> list[Order]:
        # If there are no bids or asks, do nothing
        if not book.bids or not book.asks:
            return []

        # If the last order was placed less than the wait time ago, do nothing
        if (
            self.last_order_time
            and self.last_order_time + self.wait_time > book.timestamp
        ):
            return []
        self.last_order_time = book.timestamp

        bid_price, bid_qty = book.bids[-1]
        ask_price, ask_qty = book.asks[-1]

        # Calculate the mid-price
        mid_price = (bid_price + ask_price) / 2

        # Calculate the EWMA of the mid-price
        if self.ewma_price is None:
            self.ewma_price = mid_price
        else:
            self.ewma_price = self.beta * self.ewma_price + (1 - self.beta) * mid_price

        # If the mid-price is greater than the weighted mid-price,
        # then place an bid
        if self.ewma_price > mid_price * (1 + self.margin):
            # Determine the price to place the bid
            if self.pricing == "aggressive":
                price = ask_price
            elif self.pricing == "conservative":
                price = bid_price
            else:
                price = mid_price

            # If the balance is less than the price, do nothing
            if self.balance.money < price:
                return []

            # Determine the quantity to place the bid
            if self.fixed_quantity:
                quantity = self.fixed_quantity
            else:
                quantity = int(ask_qty * self.proportional_quantity)
            quantity = min(quantity, int(math.floor(self.balance.money / price)))

            return [
                Order(
                    network_time=book.timestamp,
                    bist_time=book.timestamp + latency,
                    msg_type="A",
                    asset_name=book.asset,
                    side="B",
                    price=price,
                    quantity=quantity,
                ),
            ]
        # If the mid-price is less than the weighted mid-price,
        # then place an ask
        elif self.ewma_price < mid_price * (1 - self.margin):
            # If the balance is 0, do nothing
            if self.balance.stock == 0:
                return []

            # Determine the price to place the ask
            if self.pricing == "aggressive":
                price = bid_price
            elif self.pricing == "conservative":
                price = ask_price
            else:
                price = mid_price

            # Determine the quantity to place the ask
            if self.fixed_quantity:
                quantity = self.fixed_quantity
            else:
                quantity = int(bid_qty * self.proportional_quantity)
            quantity = min(quantity, self.balance.stock)

            return [
                Order(
                    network_time=book.timestamp,
                    bist_time=book.timestamp + latency,
                    msg_type="A",
                    asset_name=book.asset,
                    side="S",
                    price=price,
                    quantity=quantity,
                ),
            ]
        else:
            return []
