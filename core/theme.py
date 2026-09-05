"""
Theme tokens, typography, and styling configurations implementing design.md.
"""
import ctypes
import os
import tkinter as tk
from tkinter import ttk


def enable_high_dpi():
    """Configures Windows per-monitor High-DPI awareness (v2 when available)."""
    if os.name == "nt":
        try:
            # Per-Monitor V2 awareness (Windows 10 Creators Update and newer)
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass


# ---------------- Design Tokens from design.md ----------------
C = {
    # Core monochrome palette
    "ink":             "#101010",  # Primary CTAs, active states, dark elements
    "ink_hover":       "#262626",  # Dark button hover
    "ink_pressed":     "#050505",  # Dark button pressed
    "graphite":        "#242424",  # Headlines, field titles, primary text
    "slate":           "#4b5563",  # Secondary text, descriptive hints (WCAG AA ratio > 7:1)
    "stone":           "#6b7280",  # Subtle labels, secondary hints (WCAG AA ratio > 4.5:1)
    "silver":          "#e5e7eb",  # Borders, dividers, subtle outlines
    "silver_dark":     "#d1d5db",  # Active borders, focus highlights
    "paper":           "#f4f4f4",  # Main container background / outer canvas
    "white":           "#ffffff",  # Pure card surfaces, input backgrounds
    "action_blue":     "#0284c7",  # Accessible high-contrast blue (> 4.5:1 ratio on white)
    "action_blue_bg":  "#eff6fe",  # Info banner / accent background
    "danger":          "#dc2626",  # Abort / Error red
    "danger_hover":    "#b91c1c",  # Abort button hover
    "danger_pressed":  "#991b1b",  # Abort button active
    "success":         "#16a34a",  # Success green
    "card_bg":         "#f9fafb",  # Soft gray option card background
    "input_bg":        "#ffffff",  # Input field background
    "log_bg":          "#ffffff",  # Pipeline output log background
    "badge_bg":        "#f3f4f6",  # Version tag background
    "focus_ring":      "#101010",  # High-visibility keyboard focus ring
}


def _detect_fonts():
    """Detects best available typography on the host platform."""
    families = set()
    try:
        root_temp = tk.Tk()
        root_temp.withdraw()
        import tkinter.font as tkfont
        families = set(tkfont.families())
        root_temp.destroy()
    except Exception:
        pass

    disp_family = "Segoe UI Variable Display" if "Segoe UI Variable Display" in families else "Segoe UI"
    text_family = "Segoe UI Variable Text" if "Segoe UI Variable Text" in families else "Segoe UI"
    code_family = "Cascadia Code" if "Cascadia Code" in families else ("Consolas" if "Consolas" in families else "Courier New")
    return disp_family, text_family, code_family


_DISP_FONT, _TEXT_FONT, _CODE_FONT = _detect_fonts()

# Calibrated Type Ramp adhering to Cal.com scale
FONT_APP_TITLE = (_DISP_FONT, 15, "bold")
FONT_HEADLINE = (_DISP_FONT, 12, "bold")
FONT_LABEL = (_TEXT_FONT, 10, "bold")
FONT_BODY = (_TEXT_FONT, 10)
FONT_BODY_SM = (_TEXT_FONT, 9)
FONT_CAPTION = (_TEXT_FONT, 9)
FONT_CAPTION_BOLD = (_TEXT_FONT, 9, "bold")
FONT_BADGE = (_TEXT_FONT, 8, "bold")
FONT_CODE = (_CODE_FONT, 9)
FONT_CTA = (_TEXT_FONT, 11, "bold")


def configure_styles(root: tk.Tk):
    """Configures ttk styles strictly adhering to Cal.com monochrome utility theme."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Global base
    style.configure(".", font=FONT_BODY, background=C["white"])
    style.configure("TFrame", background=C["white"])
    style.configure("Page.TFrame", background=C["paper"])
    style.configure("White.TFrame", background=C["white"])
    style.configure("OptionCard.TFrame", background=C["card_bg"])

    # Labels
    style.configure("TLabel", background=C["white"], foreground=C["graphite"])
    style.configure("AppTitle.TLabel", font=FONT_APP_TITLE, foreground=C["ink"], background=C["white"])
    style.configure("Field.TLabel", font=FONT_LABEL, foreground=C["graphite"], background=C["white"])
    style.configure("FieldHint.TLabel", font=FONT_CAPTION, foreground=C["slate"], background=C["white"])
    style.configure("OptionTitle.TLabel", font=FONT_LABEL, foreground=C["graphite"], background=C["card_bg"])
    style.configure("OptionSub.TLabel", font=FONT_CAPTION, foreground=C["slate"], background=C["card_bg"])
    style.configure("Status.TLabel", font=FONT_CAPTION_BOLD, foreground=C["slate"], background=C["white"])
    style.configure("PipeHead.TLabel", font=FONT_HEADLINE, foreground=C["ink"], background=C["white"])

    # Entries
    style.configure(
        "TEntry",
        fieldbackground=C["input_bg"],
        foreground=C["graphite"],
        borderwidth=1,
        bordercolor=C["silver"],
        lightcolor=C["silver"],
        darkcolor=C["silver"],
        padding=(8, 6),
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", C["ink"]), ("hover", C["silver_dark"])],
        lightcolor=[("focus", C["ink"])],
        darkcolor=[("focus", C["ink"])],
    )

    # Comboboxes
    style.configure(
        "TCombobox",
        fieldbackground=C["input_bg"],
        background=C["white"],
        foreground=C["graphite"],
        arrowcolor=C["slate"],
        bordercolor=C["silver"],
        lightcolor=C["silver"],
        darkcolor=C["silver"],
        padding=(8, 6),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", C["input_bg"])],
        bordercolor=[("focus", C["ink"]), ("hover", C["silver_dark"])],
        lightcolor=[("focus", C["ink"])],
        darkcolor=[("focus", C["ink"])],
    )

    # Checkbuttons
    style.configure(
        "Card.TCheckbutton",
        background=C["card_bg"],
        foreground=C["graphite"],
        font=FONT_LABEL,
        focuscolor="",
    )
    style.map("Card.TCheckbutton", background=[("active", C["card_bg"])])

    style.configure(
        "CardSub.TCheckbutton",
        background=C["card_bg"],
        foreground=C["graphite"],
        font=FONT_BODY,
        focuscolor="",
    )
    style.map("CardSub.TCheckbutton", background=[("active", C["card_bg"])])

    # Secondary Action Button (Browse, Open Folder)
    style.configure(
        "Secondary.TButton",
        background=C["white"],
        foreground=C["graphite"],
        bordercolor=C["silver"],
        lightcolor=C["silver"],
        darkcolor=C["silver"],
        font=FONT_BODY,
        padding=(12, 6),
        borderwidth=1,
        focuscolor="",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", C["paper"])],
        bordercolor=[("active", C["slate"]), ("focus", C["ink"])],
        foreground=[("active", C["ink"])],
    )

    # Ghost button (Copy, Clear)
    style.configure(
        "Ghost.TButton",
        background=C["white"],
        foreground=C["slate"],
        borderwidth=0,
        font=FONT_CAPTION_BOLD,
        padding=(6, 3),
        focuscolor="",
    )
    style.map(
        "Ghost.TButton",
        foreground=[("active", C["ink"])],
        background=[("active", C["paper"])],
    )

    # Progress bar
    style.configure(
        "Horizontal.TProgressbar",
        background=C["ink"],
        troughcolor=C["silver"],
        borderwidth=0,
        thickness=3,
    )

    # Separators
    style.configure("TSeparator", background=C["silver"])
