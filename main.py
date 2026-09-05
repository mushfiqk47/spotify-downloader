"""
StreamRip Core - Main Application Launcher.
"""
import tkinter as tk
from core import enable_high_dpi
from app import StreamRipApp


def main():
    enable_high_dpi()
    root = tk.Tk()
    app = StreamRipApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
