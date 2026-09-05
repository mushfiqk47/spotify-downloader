const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const PORT = process.env.STREAMRIP_PORT ? Number(process.env.STREAMRIP_PORT) : 5050;
const BACKEND_URL = `http://127.0.0.1:${PORT}`;

let mainWindow = null;
let backendProc = null;

function backendCandidates() {
  const list = [];
  if (app.isPackaged) {
    // electron-builder extraResources -> <resources>/backend/
    list.push(path.join(process.resourcesPath, 'backend', 'streamrip-backend.exe'));
    list.push(path.join(process.resourcesPath, 'backend', 'streamrip-backend'));
  }
  // unpacked / dir builds + local dev after `npm run build:backend`
  list.push(path.join(__dirname, '..', 'dist-backend', 'streamrip-backend.exe'));
  list.push(path.join(__dirname, '..', 'dist-backend', 'streamrip-backend'));
  return list;
}

function findBackend() {
  for (const p of backendCandidates()) {
    try {
      if (fs.existsSync(p)) return p;
    } catch { /* ignore */ }
  }
  return null;
}

function chmodExec(p) {
  if (process.platform === 'win32') return;
  try { fs.chmodSync(p, 0o755); } catch { /* ignore */ }
}

function startBackend() {
  const exe = findBackend();
  if (exe) {
    chmodExec(exe);
    // bundled ffmpeg sidecar (if shipped via extraResources) must stay executable
    try {
      const dir = path.dirname(exe);
      for (const n of ['ffmpeg', 'ffmpeg.exe']) {
        const f = path.join(dir, n);
        if (fs.existsSync(f)) chmodExec(f);
      }
    } catch { /* ignore */ }
    backendProc = spawn(exe, [], {
      env: { ...process.env, STREAMRIP_PORT: String(PORT) },
      stdio: 'ignore',
      windowsHide: true,
    });
    backendProc.on('error', () => { backendProc = null; });
    backendProc.unref?.();
    return;
  }
  // Dev fallback: run from source with system python (no exe built yet).
  const root = path.join(__dirname, '..');
  const py = process.platform === 'win32' ? 'python' : 'python3';
  backendProc = spawn(py, ['server.py'], {
    cwd: root,
    env: { ...process.env, STREAMRIP_PORT: String(PORT) },
    stdio: 'ignore',
    shell: process.platform === 'win32',
    windowsHide: true,
  });
  backendProc.on('error', () => { backendProc = null; });
  backendProc.unref?.();
}

function waitForBackend(timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      const req = http.get(`${BACKEND_URL}/api/health`, (res) => {
        res.resume();
        resolve(true);
      });
      req.on('error', () => {
        if (Date.now() - started > timeoutMs) return resolve(false);
        setTimeout(tick, 400);
      });
      req.setTimeout(2000, () => req.destroy());
    };
    tick();
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1060,
    height: 760,
    minWidth: 900,
    minHeight: 620,
    title: 'StreamRip Core',
    autoHideMenuBar: true,
    backgroundColor: '#f4f4f4',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
    },
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  const ready = await waitForBackend(30000);
  if (ready) {
    await mainWindow.loadURL(BACKEND_URL);
  } else {
    // Show UI shell anyway; backend error will surface in the log pane.
    const fallback = path.join(__dirname, '..', 'UI.html');
    if (fs.existsSync(fallback)) await mainWindow.loadFile(fallback);
    else await mainWindow.loadURL(BACKEND_URL);
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  // Native Windows folder picker for the Browse button.
  // Renderer calls: await window.streamrip.selectFolder(startPath?)
  ipcMain.handle('select-folder', async (_event, startPath) => {
    try {
      const opts = { properties: ['openDirectory', 'createDirectory'] };
      if (typeof startPath === 'string' && startPath && fs.existsSync(startPath)) {
        opts.defaultPath = startPath;
      }
      const res = await dialog.showOpenDialog(mainWindow, opts);
      if (res.canceled || !res.filePaths || !res.filePaths.length) return null;
      return res.filePaths[0];
    } catch { return null; }
  });

  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    startBackend();
    await createWindow();
    app.on('activate', async () => {
      if (BrowserWindow.getAllWindows().length === 0) await createWindow();
    });
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });

  app.on('before-quit', () => {
    try {
      if (backendProc && !backendProc.killed) backendProc.kill();
    } catch { /* ignore */ }
    backendProc = null;
  });
}
