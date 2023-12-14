import time
import tkinter as tk
import dataclasses
import math
from tkinter import ttk
from typing import Optional, Iterable, Callable, Any, Tuple
import threading


@dataclasses.dataclass
class CanvasCoord:
    x: int | float
    y: int | float


@dataclasses.dataclass
class LocalCoord:
    x: float
    y: float


def dist_line_point(p0: LocalCoord | CanvasCoord, p1: LocalCoord | CanvasCoord, p: LocalCoord | CanvasCoord):
    assert type(p0) == type(p1) == type(p), "Can only compare equal types"
    px = p1.x - p0.x
    py = p1.y - p0.y
    norm = px * px + py * py
    u = ((p.x - p0.x) * px + (p.y - p0.y) * py) / float(norm)
    if u > 1:
        u = 1
    elif u < 0:
        u = 0
    x = p0.x + u * px
    y = p0.y + u * py
    dx = x - p.x
    dy = y - p.y
    return (dx * dx + dy * dy) ** .5


def dist_point_point(p0: LocalCoord | CanvasCoord, p1: LocalCoord | CanvasCoord):
    return math.sqrt(math.pow(p0.x - p1.x, 2) + math.pow(p0.y - p1.y, 2))


@dataclasses.dataclass()
class Point:
    loc: LocalCoord
    _id: Optional[int] = dataclasses.field(default=None)

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, LocalCoord):
            return self.loc == other
        if isinstance(other, Point):
            return self.loc == other.loc
        raise TypeError(f"'__eq__' not supported between instances of '{type(self)}' and '{type(other)}'")

    def __lt__(self, other):
        if isinstance(other, Point):
            return self.loc.x <= other.loc.x
        if isinstance(other, LocalCoord):
            return self.loc.x <= other.x
        raise TypeError(f"'<' not supported between instances of '{type(self)}' and '{type(other)}'")

    @staticmethod
    def tag():
        return "Point"

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


@dataclasses.dataclass()
class Line:
    p0: LocalCoord
    p1: LocalCoord
    _id: Optional[int] = dataclasses.field(default=None)

    @staticmethod
    def tag():
        return "Line"

    @property
    def slope(self):
        if (self.p1.x - self.p0.x) == 0:
            return None
        return (self.p1.y - self.p0.y) / (self.p1.x - self.p0.x)

    def get_function(self) -> Callable[[Any], Any | None]:
        assert self.slope is not None, "Slope cannot be None how did you do this, please write a bug report"

        def fn(x):
            y_intercept = self.p0.y - self.slope * self.p0.x
            return self.slope * x + y_intercept

        return fn

    def stringify_function(self) -> str:
        assert self.slope is not None, "Slope cannot be None how did you do this, please write a bug report"
        # def f_to_str(f): return str(round(f, 2)).replace(".", "_").replace("-", "neg")
        # header = f"def x0_{f_to_str(self.p0.x)}_y0_{f_to_str(self.p0.y)}_to_x1_{f_to_str(self.p1.x)}_y1_{f_to_str(self.p1.y)}:"
        y_intercept = self.p0.y - self.slope * self.p0.x
        impl = f"lambda x: {self.slope} * x + {y_intercept}"
        return impl

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def from_rgb(rgb: Tuple[int, int, int]):
    return "#%02x%02x%02x" % rgb


def float_to_str(val, max_len=10):
    if val is None:
        return "None"

    a, _ = str(val).split(".")
    # if rounding to max_len digits looses too much precision
    if val < 0:
        rounded = round(val, max_len - len(a) - 2)
    else:
        rounded = round(val, max_len - len(a) - 1)

    if rounded == 0 and val != 0 or len(str(rounded)) > max_len:
        return "{:.2e}".format(val)

    return str(rounded)


def transition_bg(widget, start_color: Tuple[int, int, int], end_color: Tuple[int, int, int], steps,
                  ui_lock: threading.Lock):
    def tf():
        sleep_time = 1000 // steps / 1000
        with ui_lock:
            for current_step in range(steps):
                r = int((1 - current_step / steps) * start_color[0] + (current_step / steps) * end_color[0])
                g = int((1 - current_step / steps) * start_color[1] + (current_step / steps) * end_color[1])
                b = int((1 - current_step / steps) * start_color[2] + (current_step / steps) * end_color[2])
                widget.configure(bg=from_rgb((r, g, b)))
                time.sleep(sleep_time)
            widget.configure(bg=from_rgb(end_color))
            time.sleep(sleep_time)

    threading.Thread(target=tf, daemon=True).start()


