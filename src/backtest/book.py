# © 2025 kerem.ai · All rights reserved.

from dataclasses import dataclass
from datetime import datetime

from src.data import Order


@dataclass
class LOBSnapshot:
    """
    A snapshot of the limit order book for a certain asset at a certain timestamp.
    """

    timestamp: datetime
    asset: str
    bids: list[tuple[float, int]]
    asks: list[tuple[float, int]]
    mold_package: str = ""

    def todict(self) -> dict:
        """
        Convert the snapshot to a dictionary,
        in a format compatible with the desired csv file.

        Returns
        -------
        snapshot_dict : dict
            A dictionary containing the snapshot's data.
        """
        snapshot_dict = {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "bid3qty": 0,
            "bid3px": 0.0,
            "bid2qty": 0,
            "bid2px": 0.0,
            "bid1qty": 0,
            "bid1px": 0.0,
            "ask1px": 0.0,
            "ask1qty": 0,
            "ask2px": 0.0,
            "ask2qty": 0,
            "ask3px": 0.0,
            "ask3qty": 0,
            "mold_package": self.mold_package,
        }

        for i in range(1, len(self.bids) + 1):
            if i > 3:
                break
            snapshot_dict[f"bid{i}qty"] = self.bids[-i][1]
            snapshot_dict[f"bid{i}px"] = self.bids[-i][0]

        for i in range(1, len(self.asks) + 1):
            if i > 3:
                break
            snapshot_dict[f"ask{i}qty"] = self.asks[-i][1]
            snapshot_dict[f"ask{i}px"] = self.asks[-i][0]

        return snapshot_dict


@dataclass
class PriceTable:
    """
    A price table at a certain timestamp for a certain asset.
    """

    mid_price: float = None
    best_bid_price: float = None
    best_ask_price: float = None
    last_bid_price: float = None
    last_ask_price: float = None


