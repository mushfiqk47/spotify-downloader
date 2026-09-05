/**
 * StreamRip Core - Dependency Update Controller
 */

async function refreshUpdates(silent) {
  const elUpdate = document.getElementById('btn-update');
  if (!elUpdate) return;

  try {
    elUpdate.disabled = true;
    if (!silent) elUpdate.textContent = 'Checking...';

    const res = await fetch('/api/check-updates');
    const data = await res.json();
    AppState.pendingUpdates = data.updates || {};
    const names = Object.keys(AppState.pendingUpdates);

    if (names.length) {
      elUpdate.textContent = `Update Available (${names.length})`;
      elUpdate.classList.add('has-update');
      if (!silent) appendLog(`Updates available: ${names.join(', ')}`, 'entry-blue');
    } else {
      elUpdate.textContent = 'Up to Date';
      elUpdate.classList.remove('has-update');
      if (!silent) appendLog('All dependencies are up to date.');
    }
  } catch (err) {
    elUpdate.textContent = 'Check Updates';
    if (!silent) appendLog(`Update check failed: ${err}`, 'entry-ink');
  } finally {
    elUpdate.disabled = false;
  }
}

async function handleUpdateClick() {
  const elUpdate = document.getElementById('btn-update');
  const names = Object.keys(AppState.pendingUpdates);

  if (!names.length) {
    refreshUpdates(false);
    return;
  }

  if (elUpdate) {
    elUpdate.disabled = true;
    elUpdate.textContent = 'Updating...';
  }

  appendLog(`Upgrading: ${names.join(' ')}`, 'entry-blue');

  try {
    const res = await fetch('/api/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ packages: names }),
    });

    const data = await res.json();
    const jobId = data.job_id;

    const timer = setInterval(async () => {
      const r = await fetch(`/api/job/${jobId}`);
      const d = await r.json();
      (d.logs || []).forEach((l) => appendLog(l.msg, tagToClass(l.tag)));

      if (d.done) {
        clearInterval(timer);
        appendLog('Upgrade finished. Re-checking...');
        AppState.pendingUpdates = {};
        refreshUpdates(true);
      }
    }, 500);
  } catch (err) {
    appendLog(`Upgrade failed: ${err}`, 'entry-ink');
    if (elUpdate) elUpdate.disabled = false;
  }
}
