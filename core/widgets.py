"""
Custom reusable UI components for Cal.com monochrome styling:
- PillButton (True pill canvas button with keyboard navigation and focus ring)
- PillBadge (Pill tag for versioning and metadata)
- SegmentedPill (Accessible segmented mode toggle)
- PipelineOutputConsole (Contained studio terminal with high-contrast logs and buffer capping)
"""
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from core.theme import (
    C,
    FONT_CTA,
    FONT_BADGE,
    FONT_CODE,
)


class PillButton(tk.Canvas):
    """
    Precision pill button (radius: 9999px) strictly implementing Cal.com design.
    Features:
    - True circular arc ends for geometric accuracy
    - Full keyboard navigation (Tab focus, Enter/Space activation)
    - High-contrast visual focus ring (WCAG AA)
    - Hover and active-press states
    - Disabled state support
    """

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "⤓ Start Extraction",
        command: Optional[Callable[[], None]] = None,
        height: int = 44,
        bg_color: str = C["ink"],
        hover_color: str = C["ink_hover"],
        pressed_color: str = C["ink_pressed"],
        fg_color: str = C["white"],
        font=FONT_CTA,
        **kwargs,
    ):
        super().__init__(
            parent,
            height=height,
            bg=C["white"],
            bd=0,
            highlightthickness=0,
            takefocus=1,
            cursor="hand2",
            **kwargs,
        )
        self.text = text
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.fg_color = fg_color
        self.current_bg = bg_color
        self.font = font
        self.height = height
        self._enabled = True
        self._focused = False
        self._pressed = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyPress-Return>", self._on_activate_key)
        self.bind("<KeyPress-space>", self._on_activate_key)

    def _draw_pill(self, x1, y1, x2, y2, fill, outline=""):
        """Draws a mathematically true pill with circular ends."""
        h = y2 - y1
        r = h / 2.0
        # If width is too small, draw regular rect
        if x2 - x1 < h:
            return self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline)

        # Smooth polygon pill using 18 points for circular arcs
        points = []
        import math
        # Right cap (angle -pi/2 to pi/2)
        cx_right = x2 - r
        cy_right = y1 + r
        for step in range(10):
            theta = -math.pi / 2.0 + (math.pi * step / 9.0)
            points.extend([cx_right + r * math.cos(theta), cy_right + r * math.sin(theta)])

        # Left cap (angle pi/2 to 3pi/2)
        cx_left = x1 + r
        cy_left = y1 + r
        for step in range(10):
            theta = math.pi / 2.0 + (math.pi * step / 9.0)
            points.extend([cx_left + r * math.cos(theta), cy_left + r * math.sin(theta)])

        return self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        pad = 3 if self._focused else 1
        bg = self.current_bg if self._enabled else C["silver"]
        fg = self.fg_color if self._enabled else C["slate"]

        # Outer focus ring if keyboard focused
        if self._focused and self._enabled:
            self._draw_pill(1, 1, w - 1, h - 1, fill="", outline=C["focus_ring"])

        # Inner Pill Body
        self._draw_pill(pad, pad, w - pad, h - pad, fill=bg, outline="")
        self.create_text(w // 2, h // 2, text=self.text, fill=fg, font=self.font)

    def _on_enter(self, event=None):
        if self._enabled and not self._pressed:
            self.current_bg = self.hover_color
            self._draw()

    def _on_leave(self, event=None):
        if self._enabled:
            self._pressed = False
            self.current_bg = self.bg_color
            self._draw()

    def _on_press(self, event=None):
        if self._enabled:
            self._pressed = True
            self.current_bg = self.pressed_color
            self._draw()

    def _on_release(self, event=None):
        if self._enabled:
            self._pressed = False
            self.current_bg = self.hover_color if event else self.bg_color
            self._draw()
            if self.command:
                self.command()

    def _on_focus_in(self, event=None):
        self._focused = True
        self._draw()

    def _on_focus_out(self, event=None):
        self._focused = False
        self._draw()

    def _on_activate_key(self, event=None):
        if self._enabled and self.command:
            self._pressed = True
            self.current_bg = self.pressed_color
            self._draw()
            self.after(120, self._restore_key_press)
            self.command()

    def _restore_key_press(self):
        self._pressed = False
        self.current_bg = self.bg_color
        self._draw()

    def set_text(self, text: str):
        self.text = text
        self._draw()

    def set_mode(self, is_danger: bool, text: str):
        self.text = text
        if is_danger:
            self.bg_color = C["danger"]
            self.hover_color = C["danger_hover"]
            self.pressed_color = C["danger_pressed"]
        else:
            self.bg_color = C["ink"]
            self.hover_color = C["ink_hover"]
            self.pressed_color = C["ink_pressed"]
        self.current_bg = self.bg_color
        self._draw()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "")
        self._draw()


