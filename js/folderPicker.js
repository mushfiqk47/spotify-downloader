/**
 * StreamRip Core - Folder Picker (Electron Native + In-Browser Fallback)
 */

let folderCurrent = '';

async function handleBrowseClick() {
  const elDest = document.getElementById('dest-path');
  const currentVal = elDest ? elDest.value.trim() : '';

  // 1) Electron: native OS folder dialog (preferred).
  try {
    if (window.streamrip && typeof window.streamrip.selectFolder === 'function') {
      const picked = await window.streamrip.selectFolder(currentVal || undefined);
      if (picked) {
        if (elDest) elDest.value = picked;
        appendLog(`Export folder set: ${picked}`);
      }
      return;
    }
  } catch (e) {
    /* fall through to in-browser picker */
  }

  // 2) Browser mode: in-page folder browser backed by /api/browse.
  openFolderPicker(currentVal);
}

async function loadFolder(targetPath) {
  const elOverlay = document.getElementById('folder-overlay');
  const elFolderPath = document.getElementById('folder-path');
  const elFolderList = document.getElementById('folder-list');
  const elBtnDrives = document.getElementById('folder-drives');

  if (!elFolderPath || !elFolderList) return;

  elFolderPath.textContent = 'Loading...';
  elFolderList.innerHTML = '';

  try {
    const res = await fetch(`/api/browse?path=${encodeURIComponent(targetPath || '')}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    folderCurrent = data.path;
    elFolderPath.textContent = data.path;
    if (elOverlay) elOverlay.dataset.parent = data.parent || '';

    const drives = data.drives || [];
    if (elBtnDrives) elBtnDrives.style.display = drives.length ? '' : 'none';

    if (!data.dirs || !data.dirs.length) {
      const empty = document.createElement('div');
      empty.className = 'folder-item empty';
      empty.textContent = 'No subfolders here.';
      elFolderList.appendChild(empty);
    } else {
      data.dirs.forEach((d) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'folder-item';
        b.textContent = '\uD83D\uDCC1 ' + d.name;
        b.addEventListener('click', () => loadFolder(d.path));
        elFolderList.appendChild(b);
      });
    }
  } catch (err) {
    elFolderPath.textContent = `Error: ${err.message}`;
  }
}

function openFolderPicker(startPath) {
  const elOverlay = document.getElementById('folder-overlay');
  if (elOverlay) {
    elOverlay.classList.add('open');
    loadFolder(startPath);
  }
}

function closeFolderPicker() {
  const elOverlay = document.getElementById('folder-overlay');
  if (elOverlay) {
    elOverlay.classList.remove('open');
  }
}

function initFolderPicker() {
  const elOverlay = document.getElementById('folder-overlay');
  const elBtnBrowse = document.getElementById('btn-browse');
  const elBtnUp = document.getElementById('folder-up');
  const elBtnHome = document.getElementById('folder-home');
  const elBtnDrives = document.getElementById('folder-drives');
  const elBtnCancel = document.getElementById('folder-cancel');
  const elBtnSelect = document.getElementById('folder-select');
  const elDest = document.getElementById('dest-path');

  if (elBtnBrowse) elBtnBrowse.addEventListener('click', handleBrowseClick);

  if (elBtnUp) {
    elBtnUp.addEventListener('click', () => {
      if (elOverlay && elOverlay.dataset.parent) {
        loadFolder(elOverlay.dataset.parent);
      }
    });
  }

  if (elBtnHome) elBtnHome.addEventListener('click', () => loadFolder(''));
  if (elBtnDrives) elBtnDrives.addEventListener('click', () => loadFolder('__drives__'));
  if (elBtnCancel) elBtnCancel.addEventListener('click', closeFolderPicker);

  if (elOverlay) {
    elOverlay.addEventListener('click', (e) => {
      if (e.target === elOverlay) closeFolderPicker();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFolderPicker();
  });

  if (elBtnSelect) {
    elBtnSelect.addEventListener('click', () => {
      if (folderCurrent && folderCurrent !== '__drives__' && elDest) {
        elDest.value = folderCurrent;
        appendLog(`Export folder set: ${folderCurrent}`);
      }
      closeFolderPicker();
    });
  }
}
