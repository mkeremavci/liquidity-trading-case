# © 2025 kerem.ai · All rights reserved.

from pathlib import Path

from .order import Order


class Parser:
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

    Parameters
    ----------
    filepath : str | Path
        The path to the order data file.
    """

    def __init__(self, filepath: str | Path) -> None:
        # Validate and store the filepath for the order data
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"File {filepath} does not exist")

        self._file = open(self.filepath, "r")
        self._is_open = True

    @property
    def is_open(self) -> bool:
        """
        Check if the file is open.
        """
        return self._is_open

    def close(self) -> None:
        """
        Close the file object.
        """
        if self._is_open:
            self._file.close()
            self._is_open = False

    def get_next_order(self) -> Order | None:
        """
        Get the next order from the file.

        Returns
        -------
        order : Order | None
            The next order from the file.
            If the file is not open or line is not valid, None is returned.
        """
        # If the file is not open, return None
        if not self._is_open:
            return None

        # Read the next line from the file
        line = self._file.readline()

        # If the line is empty, close the file and return None
        if not line:
            self.close()
            return None

        # Parse the order from the line
        return self.parse_order(line)

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
