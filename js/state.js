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
 * Fetch resolved default paths and platform info from backend
 */
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    AppState.appConfig = data;
    const elDest = document.getElementById('dest-path');
    if (elDest && !elDest.value) {
      elDest.value = AppState.mode === 'youtube' ? (data.youtube_out || '') : (data.spotify_out || '');
    }
  } catch (e) {
    /* ignore network / offline errors */
  }
}

/**
 * Switch extraction mode between YouTube and Spotify
 */
function setMode(nextMode) {
  AppState.mode = nextMode;

  const elModeYt = document.getElementById('mode-youtube');
  const elModeSp = document.getElementById('mode-spotify');
  const elHint = document.querySelector('.field-hint');
  const elUrl = document.getElementById('target-url');
  const elDest = document.getElementById('dest-path');

  if (elModeYt) elModeYt.classList.toggle('active', nextMode === 'youtube');
  if (elModeSp) elModeSp.classList.toggle('active', nextMode === 'spotify');

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
}
