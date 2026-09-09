/**
 * StreamRip Core - State Management
 */
const AppState = {
  mode: 'youtube',
  isProcessing: false,
  activeJob: null,
  pollTimer: null,
  pendingUpdates: {},
  appConfig: null,
};

/**
 * Fetch this user's resolved default paths and platform info from backend.
 * The backend sanitizes stale paths, so these are always THIS user's
 * folders — never another machine's absolute path.
 */
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    AppState.appConfig = data;
    const savedMode = (data.mode === 'youtube' || data.mode === 'spotify') ? data.mode : AppState.mode;
    renderModeUI(savedMode);
    restoreControls(data);
  } catch (e) {
    updateModeVisibility(AppState.mode);
    refreshQualityOptions();
    /* ignore network / offline errors */
  }
}

/** Quality menus: video file formats get video qualities, audio gets audio. */
const YT_VIDEO_QUALS = ['Best Available (Source)', '1080p (FHD)', '720p (HD)', '480p (SD)'];
const YT_AUDIO_QUALS = ['Best Available', 'High Quality', 'Medium Quality', 'Compact File'];

function ytFileIsAudio() {
  const el = document.getElementById('select-file-format');
  const t = el && el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : '';
  return /audio/i.test(t);
}

function refreshQualityOptions() {
  const q = document.getElementById('select-quality');
  const label = document.getElementById('label-quality');
  if (!q) return;
  const audio = ytFileIsAudio();
  const prev = q.options[q.selectedIndex] ? q.options[q.selectedIndex].text : '';
  const list = audio ? YT_AUDIO_QUALS : YT_VIDEO_QUALS;
  const keep = list.includes(prev) ? prev : list[0];
  q.innerHTML = '';
  for (const t of list) {
    const o = document.createElement('option');
    o.textContent = t;
    q.appendChild(o);
  }
  q.value = keep;
  if (label) label.textContent = audio ? 'Audio Quality' : 'Media Stream';
}

/** Apply saved prefs to every control (selects by visible text, checkboxes). */
function restoreControls(data) {
  if (!data) return;
  const textSelect = (id, val) => {
    const el = document.getElementById(id);
    if (!el || typeof val !== 'string') return;
    const hit = [...el.options].find((o) => o.text === val);
    if (hit) el.value = hit.value || hit.text;
  };
  const chk = (id, val) => {
    const el = document.getElementById(id);
    if (el && typeof val === 'boolean') el.checked = val;
  };
  // File format first: it decides which quality list exists.
  textSelect('select-file-format', data.yt_file_format);
  refreshQualityOptions();
  textSelect('select-quality', data.yt_stream);
  textSelect('select-caption', data.yt_caption_env);
  textSelect('select-transcript-lang', data.yt_lang);
  textSelect('select-format', data.sp_stream);
  textSelect('select-bitrate', data.sp_bitrate);
  chk('chk-transcript', data.yt_capture_subs);
  chk('chk-lyrics', data.sp_generate_lrc);
}

/** Save every control change as the user makes it (fire-and-forget). */
function initControlSync() {
  const on = (id, evt, fn) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(evt, fn);
  };
  const selText = (id) => {
    const el = document.getElementById(id);
    return el && el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : '';
  };
  on('select-file-format', 'change', () => {
    refreshQualityOptions();
    saveConfig({ yt_file_format: selText('select-file-format') });
  });
  on('select-quality', 'change', () => saveConfig({ yt_stream: selText('select-quality') }));
  on('select-caption', 'change', () => saveConfig({ yt_caption_env: selText('select-caption') }));
  on('select-transcript-lang', 'change', () => saveConfig({ yt_lang: selText('select-transcript-lang') }));
  on('select-format', 'change', () => saveConfig({ sp_stream: selText('select-format') }));
  on('select-bitrate', 'change', () => saveConfig({ sp_bitrate: selText('select-bitrate') }));
  on('chk-transcript', 'change', () => {
    saveConfig({ yt_capture_subs: document.getElementById('chk-transcript').checked });
  });

  on('chk-lyrics', 'change', () => {
    saveConfig({ sp_generate_lrc: document.getElementById('chk-lyrics').checked });
  });
}

