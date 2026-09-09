// Bumps package.json patch version by +1 (1.0.2 -> 1.0.3) so EVERY Windows
// installer build ships a new exe filename:
//   StreamRip-Core-Setup-<version>.exe   (electron-builder ${version})
//
// Wired into `npm run dist`, which is the only supported way to build the exe.
// Usage:
//   node scripts/bumpVersion.js            # bump for real
//   node scripts/bumpVersion.js --dry-run  # print what would happen, change nothing
const fs = require('fs');
const path = require('path');

const DRY = process.argv.includes('--dry-run') || process.argv.includes('--check');
const pkgPath = path.join(__dirname, '..', 'package.json');

let pkg;
try {
  pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
} catch (e) {
  console.error(`bumpVersion: cannot read ${pkgPath}: ${e.message}`);
  process.exit(1);
}

const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(pkg.version || '');
if (!m) {
  console.error(`bumpVersion: unsupported version "${pkg.version}" (want X.Y.Z)`);
  process.exit(1);
}
const next = `${m[1]}.${m[2]}.${Number(m[3]) + 1}`;

if (DRY) {
  console.log(`bumpVersion: ${m[0]} -> ${next} (dry run, not written)`);
  process.exit(0);
}

pkg.version = next;
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
console.log(`bumpVersion: ${m[0]} -> ${next}`);
