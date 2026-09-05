"""
StreamRip Core - Application Controller & View Assembly.
Strictly implements the Cal.com design system (design.md) with modern 2-column layout.
Features zero-lag batched UI updates and persistent settings.
"""
import os
import queue
import tkinter as tk
from pathlib import Path
from tkinter import Tk, ttk, StringVar, BooleanVar, filedialog, messagebox
from typing import Optional

from core.theme import (
    C, configure_styles,
    FONT_APP_TITLE, FONT_BODY, FONT_CAPTION, FONT_CAPTION_BOLD, FONT_CTA
)
from core.widgets import PillButton, PillBadge, SegmentedPill, PipelineOutputConsole
from core.config import SettingsManager
from engines import YouTubeEngine, SpotifyEngine, ProgressUpdate


class StreamRipApp:
    """Main application replicating the Cal.com 2-column extraction studio."""

    def __init__(self, root: Tk, default_mode: Optional[str] = None):
        self.root = root
        self.root.title("StreamRip Core")
        self.root.geometry("1040x690")
        self.root.minsize(920, 600)
        self.root.configure(bg=C["paper"])

        configure_styles(root)

        # Settings Manager
        self.settings = SettingsManager()
        initial_mode = default_mode or self.settings.get("mode", "youtube")
        self.mode = StringVar(value=initial_mode)

        # Engines
        self.yt_engine = YouTubeEngine()
        self.sp_engine = SpotifyEngine()

        # Paths
        self.youtube_out = self.settings.get("youtube_out", str(Path.home() / "Videos" / "YouTubeDownloads"))
        self.spotify_out = self.settings.get("spotify_out", str(Path.home() / "Music" / "SpotifyDownloads"))
        self.output_dir = StringVar(value=self.youtube_out if initial_mode == "youtube" else self.spotify_out)

        # Form Inputs
        self.source_url = StringVar()
        self.status_state = StringVar(value="● Standby")

        # YouTube Options from settings
        self.yt_stream = StringVar(value=self.settings.get("yt_stream", "Best Available (Source)"))
        self.yt_caption_env = StringVar(value=self.settings.get("yt_caption_env", "SubRip Subtitle (.srt)"))
        self.yt_capture_subs = BooleanVar(value=self.settings.get("yt_capture_subs", True))
        self.yt_transcript_only = BooleanVar(value=self.settings.get("yt_transcript_only", False))
        self.yt_lang = StringVar(value=self.settings.get("yt_lang", "en"))

        # Spotify Options from settings
        self.sp_stream = StringVar(value=self.settings.get("sp_stream", "MP3 Audio (.mp3)"))
        self.sp_bitrate = StringVar(value=self.settings.get("sp_bitrate", "Auto (Best Match)"))
        self.sp_generate_lrc = BooleanVar(value=self.settings.get("sp_generate_lrc", True))
        self.sp_keep_archives = BooleanVar(value=self.settings.get("sp_keep_archives", False))

        self._build_ui(initial_mode)
        self._sync_mode_ui()

        # Start periodic zero-lag output consumer (every 30ms)
        self.root.after(30, self._poll_output_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    @property
    def active_engine(self):
        return self.yt_engine if self.mode.get() == "youtube" else self.sp_engine

    def _build_ui(self, initial_mode: str):
        # Outer Page Container with token padding (16px)
        outer_pad = ttk.Frame(self.root, style="Page.TFrame", padding=16)
        outer_pad.pack(fill=tk.BOTH, expand=True)

        self.main_card = tk.Frame(
            outer_pad,
            bg=C["white"],
            highlightbackground=C["silver"],
            highlightthickness=1,
            bd=0,
        )
        self.main_card.pack(fill=tk.BOTH, expand=True)
        self.main_card.grid_columnconfigure(0, weight=1)
        self.main_card.grid_rowconfigure(2, weight=1)

        # ---------------- Row 0: Header Bar ----------------
        header = tk.Frame(self.main_card, bg=C["white"], padx=24, pady=16)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        head_left = tk.Frame(header, bg=C["white"])
        head_left.grid(row=0, column=0, sticky="w")

        title_lbl = tk.Label(head_left, text="StreamRip Core", font=FONT_APP_TITLE, fg=C["ink"], bg=C["white"])
        title_lbl.pack(side=tk.LEFT, padx=(0, 10))

        PillBadge(head_left, text="v2.4.1").pack(side=tk.LEFT, padx=(0, 16))

        # Modern Accessible Segmented Pill Switcher
        self.mode_seg = SegmentedPill(
            head_left,
            options=[("youtube", "YouTube"), ("spotify", "Spotify")],
            current_value=initial_mode,
            on_change=self._set_mode,
        )
        self.mode_seg.pack(side=tk.LEFT)

        # Right Header: Status Indicator
        self.status_lbl = tk.Label(
            header,
            textvariable=self.status_state,
            font=FONT_CAPTION_BOLD,
            fg=C["slate"],
            bg=C["white"],
        )
        self.status_lbl.grid(row=0, column=1, sticky="e")

        # ---------------- Row 1: Header Divider ----------------
        hdr_divider = tk.Frame(self.main_card, bg=C["silver"], height=1)
        hdr_divider.grid(row=1, column=0, sticky="ew")

        # ---------------- Row 2: 2-Column Split Workspace ----------------
        content = tk.Frame(self.main_card, bg=C["white"])
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=6, minsize=460)  # Left column ~58%
        content.grid_columnconfigure(1, weight=0)               # Divider
        content.grid_columnconfigure(2, weight=4, minsize=380)  # Right column ~42%
        content.grid_rowconfigure(0, weight=1)

        # ================= LEFT COLUMN =================
        left_col = tk.Frame(content, bg=C["white"], padx=24, pady=20)
        left_col.grid(row=0, column=0, sticky="nsew")
        left_col.grid_columnconfigure(0, weight=1)

        # 1. Source URL Section
        url_header = tk.Frame(left_col, bg=C["white"])
        url_header.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(url_header, text="Source URL", style="Field.TLabel").pack(side=tk.LEFT)
        self.url_hint_lbl = ttk.Label(url_header, text="YouTube & Playlists", style="FieldHint.TLabel")
        self.url_hint_lbl.pack(side=tk.RIGHT)

        self.url_entry = ttk.Entry(left_col, textvariable=self.source_url, font=FONT_BODY)
        self.url_entry.pack(fill=tk.X, ipady=4, pady=(0, 16))
        self.url_entry.bind("<Return>", lambda _e: self._on_cta_click())
        self.url_entry.bind("<FocusIn>", self._on_url_focus_in)
        self.url_entry.bind("<FocusOut>", self._on_url_focus_out)

        # 2. Export Destination Section
        dest_header = tk.Frame(left_col, bg=C["white"])
        dest_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(dest_header, text="Export Destination", style="Field.TLabel").pack(side=tk.LEFT)

        dest_row = tk.Frame(left_col, bg=C["white"])
        dest_row.pack(fill=tk.X, pady=(0, 16))
        dest_row.grid_columnconfigure(0, weight=1)

        self.dest_entry = ttk.Entry(dest_row, textvariable=self.output_dir, font=FONT_BODY, state="readonly")
        self.dest_entry.grid(row=0, column=0, sticky="ew", ipady=4)

        browse_btn = ttk.Button(dest_row, text="Browse", style="Secondary.TButton", command=self._browse_dir)
        browse_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        open_btn = ttk.Button(dest_row, text="Open", style="Secondary.TButton", command=self._open_dir)
        open_btn.grid(row=0, column=2, sticky="e", padx=(4, 0))

        # 3. Two-Column Dropdown Row
        drop_row = tk.Frame(left_col, bg=C["white"])
        drop_row.pack(fill=tk.X, pady=(0, 16))
        drop_row.grid_columnconfigure(0, weight=1)
        drop_row.grid_columnconfigure(1, weight=1)

        # Left Dropdown
        stream_cell = tk.Frame(drop_row, bg=C["white"])
        stream_cell.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.media_stream_lbl = ttk.Label(stream_cell, text="Media Stream", style="Field.TLabel")
        self.media_stream_lbl.pack(anchor=tk.W, pady=(0, 6))

        self.media_stream_combo = ttk.Combobox(
            stream_cell,
            state="readonly",
            font=FONT_BODY,
        )
        self.media_stream_combo.pack(fill=tk.X)

        # Right Dropdown
        caption_cell = tk.Frame(drop_row, bg=C["white"])
        caption_cell.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.caption_lbl = ttk.Label(caption_cell, text="Caption Envelope", style="Field.TLabel")
        self.caption_lbl.pack(anchor=tk.W, pady=(0, 6))

        self.caption_combo = ttk.Combobox(
            caption_cell,
            state="readonly",
            font=FONT_BODY,
        )
        self.caption_combo.pack(fill=tk.X)

        # 4. Contained Options Card (Soft gray surface #f9fafb with 1px silver border)
        self.opt_card = tk.Frame(
            left_col,
            bg=C["card_bg"],
            highlightbackground=C["silver"],
            highlightthickness=1,
            bd=0,
            padx=16,
            pady=16,
        )
        self.opt_card.pack(fill=tk.X, pady=(0, 20))

        # --- YouTube Options Frame ---
        self.yt_opt_frame = tk.Frame(self.opt_card, bg=C["card_bg"])

        self.yt_capture_cb = ttk.Checkbutton(
            self.yt_opt_frame,
            text="Capture Transcripts & Timestamps",
            variable=self.yt_capture_subs,
            style="Card.TCheckbutton",
            command=self._on_yt_subs_toggle,
        )
        self.yt_capture_cb.pack(anchor=tk.W)

        ttk.Label(
            self.yt_opt_frame,
            text="Prefers manual creator subs; falls back to automated tracks.",
            style="OptionSub.TLabel",
        ).pack(anchor=tk.W, padx=(22, 0), pady=(2, 10))

        sub_sub_row = tk.Frame(self.yt_opt_frame, bg=C["card_bg"])
        sub_sub_row.pack(fill=tk.X, padx=(22, 0))
        sub_sub_row.grid_columnconfigure(0, weight=1)

        left_check = tk.Frame(sub_sub_row, bg=C["card_bg"])
        left_check.grid(row=0, column=0, sticky="w")

        self.yt_only_cb = ttk.Checkbutton(
            left_check,
            text="Transcript-Only Mode",
            variable=self.yt_transcript_only,
            style="CardSub.TCheckbutton",
        )
        self.yt_only_cb.pack(anchor=tk.W)

        ttk.Label(
            left_check,
            text="Skip video track payload.",
            style="OptionSub.TLabel",
        ).pack(anchor=tk.W, padx=(22, 0), pady=(1, 0))

        lang_wrap = tk.Frame(sub_sub_row, bg=C["card_bg"])
        lang_wrap.grid(row=0, column=1, sticky="e")

        ttk.Label(lang_wrap, text="Lang", style="OptionSub.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        self.lang_entry = ttk.Entry(lang_wrap, textvariable=self.yt_lang, width=5, font=FONT_CAPTION)
        self.lang_entry.pack(side=tk.LEFT)

        # --- Spotify Options Frame ---
        self.sp_opt_frame = tk.Frame(self.opt_card, bg=C["card_bg"])

        self.sp_lyrics_cb = ttk.Checkbutton(
            self.sp_opt_frame,
            text="Generate Synced Lyrics (.lrc)",
            variable=self.sp_generate_lrc,
            style="Card.TCheckbutton",
        )
        self.sp_lyrics_cb.pack(anchor=tk.W)

        ttk.Label(
            self.sp_opt_frame,
            text="Embeds timestamped lyrics for supported audio players.",
            style="OptionSub.TLabel",
        ).pack(anchor=tk.W, padx=(22, 0), pady=(2, 10))

        self.sp_archive_cb = ttk.Checkbutton(
            self.sp_opt_frame,
            text="Preserve Cache Archives",
            variable=self.sp_keep_archives,
            style="CardSub.TCheckbutton",
        )
        self.sp_archive_cb.pack(anchor=tk.W, padx=(22, 0))

        ttk.Label(
            self.sp_opt_frame,
            text="Keep raw .spotdl and zip archives after processing.",
            style="OptionSub.TLabel",
        ).pack(anchor=tk.W, padx=(44, 0), pady=(1, 0))

        # 5. Primary CTA Pill Button
        self.cta_btn = PillButton(
            left_col,
            text="⤓ Start Extraction",
            command=self._on_cta_click,
            height=44,
            bg_color=C["ink"],
            hover_color=C["ink_hover"],
            pressed_color=C["ink_pressed"],
            fg_color=C["white"],
            font=FONT_CTA,
        )
        self.cta_btn.pack(fill=tk.X, pady=(4, 6))

        # Determinate / Indeterminate progress bar
        self.progress_bar = ttk.Progressbar(left_col, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.pack_forget()

        # ================= VERTICAL DIVIDER =================
        v_div = tk.Frame(content, bg=C["silver"], width=1)
        v_div.grid(row=0, column=1, sticky="ns")

        # ================= RIGHT COLUMN =================
        right_col = tk.Frame(content, bg=C["white"], padx=24, pady=20)
        right_col.grid(row=0, column=2, sticky="nsew")
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(0, weight=1)

        self.console = PipelineOutputConsole(right_col)
        self.console.wrap.grid(row=0, column=0, sticky="nsew")

    # ---------------- Mode Configuration ----------------
    def _set_mode(self, new_mode: str):
        if self.active_engine.is_running:
            messagebox.showwarning("Active Pipeline", "Please wait for current extraction to finish or abort it first.")
            self.mode_seg.select(self.mode.get())
            return
        self.mode.set(new_mode)
        self.mode_seg.select(new_mode)
        self.settings.set("mode", new_mode)
        self._sync_mode_ui()

    def _sync_mode_ui(self):
        m = self.mode.get()

        if m == "youtube":
            self.url_hint_lbl.configure(text="YouTube & Playlists")
            self.media_stream_lbl.configure(text="Media Stream")
            self.caption_lbl.configure(text="Caption Envelope")

            self.media_stream_combo.configure(
                textvariable=self.yt_stream,
                values=list(YouTubeEngine.STREAM_PRESETS.keys()),
            )
            self.caption_combo.configure(
                textvariable=self.yt_caption_env,
                values=list(YouTubeEngine.CAPTION_EXT_MAP.keys()),
            )

            self.output_dir.set(self.youtube_out)

            self.sp_opt_frame.pack_forget()
            self.yt_opt_frame.pack(fill=tk.X)
            self._on_yt_subs_toggle()
        else:
            self.url_hint_lbl.configure(text="Spotify Tracks & Albums")
            self.media_stream_lbl.configure(text="Audio Format")
            self.caption_lbl.configure(text="Encoding Bitrate")

            self.media_stream_combo.configure(
                textvariable=self.sp_stream,
                values=list(SpotifyEngine.FORMAT_MAP.keys()),
            )
            self.caption_combo.configure(
                textvariable=self.sp_bitrate,
                values=list(SpotifyEngine.BITRATE_MAP.keys()),
            )

            self.output_dir.set(self.spotify_out)

            self.yt_opt_frame.pack_forget()
            self.sp_opt_frame.pack(fill=tk.X)

        self._apply_placeholder()

    def _on_yt_subs_toggle(self):
        enabled = self.yt_capture_subs.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.yt_only_cb.configure(state=state)
        self.lang_entry.configure(state=state)
        self.caption_combo.configure(state="readonly" if enabled else tk.DISABLED)

    def _browse_dir(self):
        folder = filedialog.askdirectory(title="Select Destination Folder", initialdir=self.output_dir.get())
        if folder:
            self.output_dir.set(folder)
            if self.mode.get() == "youtube":
                self.youtube_out = folder
                self.settings.set("youtube_out", folder)
            else:
                self.spotify_out = folder
                self.settings.set("spotify_out", folder)
            self.settings.save()

    def _open_dir(self):
        folder = self.output_dir.get().strip()
        if folder:
            os.makedirs(folder, exist_ok=True)
            try:
                os.startfile(folder)
            except Exception as e:
                messagebox.showerror("Error Opening Folder", str(e))

    # ---------------- Placeholder Handling ----------------
    def _get_placeholder(self) -> str:
        return "https://www.youtube.com/watch?v=..." if self.mode.get() == "youtube" else "https://open.spotify.com/playlist/..."

    def _apply_placeholder(self):
        cur = self.source_url.get().strip()
        ph = self._get_placeholder()
        if not cur or cur in ("https://www.youtube.com/watch?v=...", "https://open.spotify.com/playlist/..."):
            self.source_url.set(ph)
            self.url_entry.configure(foreground=C["stone"])
        else:
            self.url_entry.configure(foreground=C["graphite"])

    def _on_url_focus_in(self, event=None):
        cur = self.source_url.get().strip()
        if cur in ("https://www.youtube.com/watch?v=...", "https://open.spotify.com/playlist/..."):
            self.source_url.set("")
        self.url_entry.configure(foreground=C["graphite"])

    def _on_url_focus_out(self, event=None):
        cur = self.source_url.get().strip()
        if not cur:
            self.source_url.set(self._get_placeholder())
            self.url_entry.configure(foreground=C["stone"])
        else:
            self.url_entry.configure(foreground=C["graphite"])

    # ---------------- Extraction Lifecycle ----------------
    def _on_cta_click(self):
        engine = self.active_engine
        if engine.is_running:
            engine.abort()
            self.console.write("Operation aborted by user.", tag="danger")
            self.status_state.set("● Aborted")
            self.status_lbl.configure(fg=C["danger"])
            self._set_idle_ui()
        else:
            self._start_extraction()

    def _start_extraction(self):
        url = self.source_url.get().strip()
        ph = self._get_placeholder()
        if not url or url == ph:
            messagebox.showwarning("Missing URL", "Please enter a valid target URL.")
            self.url_entry.focus()
            return

        engine = self.active_engine
        out_dir = self.output_dir.get().strip()
        os.makedirs(out_dir, exist_ok=True)

        # Build command based on active mode
        if self.mode.get() == "youtube":
            cmd = engine.build_command(
                url=url,
                out_dir=out_dir,
                stream_preset=self.yt_stream.get(),
                caption_env=self.yt_caption_env.get(),
                capture_subs=self.yt_capture_subs.get(),
                transcript_only=self.yt_transcript_only.get(),
                lang=self.yt_lang.get(),
            )
        else:
            cmd = engine.build_command(
                url=url,
                out_dir=out_dir,
                stream_preset=self.sp_stream.get(),
                bitrate=self.sp_bitrate.get(),
                generate_lrc=self.sp_generate_lrc.get(),
            )

        # Save settings on launch
        self._save_current_settings()

        self._set_running_ui()
        self.console.clear()
        self.console.write(f"Initiating pipeline for target: {url}", tag="action_blue")
        self.console.write(f"Destination: {out_dir}", tag="muted")

        engine.runner.start(cmd=cmd)

    def _save_current_settings(self):
        self.settings.set_many({
            "mode": self.mode.get(),
            "youtube_out": self.youtube_out,
            "spotify_out": self.spotify_out,
            "yt_stream": self.yt_stream.get(),
            "yt_caption_env": self.yt_caption_env.get(),
            "yt_capture_subs": self.yt_capture_subs.get(),
            "yt_transcript_only": self.yt_transcript_only.get(),
            "yt_lang": self.yt_lang.get(),
            "sp_stream": self.sp_stream.get(),
            "sp_bitrate": self.sp_bitrate.get(),
            "sp_generate_lrc": self.sp_generate_lrc.get(),
            "sp_keep_archives": self.sp_keep_archives.get(),
        })
        self.settings.save()

    # ---------------- High-Performance Queue Drainer ----------------
    def _poll_output_queue(self):
        """Batched queue consumer running every 30ms for 100% fluid 60fps UI."""
        engine = self.active_engine
        q = engine.runner.output_queue

        batch_log = []
        max_items = 40  # Process up to 40 items per tick to prevent starvation

        while not q.empty() and max_items > 0:
            max_items -= 1
            try:
                msg_type, data = q.get_nowait()
            except queue.Empty:
                break

            if msg_type == "LINE":
                update: ProgressUpdate = engine.parse_line(data)

                # Update progress bar if percentage parsed
                if update.percent is not None:
                    if self.progress_bar.cget("mode") != "determinate":
                        self.progress_bar.stop()
                        self.progress_bar.configure(mode="determinate", maximum=100)
                    self.progress_bar["value"] = update.percent
                    self.status_state.set(f"● Extracting {update.percent:.1f}%")
                    self.status_lbl.configure(fg=C["action_blue"])

                batch_log.append((update.raw_line, update.tag))

            elif msg_type == "ERROR":
                batch_log.append((data, "danger"))

            elif msg_type == "DONE":
                exit_code, aborted = data
                self._handle_complete(exit_code, aborted)

        if batch_log:
            self.console.write_batch(batch_log)

        # Schedule next poll
        self.root.after(30, self._poll_output_queue)

    def _handle_complete(self, exit_code: int, aborted: bool):
        self._set_idle_ui()
        out_dir = self.output_dir.get().strip()

        if aborted:
            self.status_state.set("● Aborted")
            self.status_lbl.configure(fg=C["danger"])
            self.console.write("Execution terminated by user.", tag="danger")
        elif exit_code == 0:
            self.status_state.set("● Standby")
            self.status_lbl.configure(fg=C["success"])
            self.console.write(f"\nPipeline finished. Payload saved to: {out_dir}", tag="success")
        else:
            self.status_state.set("● Failed")
            self.status_lbl.configure(fg=C["danger"])
            self.console.write(f"\nPipeline halted with exit code {exit_code}.", tag="danger")

    def _set_running_ui(self):
        self.cta_btn.set_mode(is_danger=True, text="■ Cancel Extraction")
        self.status_state.set("● Processing")
        self.status_lbl.configure(fg=C["action_blue"])
        self.progress_bar.pack(fill=tk.X, pady=(4, 0))
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start(10)
        self.url_entry.configure(state=tk.DISABLED)

    def _set_idle_ui(self):
        self.cta_btn.set_mode(is_danger=False, text="⤓ Start Extraction")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.url_entry.configure(state=tk.NORMAL)

    def _on_closing(self):
        self._save_current_settings()
        if self.yt_engine.is_running:
            self.yt_engine.abort()
        if self.sp_engine.is_running:
            self.sp_engine.abort()
        self.root.destroy()
