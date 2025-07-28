# © 2025 kerem.ai · All rights reserved.

from typing import Callable

from src.backtest import Agent


class Registry(dict[str, type[Agent]]):
    """
    A wrapper on the built-in dictionary to register and manage agents.
    """

    def __init__(self, *args, **kwargs):
        super(Registry, self).__init__(*args, **kwargs)

    @classmethod
    def _register(
        cls, module_dict: "Registry", module_name: str, module: type[Agent]
    ) -> None:
        """
        Register the agent to the given registry with the given name.

        Parameters
        ----------
        module_dict : Registry
            The registry to register the agent to.
        module_name : str
            The name of the agent to register.
        module : Agent
            The agent to register.
        """
        assert module_name not in module_dict
        module_dict[module_name.lower()] = module

    def register(
        self,
        module_name: str,
        module: type[Agent] | None = None,
    ) -> Callable | None:
        """
        Register the agent to the given registry with the given name.
        If the module is not provided, it returns a decorator to register the agent.

        Parameters
        ----------
        module_name : str
            The name of the agent to register.
        module : type[Agent] | None, optional
            The agent to register.

        Returns
        -------
        Callable | None
            The decorator function to register the agent \
            or None if the function is called directly.
        """
        # Register when this function is called
        if module is not None:
            Registry._register(self, module_name, module)
            return

        # Register when used as a decorator
        def register_func(fn: type[Agent]) -> type[Agent]:
            """
            Register the agent with the given name.

            Parameters
            ----------
            fn : Agent
                The agent to register.
            """
            Registry._register(self, module_name, fn)
            return fn

        return register_func

    def __getitem__(self, item: str) -> type[Agent]:
        """
        Get the agent with the given name.
        """
        return super(Registry, self).__getitem__(item.lower())


# Define the global registry for strategies
STRATEGIES = Registry()

# Import the strategies and register them
from .dummy import *
from .ewma import *
