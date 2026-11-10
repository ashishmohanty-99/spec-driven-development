'use strict';
const fs = require('fs');
const path = require('path');

const SKIP_DIRS = new Set(['node_modules', '.git', 'dist', 'build', 'out', '.next', '.nuxt', 'target',
  'vendor', '.venv', 'venv', '__pycache__', '.gradle', '.idea', '.vscode', 'coverage', '.cache', '.turbo']);

function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function readText(p) { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } }
function readJson(p) { const t = readText(p); if (t == null) return null; try { return JSON.parse(t); } catch { return null; } }
function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }

/** Bounded breadth-first walk returning repo-relative file paths. Names only; never reads content. */
function walk(root, { maxFiles = 5000, maxDepth = 6 } = {}) {
  const files = [];
  const queue = [['', 0]];
  while (queue.length && files.length < maxFiles) {
    const [rel, depth] = queue.shift();
    let entries;
    try { entries = fs.readdirSync(path.join(root, rel), { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) {
        if (!SKIP_DIRS.has(e.name) && depth < maxDepth) queue.push([r, depth + 1]);
      } else if (e.isFile()) {
        files.push(r);
        if (files.length >= maxFiles) break;
      }
    }
  }
  return files;
}

/** Copy a directory tree. Never overwrites existing files unless force. Returns list of written paths. */
function copyDir(src, dest, { force = false } = {}) {
  const written = [];
  mkdirp(dest);
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dest, e.name);
    if (e.isDirectory()) written.push(...copyDir(s, d, { force }));
    else if (force || !exists(d)) { fs.copyFileSync(s, d); written.push(d); }
  }
  return written;
}

module.exports = { exists, readText, readJson, mkdirp, walk, copyDir, SKIP_DIRS };