class LimitOrderBook:
    """
    A limit order book for a certain asset.
    It stores the active orders and the limit order book snapshots.

    Parameters
    ----------
    asset : str
        The asset of the limit order book.
    """

    def __init__(self, asset: str) -> None:
        self.asset = asset

        # Initialize a dict for storing the active orders
        self.orders: dict[int, Order] = {}

        # Initialize a mapping of price to quantity for bids and asks
        self.bid_prices: dict[float, int] = {}
        self.ask_prices: dict[float, int] = {}

        # Initialize containers for managing the LOB
        self.last_timestamp: datetime = None
        self.mold_package: list[str] = []
        self.lob: list[LOBSnapshot] = []

        # Initialize the price table
        self.price_table: PriceTable = PriceTable()

    def process(self, order: Order) -> bool:
        """
        Process an order from the historical data.
        It returns True if a snapshot is created, False otherwise.

        Parameters
        ----------
        order : Order
            The order to process.

        Returns
        -------
        snapshot_created : bool
            True if a snapshot is created, False otherwise.
        """
        # If the last timestamp is not the same as the order's network time,
        # create a snapshot for the last timestamp
        is_snapshot_created = False

        if self.last_timestamp and self.last_timestamp != order.network_time:
            self.create_snapshot()
            is_snapshot_created = True

        # Update the last timestamp
        self.last_timestamp = order.network_time

        # Process the order according to the message type
        if order.msg_type == "A":
            self._process_add_order(order)
        elif order.msg_type == "D":
            self._process_delete_order(order)
        else:
            self._process_execute_order(order)

        return is_snapshot_created

    def _process_add_order(self, order: Order) -> None:
        """
        Process an order with msg_type "A".
        It assumes that the message type is already checked.
        """
        # Store the order in the orders dict
        self.orders[order.order_id] = order

        # If the order is a bid, add it to the bid_prices dict
        if order.side == "B":
            qty = self.bid_prices.get(order.price, 0)
            self.bid_prices[order.price] = qty + order.quantity
        # If the order is an ask, add it to the ask_prices dict
        else:
            qty = self.ask_prices.get(order.price, 0)
            self.ask_prices[order.price] = qty + order.quantity

        # Add the order's representation to the mold package list
        self.mold_package.append(str(order))

    def _process_delete_order(self, order: Order) -> None:
        """
        Process an order with msg_type "D".
        It assumes that the message type is already checked.
        """
        # Remove the order from the orders dict
        deleted_order = self.orders.pop(order.order_id)
        order.quantity = deleted_order.quantity
        order.price = deleted_order.price

        # If the order is a bid, subtract the quantity from the bid_prices dict
        if order.side == "B":
            qty = self.bid_prices[order.price]
            if order.quantity == qty:
                self.bid_prices.pop(order.price)
            else:
                self.bid_prices[order.price] = qty - order.quantity
        # If the order is an ask, subtract the quantity from the ask_prices dict
        else:
            qty = self.ask_prices[order.price]
            if order.quantity == qty:
                self.ask_prices.pop(order.price)
            else:
                self.ask_prices[order.price] = qty - order.quantity

        # Add the order's representation to the mold package list
        self.mold_package.append(str(order))

    def _process_execute_order(self, order: Order) -> None:
        """
        Process an order with msg_type "E".
        It assumes that the message type is already checked.
        """
        # Get the target order from the orders dict
        # and update the remaining quantity
        target_order = self.orders[order.order_id]
        target_order.quantity -= order.quantity
        order.price = target_order.price

        # If the target order is fully executed, remove it from the orders dict
        if target_order.quantity == 0:
            self.orders.pop(target_order.order_id)
        else:
            self.orders[target_order.order_id] = target_order

        if order.side == "B":
            qty = self.bid_prices[order.price]
            if order.quantity == qty:
                self.bid_prices.pop(order.price)
            else:
                self.bid_prices[order.price] = qty - order.quantity

            # Update the price table
            self.price_table.last_bid_price = order.price
        else:
            qty = self.ask_prices[order.price]
            if order.quantity == qty:
                self.ask_prices.pop(order.price)
            else:
                self.ask_prices[order.price] = qty - order.quantity

            # Update the price table
            self.price_table.last_ask_price = order.price

        # Add the order's representation to the mold package list
        self.mold_package.append(str(order))

    def create_snapshot(self) -> None:
        """
        Create a snapshot of the limit order book.
        """
        if not self.mold_package:
            return

        # Sort the bids and asks such that the last item is the best
        sorted_bids = self.sorted_bids()
        sorted_asks = self.sorted_asks()

        # Create the snapshot
        snapshot = LOBSnapshot(
            timestamp=self.last_timestamp,
            asset=self.asset,
            bids=sorted_bids,
            asks=sorted_asks,
            mold_package=";".join(self.mold_package),
        )

        # Store the snapshot
        self.lob.append(snapshot)

        # Clear the mold package
        self.mold_package = []

    def update_price_table(self) -> None:
        """
        Update the price table.
        """
        # Sort the bids and asks such that the last item is the best
        sorted_bids = self.sorted_bids()
        sorted_asks = self.sorted_asks()

        # Update the price table
        if sorted_bids and sorted_asks:
            self.price_table.best_bid_price = sorted_bids[-1][0]
            self.price_table.best_ask_price = sorted_asks[-1][0]
            self.price_table.mid_price = (
                self.price_table.best_bid_price + self.price_table.best_ask_price
            ) / 2

    def sorted_bids(self) -> list[tuple[float, int]]:
        """
        Get the sorted bids, from worst to best.

        Returns
        -------
        sorted_bids : list[tuple[float, int]]
            The sorted bids.
        """
        return sorted(self.bid_prices.items(), key=lambda x: x[0])

    def sorted_asks(self) -> list[tuple[float, int]]:
        """
        Get the sorted asks, from worst to best.

        Returns
        -------
        sorted_asks : list[tuple[float, int]]
            The sorted asks.
        """
        return sorted(self.ask_prices.items(), key=lambda x: x[0], reverse=True)
