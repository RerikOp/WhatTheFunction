import threading
import tkinter as tk
from typing import Dict, Optional, Tuple, Literal

from UIStyle import UIStyle
from misc import CheckBox, CanvasCoord, Point, LocalCoord, transition_bg, hex_to_rgb, float_to_str

from DrawingPanel import DrawingPanel, SnapMode


class InfoPanel:
    def __init__(self, canvas: tk.Canvas, drawing_panel: DrawingPanel, style: UIStyle):
        self.drawing_panel = drawing_panel
        self.canvas = canvas
        self.style = style

        self.padx = 5
        self.max_digits = 10
        # to prevent weird looking UI
        self.ui_lock = threading.Lock()

        self.__next_row = 0
        self.style.init_heading_label(text="Snap Mode", master=self.canvas).grid(row=self.__get_next_row(), column=1,
                                                                                 pady=5)

        self.snap_checkboxes: Dict[SnapMode, CheckBox] = self.__init_snap_checkboxes()
        self.__place_snap_checkboxes()

        self.style.init_heading_label(text="Points", master=self.canvas).grid(row=self.__get_next_row(),
                                                                              column=1,
                                                                              pady=5)

        self.add_btn, self.enter_x, self.enter_y = self.__init_add_point()
        self.__place_add_point()
        self.style.init_button(master=self.canvas, text="CLEAR ALL", command=self.drawing_panel.clear_canvas).grid(
            row=self.__get_next_row(),
            columnspan=3,
            sticky=tk.N + tk.S + tk.W + tk.E,
            pady=(5, 0), padx=5)

        self.style.init_label(master=self.canvas, text="Function").grid(row=self.__get_next_row(),
                                                                        column=1,
                                                                        pady=5)
        self.extrapolate_left, self.extrapolate_right = self.__init_extrapolate_entries()

        self.__place_extrapolate_entries()
        self.val_x, self.val_y, self.val_fx = self.style.init_entry(master=self.canvas,
                                                                    state="readonly"), self.style.init_entry(
            master=self.canvas, state="readonly"), self.style.init_entry(master=self.canvas, state="readonly")

        self.__place_coords()

        self.export_btn, self.func_name = self.__init_export_func()
        row = self.__get_next_row()
        self.export_btn.grid(row=row, column=2, sticky=tk.N + tk.S + tk.W + tk.E, pady=5, padx=self.padx)
        self.func_name.grid(row=row, column=0, columnspan=2, sticky=tk.N + tk.S + tk.W + tk.E, pady=5,
                            padx=(self.padx, 0))

        self.canvas.configure(bg=self.style.info_panel_bg_color)

    def __get_next_row(self):
        r = self.__next_row
        self.__next_row += 1
        return r

    def __init_snap_checkboxes(self):
        checkboxes = {mode: self.style.init_checkbox(master=self.canvas) for mode in SnapMode}

        for mode, c in checkboxes.items():
            c.set_checked(mode in self.drawing_panel.snap_modes)  # sync with backend

        def add_command(cb: CheckBox, mode: SnapMode):
            cb.configure(command=lambda is_checked: self.__set_snap_mode(mode, is_checked))

        add_command(checkboxes[SnapMode.Corner], SnapMode.Corner)
        add_command(checkboxes[SnapMode.Vertical], SnapMode.Vertical)
        add_command(checkboxes[SnapMode.Horizontal], SnapMode.Horizontal)
        add_command(checkboxes[SnapMode.Corner_Only], SnapMode.Corner_Only)
        add_command(checkboxes[SnapMode.Closest_Y], SnapMode.Closest_Y)

        return checkboxes

    def __place_snap_checkboxes(self):
        row = self.__get_next_row()
        self.style.init_label(master=self.canvas, text=str(SnapMode.Corner)).grid(row=row, column=0)
        self.snap_checkboxes[SnapMode.Corner].grid(row=row + 1, column=0)
        self.style.init_label(master=self.canvas, text=str(SnapMode.Horizontal)).grid(row=row, column=1)
        self.snap_checkboxes[SnapMode.Horizontal].grid(row=row + 1, column=1)
        self.style.init_label(master=self.canvas, text=str(SnapMode.Vertical)).grid(row=row, column=2)
        self.snap_checkboxes[SnapMode.Vertical].grid(row=row + 1, column=2)
        self.__get_next_row()
        self.style.init_label(master=self.canvas, text=str(SnapMode.Closest_Y)).grid(
            row=self.__get_next_row(), column=1)
        self.snap_checkboxes[SnapMode.Closest_Y].grid(row=self.__get_next_row(), column=1)

        self.style.init_label(master=self.canvas, text=str(SnapMode.Corner_Only)).grid(
            row=self.__get_next_row(), column=1)
        self.snap_checkboxes[SnapMode.Corner_Only].grid(row=self.__get_next_row(), column=1)

    def __set_snap_mode(self, mode: SnapMode, is_checked: bool):
        combinable = (SnapMode.Horizontal, SnapMode.Vertical, SnapMode.Corner)
        combinable_nodes = [m for m in self.drawing_panel.snap_modes if m in combinable]
        if is_checked:
            if mode in self.drawing_panel.snap_modes:
                return
            if mode in combinable:
                new_modes = combinable_nodes + [mode]
            else:
                new_modes = [mode]
        else:
            if mode not in self.drawing_panel.snap_modes:
                return
            if mode in combinable:
                new_modes = combinable_nodes
                new_modes.remove(mode)
            else:
                new_modes = []

        self.drawing_panel.snap_modes = new_modes
        for mode, cb in self.snap_checkboxes.items():
            if mode in new_modes:
                cb.set_checked(True)
            else:
                cb.set_checked(False)

    def __place_coords(self):
        row = self.__get_next_row()
        self.style.init_label(master=self.canvas, text="x").grid(row=row, column=0)
        self.style.init_label(master=self.canvas, text="y").grid(row=row, column=1)
        self.style.init_label(master=self.canvas, text="f(x)").grid(row=row, column=2)
        row = self.__get_next_row()
        self.val_x.grid(row=row, column=0, sticky=tk.N + tk.S + tk.W + tk.E, pady=(5, 0), padx=(self.padx, 0))
        self.val_y.grid(row=row, column=1, sticky=tk.N + tk.S + tk.W + tk.E, pady=(5, 0), padx=self.padx)
        self.val_fx.grid(row=row, column=2, sticky=tk.N + tk.S + tk.W + tk.E, pady=(5, 0), padx=(0, self.padx))

    def on_motion(self, event):
        x, y = event.x, event.y
        self.update_loc_label(x, y)

    def invalid_entry(self, entry):
        transition_bg(entry, hex_to_rgb(self.style.invalid_color),
                      hex_to_rgb(self.style.accent_color), 10, self.ui_lock)

    @staticmethod
    def clear_text(x: tk.Event | tk.Entry, delete_only_if: str = None):
        if type(x) is tk.Event:
            if delete_only_if is None or x.widget.get() == delete_only_if:
                x.widget.delete(0, tk.END)
        if type(x) is tk.Entry:
            if delete_only_if is None or x.get() == delete_only_if:
                x.delete(0, tk.END)

    @staticmethod
    def set_text(entry: tk.Entry, initial_text):
        if entry.get() == "":
            entry.insert(0, initial_text)

    def __init_add_point(self):
        def cast(x, y) -> Optional[LocalCoord]:
            try:
                x = float(x)
            except ValueError:
                self.invalid_entry(self.enter_x)
                return None
            try:
                y = float(y)
            except ValueError:
                self.invalid_entry(self.enter_y)
                return None

            loc = LocalCoord(x, y)
            interferes = next(filter(lambda p: loc.x == p.loc.x, self.drawing_panel.points), None)
            if interferes is None:
                return loc
            else:
                self.drawing_panel.blink_point(interferes)
                self.invalid_entry(self.enter_x)

        def btn_click(*_):
            if self.ui_lock.locked():
                return
            x = enter_x.get()
            y = enter_y.get()
            if (loc := cast(x, y)) is not None:
                p = Point(loc)
                self.drawing_panel.points.append(p)
                self.drawing_panel.redraw_lines()
                self.drawing_panel.redraw_point(p)

        enter_x = self.style.init_entry(master=self.canvas)
        self.set_text(enter_x, "x")
        enter_x.bind("<Return>", btn_click)
        enter_x.bind("<FocusIn>", lambda _: self.clear_text(enter_x, "x"))
        enter_x.bind("<FocusOut>", lambda _: self.set_text(enter_x, "x"))

        enter_y = self.style.init_entry(master=self.canvas)
        self.set_text(enter_y, "y")
        enter_y.bind("<FocusIn>", lambda _: self.clear_text(enter_y, "y"))
        enter_y.bind("<FocusOut>", lambda _: self.set_text(enter_y, "y"))
        enter_y.bind("<Return>", btn_click)

        add_btn = self.style.init_button(master=self.canvas)
        add_btn.configure(text="ADD", command=btn_click)
        add_btn.bind("<Return>", btn_click)

        return add_btn, enter_x, enter_y

    def __place_add_point(self):
        row = self.__get_next_row()
        self.enter_x.grid(row=row, column=0, sticky=tk.N + tk.S + tk.W + tk.E, padx=(self.padx, 0))
        self.enter_y.grid(row=row, column=1, sticky=tk.N + tk.S + tk.W + tk.E, padx=self.padx)
        self.add_btn.grid(row=row, column=2, sticky=tk.N + tk.S + tk.W + tk.E, padx=(0, self.padx))

    def update_loc_label(self, x, y):
        cac = CanvasCoord(x, y)
        loc = self.drawing_panel.to_local_coords(cac)
        new_x, new_y, fx = loc.x, loc.y, None

        if (p := self.drawing_panel.dragged_point) is not None or (p := self.drawing_panel.intersects_point(cac)):
            new_x, new_y = p.loc.x, p.loc.y

        if (line := self.drawing_panel.intersects_line(cac, True)) is not None:
            fx = line.get_function()(new_x)

        self.val_x.configure(state=tk.NORMAL)
        self.clear_text(self.val_x)
        self.set_text(self.val_x, float_to_str(new_x, self.max_digits))
        self.val_x.configure(state="readonly")

        self.val_y.configure(state=tk.NORMAL)
        self.clear_text(self.val_y)
        self.set_text(self.val_y, float_to_str(new_y, self.max_digits))
        self.val_y.configure(state="readonly")

        self.val_fx.configure(state=tk.NORMAL)
        self.clear_text(self.val_fx)
        self.set_text(self.val_fx, float_to_str(fx, self.max_digits))
        self.val_fx.configure(state="readonly")

    def __init_export_func(self):
        # TODO iterate all children from FunctionExporter and add to dropdown or smth
        from function_exporters.FunctionExporterPy import FunctionExporterPy

        enter_func_name = self.style.init_entry(master=self.canvas)
        self.set_text(enter_func_name, "FUNCTION IDENTIFIER")

        def btn_click(*_):
            if self.ui_lock.locked():
                return
            func_name = enter_func_name.get()
            if func_name.isidentifier():
                s = FunctionExporterPy.to_function(self.drawing_panel.get_lines(), func_name)
                print(s)
            else:
                self.invalid_entry(enter_func_name)

        export_btn = self.style.init_button(master=self.canvas)
        export_btn.configure(text="EXPORT", command=btn_click)
        enter_func_name.bind("<FocusIn>", lambda _: self.clear_text(enter_func_name, "FUNCTION IDENTIFIER"))
        enter_func_name.bind("<FocusOut>", lambda _: self.set_text(enter_func_name, "FUNCTION IDENTIFIER"))
        enter_func_name.bind("<Return>", btn_click)
        return export_btn, enter_func_name

    def __place_extrapolate_entries(self):
        row = self.__get_next_row()

        self.style.init_label(master=self.canvas, text="Left").grid(row=row, column=0, padx=(self.padx, 0))
        self.style.init_label(master=self.canvas, text="Extrapolate").grid(row=row, column=1, padx=self.padx)
        self.style.init_label(master=self.canvas, text="Right").grid(row=row, column=2, padx=(0, self.padx))

        row = self.__get_next_row()
        self.extrapolate_left.grid(row=row, column=0, sticky=tk.N + tk.S + tk.W + tk.E, padx=(self.padx, 0))
        self.style.init_label(master=self.canvas, text="#Point").grid(row=row, column=1, padx=self.padx)
        self.extrapolate_right.grid(row=row, column=2, sticky=tk.N + tk.S + tk.W + tk.E, padx=(0, self.padx))

    def __init_extrapolate_entries(self):
        extrapolate_left, extrapolate_right = self.style.init_entry(master=self.canvas), self.style.init_entry(
            master=self.canvas)
        self.set_text(extrapolate_left, self.drawing_panel.extrapolate_left)
        self.set_text(extrapolate_right, self.drawing_panel.extrapolate_right)

        def btn_click(_, direction: Literal["left", "right"]):
            if self.ui_lock.locked():
                return

            if direction == "left":
                try:
                    self.drawing_panel.extrapolate_left = int(extrapolate_left.get())
                except ValueError:
                    self.invalid_entry(extrapolate_left)
            else:
                try:
                    self.drawing_panel.extrapolate_right = int(extrapolate_right.get())
                except ValueError:
                    self.invalid_entry(extrapolate_right)

        extrapolate_left.bind("<Return>", lambda event: btn_click(event, "left"))
        extrapolate_right.bind("<Return>", lambda event: btn_click(event, "right"))

        return extrapolate_left, extrapolate_right
