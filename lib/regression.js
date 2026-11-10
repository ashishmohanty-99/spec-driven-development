'use strict';
// Runs the full regression sweep: unit/integration tests the project already has, then the
// generated Playwright e2e suite (tests/e2e) if one is installed, then `verify` for every
// feature. One command, one exit code, so it drops into CI as the single required check that
// covers build -> verify of the SDLC.
const { spawnSync } = require('child_process');
const path = require('path');
const { exists, readJson } = require('./util');
const { listFeatures, verifyFeature } = require('./spec');

function run(cmd, args, cwd) {
  const label = `${cmd} ${args.join(' ')}`;
  const res = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: process.platform === 'win32' });
  return { label, status: res.status === null ? 1 : res.status, skipped: false };
}

function regression(root, { strict = false, pentestTarget = null } = {}) {
  const results = [];
  const pkg = readJson(path.join(root, 'package.json'));
  if (pkg && pkg.scripts && pkg.scripts.test) results.push(run('npm', ['test'], root));
  else results.push({ label: '(no "test" script in package.json)', status: 0, skipped: true });

  if (exists(path.join(root, 'playwright.config.js')) || exists(path.join(root, 'playwright.config.ts'))) {
    results.push(run('npx', ['playwright', 'test'], root));
  } else {
    results.push({ label: '(no playwright.config — run: sdd gen-tests <feature>)', status: 0, skipped: true });
  }

  const features = listFeatures(root);
  let gateErrors = 0;
  for (const f of features) { const r = verifyFeature(root, f, { strict }); gateErrors += r.errors.length; }
  results.push({ label: `sdd verify (${features.length} feature(s))`, status: gateErrors ? 1 : 0, skipped: features.length === 0 });

  if (pentestTarget) {
    const { pentest } = require('./pentest');
    const p = pentest({ target: pentestTarget, failOn: 'high' });
    results.push({ label: `sdd pentest --target ${pentestTarget}`, status: p.ran ? (p.status ?? 1) : 0, skipped: !p.ran, note: p.reason });
  }

  return { results, ok: results.every((r) => r.status === 0) };
}

module.exports = { regression };
