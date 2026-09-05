// Minimal preload: keep Node out of the renderer for security.
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('streamrip', {
  version: '1.0.0',
});
