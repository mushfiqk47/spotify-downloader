// electron-builder afterPack hook: applies the app icon + version metadata
// with the already-cached rcedit binary, bypassing the winCodeSign 7z
// extraction (which fails on non-admin machines due to macOS symlinks).
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function findRcedit() {
  const base =
    process.env.ELECTRON_BUILDER_CACHE ||
    path.join(process.env.LOCALAPPDATA || path.join(process.env.USERPROFILE || '', 'AppData', 'Local'), 'electron-builder', 'Cache');
  const dir = path.join(base, 'winCodeSign');
  try {
    for (const entry of fs.readdirSync(dir)) {
      const candidate = path.join(dir, entry, 'rcedit-x64.exe');
      if (fs.existsSync(candidate)) return candidate;
    }
  } catch { /* ignore */ }
  return null;
}

exports.default = async function afterPack(context) {
  // Clean-OS: backend (+ bundled ffmpeg sidecar) must stay executable
  // inside the packaged app on Linux/macOS (onefile exe or onedir folder).
  try {
    const chmod = (p) => { try { fs.chmodSync(p, 0o755); } catch { /* ignore */ } };
    const resCandidates = [
      path.join(context.appOutDir, 'resources', 'backend'),
      path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`, 'Contents', 'Resources', 'backend'),
      path.join(context.appOutDir, `${context.packager.appInfo.productName}.app`, 'Contents', 'Resources', 'backend'),
    ];

    for (const resDir of resCandidates) {
      if (!fs.existsSync(resDir)) continue;
      for (const n of ['streamrip-backend', 'streamrip-backend.exe', 'ffmpeg', 'ffmpeg.exe']) {
        const p = path.join(resDir, n);
        if (fs.existsSync(p) && fs.statSync(p).isFile()) chmod(p);
      }
      const oneDir = path.join(resDir, 'streamrip-backend');
      if (fs.existsSync(oneDir) && fs.statSync(oneDir).isDirectory()) {
        for (const n of fs.readdirSync(oneDir)) {
          const p = path.join(oneDir, n);
          try {
            const st = fs.statSync(p);
            if (st.isFile()) {
              if (
                n.startsWith('streamrip-backend') ||
                n.endsWith('.so') ||
                n.endsWith('.dylib') ||
                n === 'ffmpeg' ||
                !n.includes('.')
              ) {
                chmod(p);
              }
            }
          } catch { /* ignore */ }
        }
      }
    }
  } catch { /* ignore */ }
  if (context.packager.platform.name !== 'windows') return;
  const exePath = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.exe`);
  const iconPath = path.join(context.packager.projectDir, 'build', 'icon.ico');
  const rcedit = findRcedit();
  if (!rcedit) {
    console.warn('afterPack: rcedit not found in winCodeSign cache, skipping icon.');
    return;
  }
  if (!fs.existsSync(exePath)) {
    console.warn(`afterPack: exe not found at ${exePath}, skipping icon.`);
    return;
  }
  const { productName, version } = context.packager.appInfo;
  const args = [exePath, '--set-icon', iconPath,
    '--set-version-string', 'ProductName', productName,
    '--set-version-string', 'FileDescription', productName,
    '--set-version-string', 'CompanyName', 'StreamRip',
    '--set-version-string', 'LegalCopyright', 'Copyright (c) StreamRip',
    '--set-file-version', version,
    '--set-product-version', version,
  ];
  console.log(`afterPack: applying icon via ${rcedit}`);
  execFileSync(rcedit, args, { stdio: 'inherit' });
  console.log('afterPack: icon + version metadata applied.');
};
