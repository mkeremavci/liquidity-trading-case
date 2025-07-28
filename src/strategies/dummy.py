# © 2025 kerem.ai · All rights reserved.

from datetime import timedelta

from src.backtest import Agent, LOBSnapshot
from src.data import Order

from . import STRATEGIES


@STRATEGIES.register("dummy")
class DummyAgent(Agent):
    """
    An agent that does nothing.
    """

    def __init__(self, **kwargs) -> None:
        # Initialize the agent
        Agent.__init__(self, **kwargs)

    def strategy(self, book: LOBSnapshot, latency: timedelta) -> list[Order]:
        return []
