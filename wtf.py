import tkinter as tk
from DrawingPanel import DrawingPanel
from InfoPanel import InfoPanel
from UIStyle import UIStyle

if __name__ == '__main__':
    root = tk.Tk()
    root.title("What the Function")

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    drawing_canvas_width = 400
    drawing_canvas_height = 400
    drawing_canvas = tk.Canvas(master=main_frame,
                               width=drawing_canvas_width,
                               height=drawing_canvas_height,
                               highlightthickness=0)

    main_frame.rowconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=2)

    drawing_canvas.grid(row=0, column=1, sticky=tk.N + tk.S + tk.E + tk.W)
    drawing_panel = DrawingPanel(drawing_canvas, UIStyle())

    info_panel_canvas = tk.Canvas(master=main_frame, highlightthickness=0)
    info_panel = InfoPanel(info_panel_canvas, drawing_panel, UIStyle())
    info_panel_canvas.grid(row=0, column=0, sticky=tk.N + tk.S)

    # combined binds
    def on_button1_move(event):
        drawing_panel.on_button1_move(event)
        info_panel.on_motion(event)

    def on_motion(event):
        info_panel.on_motion(event)

    def on_zoom(event):
        drawing_panel.zoom(event)
        info_panel.on_motion(event)

    drawing_canvas.bind("<B1-Motion>", on_button1_move)
    drawing_canvas.bind("<Motion>", on_motion)
    drawing_canvas.bind("<MouseWheel>", on_zoom)

    root.attributes("-alpha", 0)  # invisible
    drawing_panel.on_resize(None)
    root.attributes("-alpha", 1)  # visible

    root.mainloop()