/**
 * Persist this user's own choices (out folder / mode) to the backend.
 * Fire-and-forget: a save failure must never block the download flow.
 */
async function saveConfig(patch) {
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch || {}),
    });
    const data = await res.json();
    if (data && (data.youtube_out || data.spotify_out)) {
      AppState.appConfig = Object.assign({}, AppState.appConfig, data);
    }
  } catch (e) {
    /* ignore — choice still applies to this session */
  }
}

/** Remember the folder currently shown in the Export Destination field. */
function persistDestFolder() {
  const elDest = document.getElementById('dest-path');
  if (!elDest || !elDest.value.trim()) return;
  const key = AppState.mode === 'youtube' ? 'youtube_out' : 'spotify_out';
  saveConfig({ [key]: elDest.value.trim() });
}

/**
 * Update UI controls visibility based on the active mode:
 * - YouTube mode: show YouTube selectors and options card; hide Spotify controls.
 * - Spotify mode: show Spotify selectors and options card; hide YouTube controls.
 */
function updateModeVisibility(mode) {
  const isYt = mode === 'youtube';
  const mapping = [
    ['youtube-selectors', isYt],
    ['youtube-options-card', isYt],
    ['spotify-selectors', !isYt],
    ['spotify-options-card', !isYt],
  ];
  for (const [id, show] of mapping) {
    const el = document.getElementById(id);
    if (el) {
      el.hidden = !show;
      if (show) {
        el.removeAttribute('hidden');
        el.style.display = '';
      } else {
        el.setAttribute('hidden', '');
        el.style.display = 'none';
      }
    }
  }
}

/**
 * Render every mode-dependent control (no saving — used on boot restore).
 */
function renderModeUI(nextMode) {
  AppState.mode = nextMode;

  const elModeYt = document.getElementById('mode-youtube');
  const elModeSp = document.getElementById('mode-spotify');
  const elHint = document.querySelector('.field-hint');
  const elUrl = document.getElementById('target-url');
  const elDest = document.getElementById('dest-path');

  if (elModeYt) elModeYt.classList.toggle('active', nextMode === 'youtube');
  if (elModeSp) elModeSp.classList.toggle('active', nextMode === 'spotify');
  if (elModeYt) elModeYt.setAttribute('aria-selected', String(nextMode === 'youtube'));
  if (elModeSp) elModeSp.setAttribute('aria-selected', String(nextMode === 'spotify'));
  document.title = nextMode === 'youtube' ? 'StreamRip Core \u00b7 Video & Captions' : 'StreamRip Core \u00b7 Music & Lyrics';

  if (elHint) {
    elHint.textContent = nextMode === 'youtube' ? 'youtube / playlists' : 'spotify / albums / tracks';
  }

  if (elUrl) {
    elUrl.placeholder = nextMode === 'youtube'
      ? 'https://www.youtube.com/watch?v=...'
      : 'https://open.spotify.com/playlist/...';
  }

  if (AppState.appConfig && elDest) {
    if (nextMode === 'youtube' && (!elDest.value || elDest.value === AppState.appConfig.spotify_out)) {
      elDest.value = AppState.appConfig.youtube_out || '';
    } else if (nextMode === 'spotify' && (!elDest.value || elDest.value === AppState.appConfig.youtube_out)) {
      elDest.value = AppState.appConfig.spotify_out || '';
    }
  }

  // Update controls visibility: in Spotify mode, completely hide YouTube selectors and options
  updateModeVisibility(nextMode);
  if (nextMode === 'youtube') refreshQualityOptions();
}

/**
 * Switch extraction mode between YouTube and Spotify
 */
function setMode(nextMode) {
  renderModeUI(nextMode);
  saveConfig({ mode: nextMode });
}
