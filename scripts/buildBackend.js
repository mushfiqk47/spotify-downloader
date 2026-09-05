const { spawnSync, execSync } = require('child_process');
const os = require('os');

// Ensure no stale backend process is locking .pyd, .dll, or .exe files
if (os.platform() === 'win32') {
  try {
    execSync('taskkill /F /IM streamrip-backend.exe /T', { stdio: 'ignore' });
  } catch {
    // Ignore error when no instance is running
  }
} else {
  try {
    execSync('pkill -f streamrip-backend', { stdio: 'ignore' });
  } catch {
    // Ignore error when no instance is running
  }
}

// Run PyInstaller compilation
const args = ['backend.spec', '--noconfirm', '--distpath', 'dist-backend'];
const proc = spawnSync('pyinstaller', args, { stdio: 'inherit', shell: true });

process.exit(proc.status ?? 0);
