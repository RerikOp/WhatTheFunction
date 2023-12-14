from UIStyle import UIStyle
from misc import CanvasCoord, LocalCoord, Point, dist_line_point, dist_point_point, Line, float_to_str
from typing import List, Optional, Literal, Tuple, Callable
import tkinter as tk
from enum import Enum, auto

from scipy import interpolate


class SnapMode(Enum):
    # snap to the y value of the closest point
    Closest_Y = auto()
    Corner = auto()
    Horizontal = auto()
    Vertical = auto()
    Corner_Only = auto()

    def __str__(self):
        return str(self.name).replace("_", " ")


class DrawingPanel:
    def __init__(self, canvas: tk.Canvas, style: UIStyle):
        self.canvas = canvas
        self.style = style
        # styling stuff
        self.canvas.config(bg=self.style.canvas_bg_color)
        self.grid_tag = "Grid"
        self.numbers_tag = "Number"
        self.axes_tag = "Axes"

        self.hit_box_extension = 3
        self.width, self.height = self.canvas.winfo_reqwidth(), self.canvas.winfo_reqheight()

        self.zoom_level = 5
        self.num_zooms = 1
        self.__grid_spacing = 28

        self.snap_dist_points = self.grid_spacing // 4
        self.snap_dist_grid = self.grid_spacing // 5

        # SYNC WITH INFO PANEL
        self.snap_modes: List[SnapMode] = []
        # extrapolate left by using the n leftmost points
        self.__extrapolate_left: int = 2
        # extrapolate right by using the n rightmost points
        self.__extrapolate_right: int = 2
        self.__extrapolate_store = None

        self.is_alt_dragging = False
        self.is_panning = False
        self.pan_start = CanvasCoord(-1, -1)
        self.alt_drag_start = CanvasCoord(-1, -1)
        self.origin = CanvasCoord(self.width // 2, self.height // 2)
        self.__points: List[Point] = []

        self.canvas.bind("<Button-1>", self.on_button1_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.canvas.bind("<Control-Button-1>", self.on_drag)
        self.canvas.bind("<Alt-Button-1>", self.on_alt_drag)

        self.canvas.bind("<Button-2>", self.on_drag)
        self.canvas.bind("<ButtonRelease-2>", self.on_button_release)
        self.canvas.bind("<B2-Motion>", self.on_panning)
        self.canvas.bind("<Button-3>", self.on_button3_click)
        self.canvas.bind("<B3-Motion>", self.on_button3_click)

        self.canvas.bind("<Configure>", self.on_resize)
        self.dragged_point: Optional[Point] = None

    @property
    def extrapolate_left(self):
        return self.__extrapolate_left

    @extrapolate_left.setter
    def extrapolate_left(self, value):
        self.__extrapolate_left = value
        self.redraw_lines()

    @property
    def extrapolate_right(self):
        return self.__extrapolate_right

    @extrapolate_right.setter
    def extrapolate_right(self, value):
        self.__extrapolate_right = value
        self.redraw_lines()

    @property
    def points(self):
        self.__points.sort()
        return self.__points

    @property
    def grid_spacing(self):
        return self.__grid_spacing - self.__zoom()

    def clear_canvas(self):
        self.points.clear()
        self.redraw_canvas()

    def __zoom(self, factor=None):
        if factor is None:
            return self.num_zooms % 8 * 2
        if factor > 0:
            if self.num_zooms % 8 == 0:
                self.zoom_level *= 2
                self.num_zooms -= 1
            self.num_zooms -= 1
        else:
            self.num_zooms += 1
            if self.num_zooms % 8 == 0:
                self.zoom_level /= 2
                self.num_zooms += 1

        return self.num_zooms % 8 * 2

    def zoom(self, event):
        factor = 1 if event.delta > 0 else -1
        cac = CanvasCoord(event.x, event.y)
        pre_local = self.to_local_coords(cac)
        self.__zoom(factor)
        post_cac = self.to_canvas_coords(pre_local)  # keep mouse at same local coordinate as before the zoom
        dx = cac.x - post_cac.x
        dy = cac.y - post_cac.y
        self.origin.x += int(dx)
        self.origin.y += int(dy)
        self.redraw_canvas()

    def on_resize(self, event):
        if event is not None and (event.width != self.width or event.height != self.height):
            self.width, self.height = event.width, event.height
            self.redraw_canvas()

    def on_button3_click(self, event):
        cac = CanvasCoord(event.x, event.y)
        p = self.intersects_point(cac)
        if p is not None and self.dragged_point is None:
            self.__points.remove(p)
            self.canvas.delete(p.id)
            self.redraw_lines()

    def to_canvas_coords(self, loc: LocalCoord) -> CanvasCoord:
        x = loc.x * self.grid_spacing
        y = loc.y * self.grid_spacing
        scaled_x = self.origin.x + x * self.zoom_level
        scaled_y = self.origin.y - y * self.zoom_level
        cac = CanvasCoord(scaled_x, scaled_y)
        return cac

    def to_local_coords(self, cac: CanvasCoord) -> LocalCoord:
        x = (cac.x - self.origin.x) / (self.grid_spacing * self.zoom_level)
        y = (cac.y - self.origin.y) / (self.grid_spacing * self.zoom_level)
        loc = LocalCoord(x, -y)
        return loc

    def redraw_numbers(self):
        self.canvas.delete(self.numbers_tag)
        vert_offset = self.origin.x % self.grid_spacing
        horiz_offset = self.origin.y % self.grid_spacing

        for i, x in enumerate(range(0 + vert_offset, self.width - vert_offset, self.grid_spacing)):
            grid = (x - self.origin.x) // self.grid_spacing
            if grid != 0 and grid % 5 == 0:
                t = float_to_str(grid / self.zoom_level)
                self.canvas.create_text(x, min(max(self.origin.y + 15, 15), self.height - 15), text=t,
                                        tags=self.numbers_tag,
                                        font=self.style.font_small,
                                        fill=self.style.text_color,
                                        anchor="center")
        for y in range(0 + horiz_offset, self.height - horiz_offset, self.grid_spacing):
            grid = -(y - self.origin.y) // self.grid_spacing
            if grid != 0 and grid % 5 == 0:
                t = float_to_str(grid / self.zoom_level)
                self.canvas.create_text(min(max(self.origin.x + len(t) * 5, len(t) * 5), self.width - len(t) * 5), y,
                                        text=t, tags=self.numbers_tag,
                                        font=self.style.font_small,
                                        fill=self.style.text_color,
                                        anchor="center")

    def redraw_grid(self):
        self.canvas.delete(self.grid_tag)
        horiz_offset = self.origin.y % self.grid_spacing
        vert_offset = self.origin.x % self.grid_spacing

        for x in range(0 + vert_offset, self.width, self.grid_spacing):
            grid = (x - self.origin.x) // self.grid_spacing
            self.canvas.create_line(x, 0, x, self.height, fill=self.style.grid_color,
                                    width=1 if grid % 5 != 0 else 2,
                                    tags=(self.grid_tag + "Y", self.grid_tag))

        for y in range(0 + horiz_offset, self.height, self.grid_spacing):
            grid = -(y - self.origin.y) // self.grid_spacing
            self.canvas.create_line(0, y, self.width, y, fill=self.style.grid_color,
                                    width=1 if grid % 5 != 0 else 2,
                                    tags=(self.grid_tag + "X", self.grid_tag))

    def blink_point(self, p: Point, blink_color="red"):
        if p.id is None:
            return
        else:
            color = self.canvas.itemcget(p.id, "fill")
            if color == blink_color:
                return
            self.canvas.itemconfig(p.id, fill=blink_color)
            self.canvas.after(1000, lambda: self.canvas.itemconfig(p.id, fill=self.style.point_fill))

    def get_extrapolate(self) -> None | List[Tuple[CanvasCoord, CanvasCoord]]:
        if self.__extrapolate_store is not None:
            return self.__extrapolate_store

        # Either segments or points
        ep_coords: List[Tuple[CanvasCoord, CanvasCoord]] = []

        extrapolate_left = min(self.extrapolate_left, len(self.points))
        extrapolate_right = min(self.extrapolate_right, len(self.points))

        def to_cac_xy(_points):
            _cac_x = []
            _cac_y = []
            for _p in _points:
                _cac = self.to_canvas_coords(_p.loc)
                _cac_x.append(_cac.x)
                _cac_y.append(_cac.y)
            return _cac_x, _cac_y

        def extrapolate(_xs, func):
            coords = []
            _x0 = _xs[0]
            _y0 = float(func(_x0))
            for i, _x1 in enumerate(_xs[1:]):
                _y1 = float(func(_x1))
                coords.append((CanvasCoord(_x0, _y0), CanvasCoord(_x1, _y1)))
                _y0 = _y1
                _x0 = _x1
            return coords

        # if we only extrapolate 1 segment (2 Points) don't use scipy:
        if extrapolate_left == 2:
            # get leftmost two points (self.points are always ordered)
            line = Line(self.points[0].loc, self.points[1].loc)
            f = line.get_function()
            # the location of the left border of the x-axis
            loc = self.to_local_coords(CanvasCoord(0, self.origin.y))
            loc.y = f(loc.x)
            cac0 = self.to_canvas_coords(loc)
            cac1 = self.to_canvas_coords(line.p0)
            ep_coords.append((cac0, cac1))
        elif extrapolate_left > 2:
            cac_x, cac_y = to_cac_xy(self.points[:self.extrapolate_left])
            # extrapolate each pixel on the canvas left of leftmost point
            xs = range(0, int(cac_x[0]) - 1)
            if xs.start < xs.stop:
                f = interpolate.interp1d(cac_x, cac_y, kind="quadratic", fill_value="extrapolate", copy=False,
                                         assume_sorted=True)
                extr = extrapolate(xs, f)
                # make the extrapolated points connect to the leftmost point
                leftmost_point = CanvasCoord(int(cac_x[0]), int(cac_y[0]))
                rightmost_extr_point = extr[-1][1]
                extr.append((leftmost_point, rightmost_extr_point))
                ep_coords += extr
        if extrapolate_right == 2:
            line = Line(self.points[-2].loc, self.points[-1].loc)
            f = line.get_function()
            loc = self.to_local_coords(CanvasCoord(self.width, self.origin.y))
            loc.y = f(loc.x)
            cac0 = self.to_canvas_coords(loc)
            cac1 = self.to_canvas_coords(line.p1)
            ep_coords.append((cac0, cac1))
        elif extrapolate_right > 2:
            cac_x, cac_y = to_cac_xy(self.points[-self.extrapolate_right:])
            # extrapolate each pixel on the canvas right of rightmost point
            xs = range(int(cac_x[-1]), self.width)
            if xs.start < xs.stop:
                f = interpolate.interp1d(cac_x, cac_y, kind="quadratic", fill_value="extrapolate", copy=False,
                                         assume_sorted=True)
                ep_coords += extrapolate(xs, f)

        self.__extrapolate_store = ep_coords

        return ep_coords

    def redraw_lines(self):
        self.canvas.delete(Line.tag())
        self.__extrapolate_store = None
        lines = self.get_lines()
        for line in lines:
            cac0: CanvasCoord = self.to_canvas_coords(line.p0)
            cac1: CanvasCoord = self.to_canvas_coords(line.p1)
            line.id = self.canvas.create_line(cac0.x, cac0.y, cac1.x, cac1.y, smooth=True, splinesteps=1,
                                              width=self.style.segment_width,
                                              fill=self.style.default_segment_fill,
                                              tags=Line.tag())

        def draw_extrapolate(cac0, cac1):
            _id = self.canvas.create_line(cac0.x, cac0.y, cac1.x, cac1.y, smooth=True, splinesteps=1,
                                          width=self.style.segment_width,
                                          fill=self.style.extrapolate_segment_fill,
                                          tags=(Line.tag()))

        if (res := self.get_extrapolate()) is not None:
            for val in res:
                draw_extrapolate(*val)

        # make sure points are always on top!
        self.canvas.tag_raise(Point.tag())

    def redraw_points(self):
        self.canvas.delete(Point.tag())
        for p in self.points:
            self.redraw_point(p)

    def redraw_point(self, p: Point):
        cac = self.to_canvas_coords(p.loc)
        if p.id is not None:
            self.canvas.delete(p.id)

        id_ = self.canvas.create_oval(cac.x - self.style.point_radius,
                                      cac.y - self.style.point_radius,
                                      cac.x + self.style.point_radius,
                                      cac.y + self.style.point_radius, fill=self.style.point_fill, tags=Point.tag())
        p.id = id_

    def redraw_axes(self):
        self.canvas.delete(self.axes_tag)
        self.canvas.create_line(0, self.origin.y, self.width, self.origin.y, fill=self.style.axes_color, width=2,
                                tags=self.axes_tag)
        self.canvas.create_line(self.origin.x, 0, self.origin.x, self.height, fill=self.style.axes_color, width=2,
                                tags=self.axes_tag)

    def on_drag(self, event):
        self.is_panning = True
        self.pan_start = CanvasCoord(event.x, event.y)

    def on_alt_drag(self, event):
        self.is_alt_dragging = True
        self.alt_drag_start = CanvasCoord(event.x, event.y)

    def on_button1_move(self, event):
        if self.dragged_point is not None:
            cac = CanvasCoord(event.x, event.y)
            if (res := self.snap_and_verify(cac)) is None:
                return
            self.dragged_point.loc = res[1]
            self.redraw_point(self.dragged_point)
            self.redraw_lines()
        elif self.is_panning:
            self.on_panning(event)
        elif self.is_alt_dragging:
            self.on_alt_dragging(event)

    def on_panning(self, event):
        dx = event.x - self.pan_start.x
        dy = event.y - self.pan_start.y
        self.origin.x += dx
        self.origin.y += dy
        self.pan_start = CanvasCoord(event.x, event.y)
        self.redraw_canvas()

    def on_alt_dragging(self, _):
        pass
        # self.canvas.create_rectangle(self.alt_drag_start.x, 0, event.x, self.get_height(), fill="red")

    def snap_and_verify(self, cac: CanvasCoord) -> Optional[Tuple[CanvasCoord, LocalCoord]]:
        new_cac = cac
        if SnapMode.Closest_Y in self.snap_modes:
            sp_y = next(self.get_snap_y_points(cac, self.snap_dist_points), None)
            if sp_y is not None:
                sp_y_cac = self.to_canvas_coords(sp_y.loc)
                new_cac.y = sp_y_cac.y

        def grid_coords(lit: Literal["X", "Y"]) -> List[Tuple[CanvasCoord, CanvasCoord]]:
            # find the coords of the Y or X grid lines and cast them to CanvasCoord
            coords = [self.canvas.coords(_id) for _id in self.canvas.find_withtag(self.grid_tag + lit)]
            coords = [(CanvasCoord(x0, y0), CanvasCoord(x1, y1)) for x0, y0, x1, y1 in coords]
            return coords

        if SnapMode.Corner_Only in self.snap_modes:
            new_cac = self.closest_grid_point(cac)

        if SnapMode.Horizontal in self.snap_modes:
            min_y, dist = min([(cac0.y, dist_line_point(cac0, cac1, cac)) for cac0, cac1 in grid_coords("X")],
                              key=lambda t: t[1])
            if dist <= self.snap_dist_grid:
                new_cac.y = min_y

        if SnapMode.Vertical in self.snap_modes:
            min_x, dist = min([(cac0.x, dist_line_point(cac0, cac1, cac)) for cac0, cac1 in grid_coords("Y")],
                              key=lambda t: t[1])
            if dist <= self.snap_dist_grid:
                new_cac.x = min_x

        if SnapMode.Corner in self.snap_modes:
            next_grid_point = self.closest_grid_point(cac)
            if dist_point_point(next_grid_point, cac) <= self.snap_dist_grid:
                new_cac = next_grid_point

        min_dist = 2 * self.style.point_radius + 2 * self.hit_box_extension
        # Make sure all points are clickable: if not far enough away from other points then blink this point red
        if (interferes := next(filter(lambda p: dist_point_point(self.to_canvas_coords(p.loc),
                                                                 cac) <= min_dist and p != self.dragged_point,
                                      self.points), None)) is not None:
            self.blink_point(interferes)
            return None

        # if on the same X value, the function is not bijective anymore which we don't allow
        new_loc = self.to_local_coords(new_cac)
        if (interferes := next(self.get_x_collision(new_loc), None)) is not None:
            self.blink_point(interferes)
            return None

        return new_cac, new_loc

    def on_button_release(self, _):
        self.dragged_point = None
        self.is_alt_dragging = False
        self.is_panning = False

    def get_lines(self):
        lines: List[Line] = []
        for i, left in enumerate(self.points[:-1]):
            right: Point = self.points[i + 1]
            lines.append(Line(left.loc, right.loc))
        return lines

    def intersects_point(self, cac: CanvasCoord) -> Optional[Point]:
        for p in self.points:
            if dist_point_point(self.to_canvas_coords(p.loc), cac) <= self.hit_box_extension + self.style.point_radius:
                return p
        return None

    def intersects_line(self, cac: CanvasCoord, consider_extension: bool = False) -> Optional[Line]:
        dw = self.style.segment_width + self.hit_box_extension
        lines = self.get_lines()
        for line in lines:
            cac0: CanvasCoord = self.to_canvas_coords(line.p0)
            cac1: CanvasCoord = self.to_canvas_coords(line.p1)
            if dist_line_point(cac0, cac1, cac) <= dw:
                return line

            # if consider_extension and (res := self.get_extrapolate()) is not None:
            #    pass
            """cac0_l, cac1_l, cac0_r, cac1_r = res
            if cac0_l and cac1_l and dist_line_point(cac0_l, cac1_l, cac) <= dw:
                return Line(self.to_local_coords(cac0_l), self.to_local_coords(cac1_l))
    
            if cac0_r and cac1_r and dist_line_point(cac0_r, cac1_r, cac) <= dw:
                return Line(self.to_local_coords(cac0_r), self.to_local_coords(cac1_r))"""

    def on_button1_click(self, event):
        cac = CanvasCoord(event.x, event.y)
        if (p := self.intersects_point(cac)) is not None:
            self.dragged_point = p
            return
        # if the new location of the point is valid, we add it
        if (res := self.snap_and_verify(cac)) is not None:
            new_loc = res[1]
            p = Point(new_loc)
            self.__points.append(p)
            self.dragged_point = p
            self.redraw_point(p)
            self.redraw_lines()

    def get_x_collision(self, loc: LocalCoord):
        return filter(lambda p: p != self.dragged_point and loc.x == p.loc.x, self.points)

    def get_snap_y_points(self, cac: CanvasCoord, snap_dist):
        return filter(
            lambda p: p != self.dragged_point and abs(cac.y - self.to_canvas_coords(p.loc).y) <= snap_dist,
            self.points)

    def closest_grid_point(self, cac: CanvasCoord) -> CanvasCoord:
        x_offset = self.origin.x % self.grid_spacing
        y_offset = self.origin.y % self.grid_spacing
        kx_0 = cac.x // self.grid_spacing
        ky_0 = cac.y // self.grid_spacing

        x_0 = int(kx_0 * self.grid_spacing + x_offset)
        x_1 = int((kx_0 + 1) * self.grid_spacing + x_offset)
        y_0 = int(ky_0 * self.grid_spacing + y_offset)
        y_1 = int((ky_0 + 1) * self.grid_spacing + y_offset)

        corners = [CanvasCoord(x_0, y_0), CanvasCoord(x_0, y_1), CanvasCoord(x_1, y_0), CanvasCoord(x_1, y_1)]
        min_dist = min([(corner, dist_point_point(corner, cac)) for corner in corners], key=lambda t: t[1])
        return min_dist[0]

    def redraw_canvas(self):
        self.redraw_grid()
        self.redraw_axes()
        self.redraw_numbers()
        self.redraw_points()
        self.redraw_lines()
