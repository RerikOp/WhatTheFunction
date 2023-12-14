import abc
from misc import Line, LocalCoord
from typing import List, Tuple


class FunctionExporter(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def to_function(lines: List[Line], name: str) -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        pass