class PillBadge(tk.Canvas):
    """
    Renders an authentic pill-shaped badge tag with --radius-tags: 9999px.
    Used for version indicators ('v2.4.1') and metadata tags.
    """

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "v2.4.1",
        bg: str = C["badge_bg"],
        fg: str = C["slate"],
        border: str = C["silver"],
        font=FONT_BADGE,
        height: int = 22,
        **kwargs,
    ):
        super().__init__(
            parent,
            height=height,
            bg=C["white"],
            bd=0,
            highlightthickness=0,
            **kwargs,
        )
        self.text = text
        self.badge_bg = bg
        self.badge_fg = fg
        self.badge_border = border
        self.font = font
        self.height = height

        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        r = h / 2.0
        import math
        points = []
        # Right cap
        cx_right = w - r - 1
        cy_right = r
        for step in range(8):
            theta = -math.pi / 2.0 + (math.pi * step / 7.0)
            points.extend([cx_right + (r - 1) * math.cos(theta), cy_right + (r - 1) * math.sin(theta)])
        # Left cap
        cx_left = r + 1
        cy_left = r
        for step in range(8):
            theta = math.pi / 2.0 + (math.pi * step / 7.0)
            points.extend([cx_left + (r - 1) * math.cos(theta), cy_left + (r - 1) * math.sin(theta)])

        self.create_polygon(points, smooth=True, fill=self.badge_bg, outline=self.badge_border)
        self.create_text(w // 2, h // 2, text=self.text, fill=self.badge_fg, font=self.font)

    def set_text(self, text: str):
        self.text = text
        self._draw()


class SegmentedPill(tk.Frame):
    """
    A segmented 2-button pill switcher adhering strictly to Cal.com binary action styling.
    Features:
    - Active pill indicator in Ink (#101010) with crisp white text
    - Inactive pill in Paper (#f4f4f4) with Slate (#4b5563) text and hover transition
    - Keyboard arrow key navigation & focus
    """

    def __init__(
        self,
        parent: tk.Widget,
        options: List[Tuple[str, str]],  # [("youtube", "YouTube"), ("spotify", "Spotify")]
        current_value: str = "youtube",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            bg=C["paper"],
            highlightbackground=C["silver"],
            highlightthickness=1,
            bd=0,
            padx=2,
            pady=2,
            **kwargs,
        )
        self.options = options
        self.current_value = current_value
        self.on_change = on_change
        self.buttons = {}

        for val, label in options:
            btn = tk.Button(
                self,
                text=label,
                font=FONT_BADGE,
                relief="flat",
                bd=0,
                padx=12,
                pady=4,
                cursor="hand2",
                takefocus=1,
                command=lambda v=val: self.select(v),
            )
            btn.pack(side=tk.LEFT, padx=1)
            btn.bind("<Left>", self._on_arrow_left)
            btn.bind("<Right>", self._on_arrow_right)
            self.buttons[val] = btn

        self._refresh()

    def select(self, val: str):
        if self.current_value != val:
            self.current_value = val
            self._refresh()
            if self.on_change:
                self.on_change(val)

    def _refresh(self):
        for val, btn in self.buttons.items():
            if val == self.current_value:
                btn.configure(
                    bg=C["ink"],
                    fg=C["white"],
                    activebackground=C["ink_hover"],
                    activeforeground=C["white"],
                )
            else:
                btn.configure(
                    bg=C["paper"],
                    fg=C["slate"],
                    activebackground=C["silver"],
                    activeforeground=C["ink"],
                )

    def _on_arrow_left(self, event=None):
        keys = [v for v, _ in self.options]
        idx = keys.index(self.current_value)
        if idx > 0:
            self.select(keys[idx - 1])
            self.buttons[keys[idx - 1]].focus_set()

    def _on_arrow_right(self, event=None):
        keys = [v for v, _ in self.options]
        idx = keys.index(self.current_value)
        if idx < len(keys) - 1:
            self.select(keys[idx + 1])
            self.buttons[keys[idx + 1]].focus_set()


class PipelineOutputConsole:
    """
    Precision terminal viewport for process telemetry.
    Features:
    - Enclosed rounded card border (1px silver) with dedicated header bar
    - WCAG AA compliant tagged log colors
    - Line-capped buffer to eliminate memory leaks on 1000+ item playlists
    - Batched updates for zero UI stutter
    - Timestamp prefixes and status telemetry
    """

    MAX_LINES = 1200

    def __init__(self, parent: tk.Widget):
        # Outer Container Card with 1px silver border
        self.card = tk.Frame(
            parent,
            bg=C["white"],
            highlightbackground=C["silver"],
            highlightthickness=1,
            bd=0,
        )
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(1, weight=1)

        # Header Bar: Title + Telemetry + Copy/Clear buttons
        head = tk.Frame(self.card, bg=C["white"], padx=14, pady=10)
        head.grid(row=0, column=0, sticky="ew")
        head.grid_columnconfigure(1, weight=1)

        title_frame = tk.Frame(head, bg=C["white"])
        title_frame.grid(row=0, column=0, sticky="w")

        self.title_lbl = ttk.Label(title_frame, text="Pipeline Output", style="PipeHead.TLabel")
        self.title_lbl.pack(side=tk.LEFT, padx=(0, 8))

        self.line_badge = PillBadge(title_frame, text="0 lines", bg=C["badge_bg"], fg=C["stone"], height=18)
        self.line_badge.pack(side=tk.LEFT)

        # Header Action Buttons
        actions = tk.Frame(head, bg=C["white"])
        actions.grid(row=0, column=2, sticky="e")

        self.copy_btn = ttk.Button(actions, text="Copy", style="Ghost.TButton", command=self.copy_to_clipboard)
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.clear_btn = ttk.Button(actions, text="Clear", style="Ghost.TButton", command=self.clear)
        self.clear_btn.pack(side=tk.LEFT)

        # Divider between header and text area
        div = tk.Frame(self.card, bg=C["silver"], height=1)
        div.grid(row=0, column=0, sticky="sew")

        # Monospace Text Viewport
        body = tk.Frame(self.card, bg=C["log_bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(body, orient="vertical")
        self.text = tk.Text(
            body,
            yscrollcommand=scrollbar.set,
            font=FONT_CODE,
            wrap="word",
            padx=10,
            pady=8,
            bg=C["log_bg"],
            fg=C["graphite"],
            insertbackground=C["graphite"],
            selectbackground=C["ink"],
            selectforeground=C["white"],
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scrollbar.configure(command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.configure(state=tk.DISABLED)

        # WCAG AA compliant tag colors
        self.text.tag_configure("muted", foreground=C["stone"])
        self.text.tag_configure("action_blue", foreground=C["action_blue"])
        self.text.tag_configure("success", foreground=C["success"])
        self.text.tag_configure("danger", foreground=C["danger"])
        self.text.tag_configure("normal", foreground=C["graphite"])
        self.text.tag_configure("timestamp", foreground=C["stone"])

        self._line_count = 0
        self._pending_batch: List[Tuple[str, str, bool]] = []
        self._batch_job = None
        self.clear()

    @property
    def wrap(self) -> tk.Widget:
        """Compatibility property for parent grids."""
        return self.card

    def clear(self):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, "Ready. Pipeline engine initialized.\n", "muted")
        self.text.insert(tk.END, "Awaiting extraction target URL...\n\n", "action_blue")
        self.text.configure(state=tk.DISABLED)
        self._line_count = 3
        self._update_badge()

    def write(self, msg: str, tag: str = "normal", with_time: bool = False):
        """Writes a single line to console with line-count capping."""
        self.text.configure(state=tk.NORMAL)

        if self._line_count > self.MAX_LINES:
            self.text.delete("1.0", "300.0")
            self._line_count -= 300

        if with_time:
            t_str = time.strftime("[%H:%M:%S] ")
            self.text.insert(tk.END, t_str, "timestamp")

        self.text.insert(tk.END, msg + "\n", tag)
        self._line_count += 1
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)
        self._update_badge()

    def write_batched(self, msg: str, tag: str = "normal"):
        """Buffers lines and flushes in batches every 30ms to maintain 60fps UI."""
        self._pending_batch.append((msg, tag, False))
        if self._batch_job is None:
            self._batch_job = self.card.after(30, self._flush_batch)

    def _flush_batch(self):
        self._batch_job = None
        if not self._pending_batch:
            return

        batch = self._pending_batch
        self._pending_batch = []

        self.text.configure(state=tk.NORMAL)
        if self._line_count > self.MAX_LINES:
            self.text.delete("1.0", "300.0")
            self._line_count -= 300

        for msg, tag, _ in batch:
            self.text.insert(tk.END, msg + "\n", tag)
            self._line_count += 1

        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)
        self._update_badge()

    def _update_badge(self):
        self.line_badge.set_text(f"{self._line_count} lines")

    def copy_to_clipboard(self):
        content = self.text.get("1.0", tk.END).strip()
        if content:
            self.card.clipboard_clear()
            self.card.clipboard_append(content)
            self.copy_btn.configure(text="Copied!")
            self.card.after(1500, lambda: self.copy_btn.configure(text="Copy"))