class CheckBox(tk.Canvas):
    def __init__(self, master, checked_color, unchecked_color, disabled_color, size=15, *args, **kwargs):
        self._checked = False
        if "checked" in kwargs:
            self._checked = kwargs.pop("checked")
        super().__init__(master, width=size, height=size, *args, **kwargs)
        self.checked_color = checked_color
        self.unchecked_color = unchecked_color
        self.disabled_color = disabled_color

        self.rect = self.create_rectangle(0, 0, size + 2, size + 2, outline=self.unchecked_color,
                                          fill=self.unchecked_color)

        self._command = None

        self._disabled = tk.BooleanVar()
        self._disabled.trace_add('write', self.__on_disabled_change)
        self.set_checked(self._checked)
        self.bind("<Button-1>", self.__toggle)

    def configure(self, cnf=None, **kwargs):
        if cnf is not None:
            kwargs.update(cnf)

        if "command" in kwargs:
            self._command = kwargs.pop("command")

        tk.Canvas.configure(self, **kwargs)

    # alias
    config = configure

    def __toggle(self, *args, **kwargs):
        if self.disabled:
            return
        self.set_checked(not self._checked)
        if self._command:
            self._command(self._checked)

    def set_checked(self, value):
        self._checked = value
        fill_color = self.checked_color if self._checked else self.unchecked_color
        self.itemconfig(self.rect, fill=fill_color)

    def get_checked(self):
        return self._checked

    def __on_disabled_change(self, *args):
        if self.disabled:
            fill_color = self.disabled_color
        else:
            if self._checked:
                fill_color = self.checked_color
            else:
                fill_color = self.unchecked_color

        self.itemconfig(self.rect, fill=fill_color)
        if not self.disabled and self._command:
            self._command(self._checked)

    @property
    def disabled(self):
        return self._disabled.get()

    @disabled.setter
    def disabled(self, value):
        self._disabled.set(value)


def clip_line(bottom_left: LocalCoord | CanvasCoord, top_right: LocalCoord | CanvasCoord, p0: LocalCoord | CanvasCoord,
              p1: LocalCoord | CanvasCoord) -> Tuple[LocalCoord, LocalCoord] | Tuple[CanvasCoord, CanvasCoord]:
    assert type(bottom_left) is type(top_right) is type(p0) is type(p1), "Can only compare equal types"

    T = type(bottom_left)
    INSIDE = 0
    LEFT = 1
    RIGHT = 2
    BOTTOM = 4
    TOP = 8

    x_max = top_right.x
    y_max = bottom_left.y
    x_min = bottom_left.x
    y_min = top_right.y

    def compute_code(x, y):
        code = INSIDE
        if x < x_min:  # to the left of rectangle
            code |= LEFT
        elif x > x_max:  # to the right of rectangle
            code |= RIGHT
        if y < y_min:  # below the rectangle
            code |= BOTTOM
        elif y > y_max:  # above the rectangle
            code |= TOP
        return code

    x1, y1, x2, y2 = p0.x, p0.y, p1.x, p1.y
    code1 = compute_code(x1, y1)
    code2 = compute_code(x2, y2)
    accept = False

    while True:
        if code1 == 0 and code2 == 0:
            accept = True
            break
        elif (code1 & code2) != 0:
            break
        else:
            x = 1.0
            y = 1.0
            if code1 != 0:
                code_out = code1
            else:
                code_out = code2
            if code_out & TOP:
                x = x1 + (x2 - x1) * (y_max - y1) / (y2 - y1)
                y = y_max
            elif code_out & BOTTOM:
                x = x1 + (x2 - x1) * (y_min - y1) / (y2 - y1)
                y = y_min
            elif code_out & RIGHT:
                y = y1 + (y2 - y1) * (x_max - x1) / (x2 - x1)
                x = x_max
            elif code_out & LEFT:
                y = y1 + (y2 - y1) * (x_min - x1) / (x2 - x1)
                x = x_min
            if code_out == code1:
                x1 = x
                y1 = y
                code1 = compute_code(x1, y1)
            else:
                x2 = x
                y2 = y
                code2 = compute_code(x2, y2)
    return T(x1, y1), T(x2, y2)
