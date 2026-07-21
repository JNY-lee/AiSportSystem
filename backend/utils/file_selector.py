import tkinter as tk
from tkinter import filedialog

def select_mp4():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()
    path = filedialog.askopenfilename(
        title="选择健身MP4视频",
        filetypes=[("MP4视频", "*.mp4")]
    )
    root.destroy()
    return path