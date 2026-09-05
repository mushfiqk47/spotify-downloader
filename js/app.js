/**
 * StreamRip Core - Application Bootstrap & Event Wiring
 */

function nearBottom() {
  const elFeed = document.getElementById('console-feed');
  if (!elFeed) return true;
  return elFeed.scrollHeight - elFeed.scrollTop - elFeed.clientHeight < 40;
}

function appendLog(text, variant = '') {
  const elFeed = document.getElementById('console-feed');
  if (!elFeed) return;

  const stick = nearBottom();
  const line = document.createElement('div');
  if (variant) line.classList.add(variant);
  line.textContent = `[${new Date().toTimeString().split(' ')[0]}] ${text}`;
  elFeed.appendChild(line);

  while (elFeed.children.length > 1200) {
    elFeed.removeChild(elFeed.firstChild);
  }

  if (stick) {
    elFeed.scrollTop = elFeed.scrollHeight;
  }
}

function tagToClass(tag) {
  if (tag === 'success') return 'entry-ink';
  if (tag === 'action_blue') return 'entry-blue';
  if (tag === 'danger') return 'entry-ink';
  return '';
}

document.addEventListener('DOMContentLoaded', () => {
  const elModeYt = document.getElementById('mode-youtube');
  const elModeSp = document.getElementById('mode-spotify');
  const elClearFeed = document.getElementById('btn-clear-feed');
  const elDownload = document.getElementById('btn-download');
  const elUpdate = document.getElementById('btn-update');

  // Mode toggling
  if (elModeYt) elModeYt.addEventListener('click', () => setMode('youtube'));
  if (elModeSp) elModeSp.addEventListener('click', () => setMode('spotify'));

  // Clear log buffer
  if (elClearFeed) {
    elClearFeed.addEventListener('click', () => {
      const elFeed = document.getElementById('console-feed');
      if (elFeed) {
        elFeed.innerHTML = '';
        appendLog('Pipeline buffer cleared.');
      }
    });
  }

  // Download & Update actions
  if (elDownload) elDownload.addEventListener('click', handleDownloadClick);
  if (elUpdate) elUpdate.addEventListener('click', handleUpdateClick);

  // Initialize modular folder picker
  initFolderPicker();

  // Persist control changes + keep quality list in sync with file format
  initControlSync();

  // Initialize custom themed dropdowns
  initCustomDropdowns();

  // Synchronize initial mode controls visibility
  updateModeVisibility(AppState.mode);

  // Load platform paths and perform background update check
  loadConfig();
  refreshUpdates(true);
});
