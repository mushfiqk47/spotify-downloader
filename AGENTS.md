# StreamRip Core — agent rules (read before changing build/release code)

## 1. Exe version auto-bump (HARD RULE)

- Source of truth for the app version is `version` in `package.json` (currently 1.0.x).
- **Every Windows exe build MUST ship a version +1 higher than the last.**
  `npm run dist` runs `node scripts/bumpVersion.js` first, which bumps the
  patch number (1.0.2 → 1.0.3), so the installer filename
  `StreamRip-Core-Setup-<version>.exe` (electron-builder `${version}`) is
  always new. This is automatic — do not bump by hand alongside a build.
- **Never run `electron-builder` directly for a release** — it bypasses the
  bump and reuses the previous exe filename. Always use:
  - `npm run pack` — full pipeline: backend (PyInstaller) + version bump + exe
  - `npm run dist` — version bump + exe only (backend already built)
- `dist:linux` / `dist:mac` do NOT auto-bump (rule is exe-only). If a Mac/Linux
  release needs a new number, run `node scripts/bumpVersion.js` once by hand.
- Verify the bump after building: `node -e "console.log(require('./package.json').version)"`
  and confirm `dist-installer/StreamRip-Core-Setup-<that version>.exe` exists.
- Pre-release check that never fails silently: `node scripts/bumpVersion.js --dry-run`.

## 2. Python deps live in .venv, never global

- `pip install -r requirements.txt` in global python BREAKS the machine's other
  tools (SpotDL pins fastapi 0.103 / anyio 3.x; agent tools need anyio>=4.10).
- Windows: `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
- Linux/macOS: `./setup.sh` (creates `.venv` automatically).
- `requirements.txt` is `==` pinned; ranges live in `requirements.in`.

## 3. Before calling anything done

- `make test` (compileall + pytest) must pass. New backend logic needs a test
  in `tests/` through the public interface — no Tk/Electron in tests.
- Keep `server.py` job-store invariants: cap `MAX_JOBS`, TTL prune, URL
  allowlist per mode. Don't weaken them for convenience.
