# © 2025 kerem.ai · All rights reserved.

import argparse
import inspect
import pickle
from datetime import datetime
from types import UnionType
from typing import Any, Literal, get_args, get_origin
from pathlib import Path

from src import STRATEGIES
from src.backtest import Agent, Backtest
from src.data import order


def parse_args() -> dict[str, Any]:
    """
    Parse the command line arguments.

    Returns
    -------
    args : dict[str, Any]
        The command line arguments.
    """
    parser = argparse.ArgumentParser(description="backtest a strategy on a given file")
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()),
        required=True,
        help="name/key of the strategy to use for backtesting",
    )
    parser.add_argument(
        "--filepath",
        type=str,
        required=True,
        help="path to the historical order data file",
    )
    parser.add_argument(
        "--latency",
        type=float,
        default=0.0,
        help="latency between the network and the BIST in seconds",
    )
    parser.add_argument(
        "--order-cost",
        type=float,
        default=0.0,
        help="cost of an order in the currency",
    )
    parser.add_argument(
        "--initial-money",
        type=float,
        default=10000.0,
        help="initial money of the agent",
    )
    parser.add_argument(
        "--initial-stock",
        type=int,
        default=0,
        help="initial stock of the agent",
    )
    parser.add_argument(
        "--options",
        type=str,
        nargs="*",
        default=[],
        help="options to pass to the strategy",
    )

    return vars(parser.parse_args())


def resolve_options(agent_cls: type[Agent], options: list[str]) -> dict[str, Any]:
    """
    Resolve the options to pass to the strategy.
    """
    # Split the options into key-value pairs
    options: list[tuple[str, str]] = [option.split("=") for option in options]

    # Get the annotations of the agent's constructor
    annotations = inspect.getfullargspec(agent_cls.__init__).annotations

    # Reconstruct the keyword arguments
    kwargs = {}

    for name, value in options:
        # Skip if the option is not in the annotations
        if name not in annotations:
            continue
        annotation = annotations[name]

        # Try to resolve the value
        try:
            kwargs[name] = cast_value(value, annotation)
        except BaseException:
            continue

    return kwargs


def cast_value(value: str, annotation: Any) -> Any:
    """
    Cast the value to the given annotation.
    """
    origin = get_origin(annotation)

    if origin is UnionType:
        sub_origins = get_args(annotation)
        for sub_origin in sub_origins:
            try:
                return cast_value(value, sub_origin)
            except BaseException:
                continue
        raise ValueError(f"Invalid value for {value}: {annotation}")
    # If Literal, check if the value is in the allowed values
    elif origin is Literal:
        if value not in get_args(annotation):
            raise ValueError(f"Invalid value for {value}: {annotation}")
        return value
    elif origin in (dict, list, tuple, set):
        return origin(eval(value))
    elif annotation in (dict, list, tuple, set):
        return annotation(eval(value))
    elif annotation in (float, int, str, bool):
        return annotation(value)
    elif annotation is None or annotation is type(None):
        return None
    else:
        raise ValueError(f"Invalid value for {value}: {annotation}")


def main(
    strategy: str,
    filepath: str,
    latency: float = 0.0,
    order_cost: float = 0.0,
    initial_money: float = 10000.0,
    initial_stock: int = 0,
    options: list[str] = [],
) -> None:
    """
    Run a backtest with the specified strategy on the given data file.

    Parameters
    ----------
    strategy : str
        The name/key of the strategy to use for backtesting.
    filepath : str
        The path to the historical order data file.
    latency : float, optional
        The latency between the network and the BIST in seconds.
        Default is 0.0.
    order_cost : float, optional
        The cost of an order in the currency.
        Default is 0.0.
    initial_money : float, optional
        The initial money of the agent.
        Default is 10000.0.
    initial_stock : int, optional
        The initial stock of the agent.
        Default is 0.
    options : list[str], optional
        The options to pass to the strategy.
        Default is an empty list.
    """
    # Get the strategy agent class
    agent_cls = STRATEGIES[strategy]

    # Resolve its options
    kwargs = resolve_options(agent_cls, options)

    # Create the agent
    agent = agent_cls(
        order_cost=order_cost,
        initial_money=initial_money,
        initial_stock=initial_stock,
        **kwargs,
    )

    # Create the backtest
    backtest = Backtest(
        agent=agent,
        filepath=filepath,
        latency=latency,
    )

    # Run the backtest
    backtest.run()

    # Export the limit order book if dummy agent is used
    if strategy == "dummy":
        output_path = backtest.parser.filepath.with_stem("limit-order-book")
        backtest.export_lob(output_path)
    else:
        # Export the agent's history, otherwise
        result_dir = Path(__file__).parents[1] / "results"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = (
            result_dir / f"{strategy}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )

        with open(result_path, "wb") as f:
            pickle.dump(
                {
                    "balance": backtest.agent.balance,
                    "timestamps": backtest.agent.history,
                    "price_history": backtest.agent.price_history,
                    "balance_history": backtest.agent.balance_history,
                },
                f,
            )


if __name__ == "__main__":
    args = parse_args()
    main(**args)
