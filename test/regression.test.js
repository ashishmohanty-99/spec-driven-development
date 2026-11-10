'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { regression } = require('../lib/regression');

const CLI = path.join(__dirname, '..', 'bin', 'sdd.js');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sdd-reg-'));

test('regression skips the unit-test and e2e steps cleanly when neither is set up, and still runs the gate', () => {
  const r = tmp();
  execFileSync('node', [CLI, 'init', '--dir', r]);
  fs.unlinkSync(path.join(r, 'playwright.config.js')); // simulate "not yet generated"
  const { results, ok } = regression(r);
  const byLabel = Object.fromEntries(results.map((x) => [x.label, x]));
  assert.ok(Object.keys(byLabel).some((l) => l.includes('no "test" script')));
  assert.ok(Object.keys(byLabel).some((l) => l.includes('no playwright.config')));
  assert.ok(ok);
});

test('regression reports a failing sdd verify gate', () => {
  const r = tmp();
  execFileSync('node', [CLI, 'init', '--dir', r]);
  fs.unlinkSync(path.join(r, 'playwright.config.js'));
  const dir = path.join(r, '.sdd/specs/bad');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'spec.md'), 'Status: approved\n- REQ-001: a');
  fs.writeFileSync(path.join(dir, 'tasks.md'), '- [ ] T-001 x'); // orphan: no plan.md, no covers
  const { ok, results } = regression(r);
  assert.strictEqual(ok, false);
  assert.ok(results.find((x) => x.label.includes('sdd verify')).status !== 0);
});

test('pentest step is skipped (not failed) when no target is given, and reported with a reason when one is', () => {
  const r = tmp();
  execFileSync('node', [CLI, 'init', '--dir', r]);
  fs.unlinkSync(path.join(r, 'playwright.config.js'));
  const noTarget = regression(r);
  assert.ok(!noTarget.results.some((x) => x.label.startsWith('sdd pentest')));
  const withTarget = regression(r, { pentestTarget: './app' });
  const step = withTarget.results.find((x) => x.label.startsWith('sdd pentest'));
  assert.ok(step && step.skipped && step.status === 0);
});
