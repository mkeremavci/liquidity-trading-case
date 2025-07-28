# © 2025 kerem.ai · All rights reserved.

from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic.type_adapter import P
from tqdm import tqdm

from src.data import Order, Parser

from .agent import Agent
from .book import LimitOrderBook
from .utils import OrderSourceEnum


class Backtest:
    """
    Backtest class for the liquidity trading case.

    Parameters
    ----------
    agent : Agent
        The agent for the backtest.
    filepath : str | Path
        The path to the historical order data.
    latency : float, optional
        The latency between the network and the BIST.
        Default is 0.0 seconds.
    """

    def __init__(
        self, agent: Agent, filepath: str | Path, latency: float = 0.0
    ) -> None:
        # Initialize the agent
        self.agent = agent

        # Initialize the parser for the historical order data
        self.parser = Parser(filepath)
        self.num_columns = len(pd.read_csv(filepath))
        self.pbar = tqdm(total=self.num_columns, colour="#FF9900")

        # Initialize the queues between the network and the BIST
        self.last_timestamp: datetime = None  # for historical order data
        self.hist_queue: deque[Order] = deque()
        self.network2bist_queue: deque[Order] = deque()
        self.bist2network_queue: deque[Order] = deque()

        # Initialize the limit order book
        self.book = LimitOrderBook(self.parser.filepath.stem)

        # Initialize containes for the test orders
        self.test_orders: dict[int, Order] = {}
        self.finished_orders: set[int] = set()
        self.test_timeline: list[str] = []

        # Initialize the latency between the network and the BIST
        self.latency = timedelta(seconds=max(latency, 0.0))

    def run(self) -> None:
        """
        Run the backtest on the historical order data.
        It will run until there is no more order in the queues.
        """
        while True:
            # Get the next order from the queues
            source, next_order = self._get_next_order()

            # If there is no order, break the loop
            if source == OrderSourceEnum.NO_ORDER:
                self.book.update_price_table()
                self.book.create_snapshot()
                self.agent.update_history(self.last_timestamp, self.book.price_table)
                self._run_market_maker()
                break
            # If the order is from the historical order data,
            # add it to the book
            elif source == OrderSourceEnum.HISTORICAL:
                # If the last timestamp is not the same as the order's bist time,
                # run the market maker on the book
                if self.last_timestamp and self.last_timestamp != next_order.bist_time:
                    self.book.update_price_table()
                    self.agent.update_history(
                        self.last_timestamp, self.book.price_table
                    )
                    self._run_market_maker()
                self.last_timestamp = next_order.bist_time

                # Process the next order
                is_snapshot_created = self.book.process(next_order)

                # If a snapshot is created,
                # run the strategy on the snapshot
                if is_snapshot_created:
                    for new_order in self.agent.run(self.book.lob[-1], self.latency):
                        self.network2bist_queue.append(new_order)
            elif source == OrderSourceEnum.NETWORK2BIST:
                self._execute_network2bist(next_order)
            elif source == OrderSourceEnum.BIST2NETWORK:
                self._execute_bist2network(next_order)
            else:
                raise ValueError(f"Invalid source: {source}")

        self.pbar.close()
        self.parser.close()

    def _get_next_order(self) -> tuple[OrderSourceEnum, Order | None]:
        """
        Get the next order from the historical order data or the queues.
        It returns a enum of the source of the order and the order itself.
        If enum is 1, the order is from the historical order data.
        If enum is 2, the order is from the network to the BIST.
        If enum is 3, the order is from the BIST to the network.
        If enum is 0, there is no more order.
        """
        # Read the historical order data
        self._read_historical_order()

        # If there is no order in any queue, return NO_ORDER
        if (
            not self.hist_queue
            and not self.network2bist_queue
            and not self.bist2network_queue
        ):
            return OrderSourceEnum.NO_ORDER, None

        # Get the enum of the queue with the minimum timestamp
        order_enum = int(np.argmin(self._get_queue_time())) + 1

        return OrderSourceEnum(order_enum), self._get_order_from_queue(order_enum)

    def _read_historical_order(self) -> None:
        """
        Read the historical order data from the parser.
        """
        # If the queue is not empty, return
        if self.hist_queue:
            return

        # Read the next order from the parser, if exists
        next_order = None
        while self.parser.is_open and not next_order:
            next_order = self.parser.get_next_order()
            self.pbar.update(1)

        # If the order is valid, add it to the queue
        if next_order:
            self.hist_queue.append(next_order)

    def _get_queue_time(self) -> list[datetime]:
        """
        Get the timestamp of the next order in each queue.
        If the queue is empty, return maximum datetime.
        """
        return [
            queue[0].network_time if queue else datetime.max
            for queue in (
                self.hist_queue,
                self.network2bist_queue,
                self.bist2network_queue,
            )
        ]

    def _get_order_from_queue(self, order_enum: int) -> Order | None:
        """
        Get the order from the queue with the given enum.
        If the queue is empty, return None.
        """
        if order_enum == 1:
            return self.hist_queue.popleft()
        elif order_enum == 2:
            return self.network2bist_queue.popleft()
        else:
            return self.bist2network_queue.popleft()

    def _run_market_maker(self) -> None:
        """
        Run the market maker on the book.
        """
        # Run the market maker on the bids
        self._run_bids()

        # Run the market maker on the asks
        self._run_asks()

    def _run_bids(self) -> None:
        """
        Run the market maker on the bids.
        """
        bids = OrderedDict(
            sorted(
                [
                    (bid_id, bid)
                    for bid_id, bid in self.test_orders.items()
                    if bid.side == "B" and bid_id not in self.finished_orders
                ],
                key=lambda x: x[1].price,
                reverse=True,
            )
        )
        prices = self.book.sorted_asks()

        while bids and prices:
            # Get the next best bid and run the market maker on it
            _, bid = bids.popitem(last=False)
            is_stopped, prices = self._run_single_bid(bid, prices)

            # If the stop condition is met, break the loop
            if is_stopped:
                break

    def _run_single_bid(
        self, bid: Order, prices: list[tuple[float, int]]
    ) -> tuple[bool, list[tuple[float, int]]]:
        """
        Run the market maker on a single bid, and return the updated prices,
        as well as a boolean indicating whether the prices are above the best bid's price.

        Parameters
        ----------
        bid : Order
            The bid to run the market maker on.
        prices : list[tuple[float, int]]
            The prices to run the market maker on.

        Returns
        -------
        is_stopped : bool
            Whether the prices are above the best bid's price.
        prices : list[tuple[float, int]]
            The updated prices.
        """
        bid = deepcopy(bid)
        is_stopped = False
        qty = 0.0

        while prices and bid.quantity:
            # If the bid's quantity is 0, break the loop
            if bid.quantity <= 0:
                break

            # If the quantity is 0, remove the next price from the list
            if qty == 0.0:
                px, qty = prices.pop()

            # If the bid's price is below the best price, stop the loop
            if bid.price < px:
                is_stopped = True
                break

            # Find the executed quantity
            exec_qty = min(bid.quantity, qty)
            qty -= exec_qty
            bid.quantity -= exec_qty

            # Add the executed order to the bist2network queue
            self.bist2network_queue.append(
                Order(
                    network_time=self.last_timestamp + self.latency,
                    bist_time=self.last_timestamp,
                    msg_type="E",
                    asset_name=bid.asset_name,
                    side="B",
                    price=px,
                    quantity=exec_qty,
                    order_id=bid.order_id,
                )
            )

        # If the last price is not fully executed, append it
        if qty > 0:
            prices.append((px, qty))

        # If the bid is fully executed, add it to the finished orders
        if bid.quantity == 0:
            self.finished_orders.add(bid.order_id)

        return is_stopped, prices

    def _run_asks(self) -> None:
        """
        Run the market maker on the asks.
        """
        asks = OrderedDict(
            sorted(
                [
                    (ask_id, ask)
                    for ask_id, ask in self.test_orders.items()
                    if ask.side == "A" and ask_id not in self.finished_orders
                ],
                key=lambda x: x[1].price,
                reverse=False,
            )
        )
        prices = self.book.sorted_bids()

        while asks and prices:
            # Get the next best ask and run the market maker on it
            _, ask = asks.popitem(last=False)
            is_stopped, prices = self._run_single_ask(ask, prices)

            # If the stop condition is met, break the loop
            if is_stopped:
                break

    def _run_single_ask(
        self, ask: Order, prices: list[tuple[float, int]]
    ) -> tuple[bool, list[tuple[float, int]]]:
        """
        Run the market maker on a single ask, and return the updated prices,
        as well as a boolean indicating whether the prices are below the best ask's price.

        Parameters
        ----------
        ask : Order
            The ask to run the market maker on.
        prices : list[tuple[float, int]]
            The prices to run the market maker on.

        Returns
        -------
        is_stopped : bool
            Whether the prices are below the best ask's price.
        prices : list[tuple[float, int]]
            The updated prices.
        """
        ask = deepcopy(ask)
        is_stopped = False
        qty = 0.0

        while prices and ask.quantity:
            # If the ask's quantity is 0, break the loop
            if ask.quantity <= 0:
                break

            # If the quantity is 0, remove the next price from the list
            if qty == 0.0:
                px, qty = prices.pop()

            # If the ask's price is above the best price, stop the loop
            if ask.price > px:
                is_stopped = True
                break

            # Find the executed quantity
            exec_qty = min(ask.quantity, qty)
            qty -= exec_qty
            ask.quantity -= exec_qty

            # Add the executed order to the bist2network queue
            self.bist2network_queue.append(
                Order(
                    network_time=self.last_timestamp + self.latency,
                    bist_time=self.last_timestamp,
                    msg_type="E",
                    asset_name=ask.asset_name,
                    side="S",
                    price=ask.price,
                    quantity=exec_qty,
                    order_id=ask.order_id,
                )
            )

        # If the last price is not fully executed, append it
        if qty > 0:
            prices.append((px, qty))

        # If the ask is fully executed, add it to the finished orders
        if ask.quantity == 0:
            self.finished_orders.add(ask.order_id)

        return is_stopped, prices

    def _execute_network2bist(self, order: Order) -> None:
        """
        Execute the network to the BIST order.

        Parameters
        ----------
        order : Order
            The network to the BIST order.
        """
        # Add the order to the timeline -- without modifying it
        self.test_timeline.append(str(order))

        # If the order is a cancel request, remove it from the test orders
        # And add a "D" message to bist2network queue
        if order.msg_type == "C":
            self._execute_cancel(order)
        # If the order is an add order, add it to the test orders
        elif order.msg_type == "A":
            self._execute_add(order)
        # Other message types are not supported in the network2bist queue
        else:
            raise ValueError(f"Invalid message type: {order.msg_type}")

    def _execute_bist2network(self, order: Order) -> None:
        """
        Execute a BIST to network order.

        Parameters
        ----------
        order : Order
            The BIST to the network order.
        """
        # Add the order to the timeline -- without modifying it
        self.test_timeline.append(str(order))

        # If the order is a delete order, remove it from the test orders
        if order.msg_type == "D":
            self._execute_delete(order)
        # If the order is an execute order, execute it
        elif order.msg_type == "E":
            self._execute_execute(order)
        # Other message types are not supported in the bist2network queue
        else:
            raise ValueError(f"Invalid message type: {order.msg_type}")

    def _execute_cancel(self, order: Order) -> None:
        """
        Execute a cancel request and write a "D" message to the bist2network queue.

        Parameters
        ----------
        order : Order
            The cancel request order.
        """
        # Pop the cancelled order from the test orders
        cancelled_order = self.test_orders.pop(order.order_id, None)

        # If the order is already cancelled or fully executed, return
        if not cancelled_order:
            return

        # Modify the order to a delete order
        order.msg_type = "D"
        order.network_time = order.bist_time + self.latency
        order.quantity = cancelled_order.quantity
        order.price = cancelled_order.price

        # Add the order to the bist2network queue
        self.bist2network_queue.append(order)

    def _execute_add(self, order: Order) -> None:
        """
        Execute an add order.
        """
        # Hold money or stock according to the order's side
        if order.side == "B":
            # If the order's money is more than the agent's money, return
            total_money = order.price * order.quantity
            if total_money > self.agent.balance.money:
                return

            # Otherwise, execute order and hold money
            self.agent.balance.money -= total_money
            self.agent.balance.held_money += total_money
        else:
            # If the order's stock is more than the agent's stock, return
            if order.quantity > self.agent.balance.stock:
                return

            # Otherwise, execute order and hold stock
            self.agent.balance.stock -= order.quantity
            self.agent.balance.held_stock += order.quantity

        # Add the order to the test orders
        self.test_orders[order.order_id] = order

    def _execute_delete(self, order: Order) -> None:
        """
        Execute a delete message's results.

        Parameters
        ----------
        order : Order
            The delete message.
        """
        total_money = order.price * order.quantity

        # If the order is a buy order,
        # add the held money to the agent's wallet
        if order.side == "B":
            self.agent.balance.money += total_money
            self.agent.balance.held_money -= total_money
        # If the order is a sell order,
        # add the held stock to the agent's wallet
        else:
            self.agent.balance.stock += order.quantity
            self.agent.balance.held_stock -= order.quantity

    def _execute_execute(self, order: Order) -> None:
        """
        Execute an execute message's results.

        Parameters
        ----------
        order : Order
            The execute message.
        """
        # If the order is not in the test orders, return
        executed_order = self.test_orders[order.order_id]
        executed_qty = min(executed_order.quantity, order.quantity)
        total_money = order.price * executed_qty

        # If the order is a buy order, remove expected money from held balance
        # and add the corresponding stock to the agent's wallet
        # Besides, add the difference to the agent's wallet
        if order.side == "B":
            expected_money = executed_order.price * executed_qty
            self.agent.balance.held_money -= expected_money
            self.agent.balance.stock += executed_qty
            self.agent.balance.money += expected_money - total_money

            # Update the test order's quantity
            if executed_order.quantity == executed_qty:
                self.finished_orders.add(order.order_id)
                self.test_orders.pop(order.order_id)
            else:
                self.test_orders[order.order_id].quantity -= executed_qty

        # If the order is a sell order, remove quantity from held balance
        # and add the corresponding money to the agent's wallet
        else:
            self.agent.balance.money += total_money
            self.agent.balance.held_stock -= executed_qty

            # Update the test order's quantity
            if executed_order.quantity == executed_qty:
                self.finished_orders.add(order.order_id)
                self.test_orders.pop(order.order_id)
            else:
                self.test_orders[order.order_id].quantity -= executed_qty

    def export_lob(self, output_path: str | Path) -> None:
        """
        Export the limit order book to a csv file.

        Parameters
        ----------
        output_path : str | Path
            The path to the output file.
        """
        output_path = Path(output_path)
        assert output_path.suffix == ".csv", "Output path must be a csv file"

        df = pd.DataFrame([lob.todict() for lob in self.book.lob])
        df.to_csv(output_path, index=False)
