import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from misc import CheckBox


@dataclass
class UIStyle:
    canvas_bg_color = "#5A5A5A"
    info_panel_bg_color = "gray"
    point_fill = "black"
    point_radius = 5
    default_segment_fill = "white"
    extrapolate_segment_fill = "yellow"
    segment_width = 3
    label_width = 10
    axes_color = "black"
    grid_color = "grey"

    font_small = ("Courier New", 11)
    font_large = ("Courier New", 15)

    accent_color = "#D3D3D3"
    invalid_color = "#F1807E"
    text_color = "black"

    def __post_init__(self):
        self.init_button = lambda **kwargs: \
            tk.Button(font=self.font_small, bg=self.accent_color, relief=tk.FLAT, **kwargs)

        self.init_checkbox = lambda **kwargs: \
            CheckBox(checked_color=self.accent_color, unchecked_color=self.info_panel_bg_color,
                     disabled_color=self.info_panel_bg_color, **kwargs)

        self.init_entry = lambda **kwargs: \
            tk.Entry(insertbackground=self.info_panel_bg_color, width=self.label_width,
                     background=self.accent_color, font=self.font_small, disabledforeground=self.text_color,
                     disabledbackground=self.accent_color, relief=tk.FLAT, **kwargs)

        self.init_heading_label = lambda **kwargs: \
            ttk.Label(font=self.font_large, foreground=self.text_color, background=self.info_panel_bg_color, **kwargs)

        self.init_label = lambda **kwargs: \
            ttk.Label(font=self.font_small, foreground=self.text_color, background=self.info_panel_bg_color, **kwargs)
