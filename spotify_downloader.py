"""
StreamRip Core - Spotify Extraction Studio.
Entry point for Spotify downloading using the Cal.com design system (design.md).
"""
import tkinter as tk
from core import enable_high_dpi
from app import StreamRipApp


def main():
    enable_high_dpi()
    root = tk.Tk()
    app = StreamRipApp(root, default_mode="spotify")
    root.mainloop()


if __name__ == "__main__":
    main()
