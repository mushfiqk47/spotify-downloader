"""Engine command builders + line parsers — no downloads, no network."""
from engines.spotify import SpotifyEngine
from engines.youtube import YouTubeEngine


def test_youtube_build_defaults_to_best_and_newline():
    cmd = YouTubeEngine().build_command(url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt")
    assert "--newline" in cmd and "https://www.youtube.com/watch?v=x" in cmd
    assert any("bestvideo+bestaudio" in c for c in cmd)


def test_youtube_audio_format_extracts_mp3():
    cmd = YouTubeEngine().build_command(
        url="https://youtu.be/x", out_dir="/tmp/yt",
        stream_preset="Best Available (Source)", file_format="MP3 Audio (.mp3)",
    )
    assert "-x" in cmd and "--audio-format" in cmd and "mp3" in cmd


def test_youtube_subs_are_nonfatal_without_sleep_stalls():
    cmd = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt",
        capture_subs=True,
    )
    for flag in ("--write-subs", "--write-auto-subs", "--ignore-errors",
                 "--retries", "--extractor-retries"):
        assert flag in cmd
    for flag in ("--sleep-requests", "--sleep-subtitles", "--retry-sleep"):
        assert flag not in cmd
    # No-sub runs keep strict behavior: a real failure must still fail loudly.
    strict = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt")
    assert "--ignore-errors" not in strict


def _sub_spec(**kw):
    cmd = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt",
        capture_subs=True, **kw)
    return cmd[cmd.index("--sub-langs") + 1]


def test_youtube_sub_lang_picker_single_all_and_invalid():
    assert _sub_spec(lang="Spanish") == "es"  # exact code: video + 1 transcript, never en-orig extras
    assert _sub_spec(lang="English") == "en"
    assert _sub_spec(lang="All languages") == "all,-live_chat"
    assert _sub_spec(lang="en") == "en"  # legacy bare code
    assert _sub_spec(lang="en.*,ja|evil") == "en"  # injection falls back


def test_youtube_subs_request_single_native_format(monkeypatch):
    monkeypatch.setattr("engines.youtube.find_ffmpeg", lambda: "/fake/ffmpeg")
    cmd = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt",
        capture_subs=True, caption_env="SubRip Subtitle (.srt)",
    )
    fmt = cmd[cmd.index("--sub-format") + 1]
    assert fmt.split("/")[0] == "srt"  # wanted container first: one output type
    assert "--convert-subs" in cmd and cmd[cmd.index("--convert-subs") + 1] == "srt"


def test_youtube_transcript_only_skips_media_and_implies_subs():
    cmd = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt",
        capture_subs=False, transcript_only=True,
    )
    assert "--skip-download" in cmd and "--write-subs" in cmd
    strict = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt")
    assert "--skip-download" not in strict


def test_youtube_remux_requested_even_without_ffmpeg(monkeypatch):
    monkeypatch.setattr("engines.youtube.find_ffmpeg", lambda: None)
    cmd = YouTubeEngine().build_command(
        url="https://www.youtube.com/watch?v=x", out_dir="/tmp/yt",
        file_format="MP4 Video (.mp4)",
    )
    assert "--remux-video" in cmd and "mp4" in cmd


def test_youtube_parses_percent_and_errors():
    eng = YouTubeEngine()
    up = eng.parse_line("[download]  45.2% of ~10.5MiB at 2.0MiB/s ETA 00:05")
    assert up.percent == 45.2 and up.tag == "action_blue"
    assert eng.parse_line("ERROR: Video unavailable").tag == "danger"
    assert eng.parse_line("[download] Downloading video 2 of 10").current_item == 2


def test_spotify_build_pins_format_threads_and_lrc():
    cmd = SpotifyEngine().build_command(
        url="https://open.spotify.com/track/x", out_dir="/tmp/sp",
        stream_preset="MP3 Audio (.mp3)", bitrate="320 kbps (High)", generate_lrc=True,
    )
    assert "--format" in cmd and "mp3" in cmd
    assert "--bitrate" in cmd and "320k" in cmd
    assert "--threads" in cmd and "--generate-lrc" in cmd


def test_spotify_parses_progress_and_failure():
    eng = SpotifyEngine()
    up = eng.parse_line("Downloading 3 / 12 tracks")
    assert (up.current_item, up.total_items) == (3, 12)
    assert up.percent == 25.0
    assert eng.parse_line("Downloaded 12 / 12 files").percent == 100.0
    assert eng.parse_line("Found 12 songs").total_items == 12
    assert eng.parse_line("Failed to download track").tag == "danger"
