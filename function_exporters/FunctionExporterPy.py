from function_exporters.FunctionExporter import FunctionExporter
from misc import Line, LocalCoord
from typing import List, Tuple


class FunctionExporterPy(FunctionExporter):

    @staticmethod
    def name() -> str:
        return "Python"

    @staticmethod
    def to_function(lines: List[Line], name: str) -> str:
        s = f"def {name}(x):\n"
        lines = sorted(lines, key=lambda l: l.p0.x)
        tail = ""
        # special case:
        if len(lines) == 1:
            s += f"\treturn ({lines[0].stringify_function()})(x)\n"
            return s

        if lines:
            line = lines.pop(0)
            s += f"\tif(x <= {line.p1.x}):\n\t\treturn ({line.stringify_function()})(x)\n"

        if lines:
            line = lines.pop(-1)
            tail = f"\tif(x >= {line.p0.x}):\n\t\treturn ({line.stringify_function()})(x)\n"

        for line in lines:
            s += f"\tif({line.p0.x} <= x <= {line.p1.x}):\n\t\treturn ({line.stringify_function()})(x)\n"

        s += tail

        return s
