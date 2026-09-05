// Minimal preload: keep Node out of the renderer for security.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('streamrip', {
  version: '1.0.0',
  // Opens the native Windows folder dialog. Returns absolute path or null.
  selectFolder: (startPath) => ipcRenderer.invoke('select-folder', startPath || null),
});
