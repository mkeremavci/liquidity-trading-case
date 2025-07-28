# © 2025 kerem.ai · All rights reserved.

from enum import IntEnum


class OrderSourceEnum(IntEnum):
    """
    Enum for the source of the order.

    HISTORICAL (1) : The order is from the historical order data.
    NETWORK2BIST (2) : The order is from the network to the BIST.
    BIST2NETWORK (3) : The order is from the BIST to the network.
    NO_ORDER (0) : There is no order in any queue.
    """

    HISTORICAL = 1
    NETWORK2BIST = 2
    BIST2NETWORK = 3
    NO_ORDER = 0
