# © 2025 kerem.ai · All rights reserved.

from abc import ABC, abstractmethod
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from src.data import Order

from .book import LOBSnapshot, PriceTable


@dataclass
class Balance:
    """
    A balance sheet for an agent.
    """

    money: float = 0.0
    stock: int = 0
    held_money: float = 0.0
    held_stock: int = 0


class Agent(ABC):
    """
    An agent that can trade on a market.
    It is an abstract base class for all agents.
    You should implement your own agent by inheriting from this class.

    Parameters
    ----------
    order_cost : float
        The cost of each requested order.
        Default is 0.0.
    initial_money : float
        The initial money of the agent.
        Default is 10000.0.
    initial_stock : int, optional
        The initial stock of the agent.
        Default is 0.
    """

    def __init__(
        self,
        order_cost: float = 0.0,
        initial_money: float = 10000.0,
        initial_stock: int = 0,
    ) -> None:
        # Initialize the abstract base class
        ABC.__init__(self)

        self.order_cost = order_cost
        self.balance = Balance(initial_money, initial_stock)

        self.history: list[datetime] = []
        self.balance_history: list[Balance] = []
        self.price_history: list[PriceTable] = []

    def run(self, book: LOBSnapshot, latency: timedelta) -> list[Order]:
        """
        It runs the agent's strategy and returns the orders to be executed.
        For each order, the agent's balance is decreased by the order cost.

        Parameters
        ----------
        book : LOBSnapshot
            The limit order book snapshot.
        latency : timedelta
            The delay between the network and the BIST.

        Returns
        -------
        orders : list[Order]
            A list of orders to be executed.
        """
        orders = self.strategy(book, latency)
        self.balance.money -= self.order_cost * len(orders)

        return orders

    @abstractmethod
    def strategy(self, book: LOBSnapshot, latency: timedelta) -> list[Order]:
        """
        A strategy for the agent.
        Agent should decide whether to place a bid or an ask,
        or a cancel order.

        Parameters
        ----------
        book : LOBSnapshot
            The limit order book snapshot.
        latency : timedelta
            The delay between the network and the BIST.

        Returns
        -------
        orders : list[Order]
            A list of orders to be executed.
        """
        ...

    def update_history(self, timestamp: datetime, price_table: PriceTable) -> None:
        """
        Update the history of the agent.

        Parameters
        ----------
        price_table : PriceTable
            The price table of the agent.
        """
        self.history.append(timestamp)
        self.balance_history.append(deepcopy(self.balance))
        self.price_history.append(deepcopy(price_table))

    def calculate_total_balance(
        self,
        balance: Balance,
        prices: PriceTable,
        base_price: Literal["mid", "last", "best"] = "mid",
        optimistic: bool = False,
    ) -> float:
        """
        Get the last total balance of the agent.

        Parameters
        ----------
        balance : Balance
            The balance of the agent.
        prices : PriceTable
            The price table of the agent.
        base_price : Literal["mid", "last", "best"]
            The base price to use for the calculation.
        optimistic : bool
            If True, the balance is calculated such that
            the agent receives the maximum possible balance.
            If False, the balance is calculated such that
            the agent receives the minimum possible balance.

        Returns
        -------
        total_balance : float
            The last balance of the agent.
        """
        total_balance = balance.money + balance.held_money
        total_stock = balance.stock + balance.held_stock

        if base_price == "mid":
            total_balance += total_stock * prices.mid_price
        elif base_price == "last":
            price = prices.last_ask_price if optimistic else prices.last_bid_price
            total_balance += total_stock * price
        elif base_price == "best":
            price = prices.best_ask_price if optimistic else prices.best_bid_price
            total_balance += total_stock * price
        else:
            raise ValueError(f"Invalid base price: {base_price}")

        return total_balance

    def last_total_balance(
        self,
        base_price: Literal["mid", "last", "best"] = "mid",
        optimistic: bool = False,
    ) -> float:
        """
        Get the last total balance of the agent.

        Parameters
        ----------
        base_price : Literal["mid", "last", "best"]
            The base price to use for the calculation.
        optimistic : bool
            If True, the balance is calculated such that
            the agent receives the maximum possible balance.

        Returns
        -------
        total_balance : float
            The last total balance of the agent.
        """
        return self.calculate_total_balance(
            self.balance, self.price_history[-1], base_price, optimistic
        )

    def initial_total_balance(
        self,
        base_price: Literal["mid", "last", "best"] = "mid",
        optimistic: bool = False,
    ) -> float:
        return self.calculate_total_balance(
            self.balance_history[0], self.price_history[0], base_price, optimistic
        )

    def total_balance_history(
        self,
        base_price: Literal["mid", "last", "best"] = "mid",
        optimistic: bool = False,
    ) -> list[float]:
        """
        Get the total balance history of the agent.

        Parameters
        ----------
        base_price : Literal["mid", "last", "best"]
            The base price to use for the calculation.
        optimistic : bool
            If True, the balance is calculated such that
            the agent receives the maximum possible balance.
        """
        return [
            self.calculate_total_balance(balance, prices, base_price, optimistic)
            for balance, prices in zip(self.balance_history, self.price_history)
        ]
