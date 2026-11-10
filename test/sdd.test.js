'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');
const { scan } = require('../lib/scan');
const { parseSpec, parseTasks, verifyFeature, phaseOf } = require('../lib/spec');

const CLI = path.join(__dirname, '..', 'bin', 'sdd.js');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sdd-'));
const write = (root, f, c) => { fs.mkdirSync(path.dirname(path.join(root, f)), { recursive: true }); fs.writeFileSync(path.join(root, f), c); };
const sdd = (root, ...args) => spawnSync('node', [CLI, ...args, '--dir', root], { encoding: 'utf8' });

function sampleRepo() {
  const r = tmp();
  write(r, 'package.json', JSON.stringify({ scripts: { test: 'vitest', lint: 'eslint .' }, devDependencies: { vitest: '1', eslint: '9', typescript: '5' }, dependencies: { express: '4' } }));
  write(r, 'pnpm-lock.yaml', '');
  write(r, 'src/app.ts', 'export {}');
  write(r, 'src/app.test.ts', 'it("works")');
  write(r, '.env', 'SECRET=hunter2');
  write(r, '.github/workflows/ci.yml', 'name: ci');
  return r;
}

test('scan detects stack, commands, CI and sensitive files without reading secrets', () => {
  const p = scan(sampleRepo());
  assert.ok(p.languages.some((l) => l.name === 'TypeScript'));
  assert.deepStrictEqual(p.packageManagers, ['pnpm']);
  assert.ok(p.frameworks.includes('express'));
  assert.ok(p.testTools.includes('vitest'));
  assert.strictEqual(p.commands.test, 'pnpm test');
  assert.deepStrictEqual(p.ci, ['GitHub Actions']);
  assert.deepStrictEqual(p.sensitiveFiles, ['.env']);
  assert.ok(!JSON.stringify(p).includes('hunter2'));
});

test('scan works on an empty directory', () => {
  const p = scan(tmp());
  assert.strictEqual(p.languages.length, 0);
  assert.ok(p.notes.length > 0);
});

test('init installs skills, commands, profile, constitution and is idempotent', () => {
  const r = sampleRepo();
  assert.strictEqual(sdd(r, 'init').status, 0);
  for (const f of ['.sdd/config.json', '.sdd/codebase-profile.md', '.sdd/constitution.md', '.claude/skills/using-sdd/SKILL.md', '.claude/commands/sdd-spec.md', 'CLAUDE.md'])
    assert.ok(fs.existsSync(path.join(r, f)), f);
  fs.appendFileSync(path.join(r, '.sdd/codebase-profile.md'), '\nMY HUMAN NOTE\n');
  fs.writeFileSync(path.join(r, 'CLAUDE.md'), '# Mine\n\n' + fs.readFileSync(path.join(r, 'CLAUDE.md'), 'utf8'));
  assert.strictEqual(sdd(r, 'init').status, 0);
  const claude = fs.readFileSync(path.join(r, 'CLAUDE.md'), 'utf8');
  assert.strictEqual(claude.split('SPECPILOT:BEGIN').length, 2, 'managed block not duplicated');
  assert.ok(claude.startsWith('# Mine'), 'user content kept');
  assert.ok(fs.readFileSync(path.join(r, '.sdd/codebase-profile.md'), 'utf8').includes('MY HUMAN NOTE'), 'human notes survive re-init');
});

test('init --agent generic targets AGENTS.md and .agents/skills', () => {
  const r = tmp();
  assert.strictEqual(sdd(r, 'init', '--agent', 'generic').status, 0);
  assert.ok(fs.existsSync(path.join(r, '.agents/skills/using-sdd/SKILL.md')));
  assert.ok(fs.existsSync(path.join(r, 'AGENTS.md')));
});

test('init does not overwrite user-modified skills without --force', () => {
  const r = tmp(); sdd(r, 'init');
  const f = path.join(r, '.claude/skills/specify/SKILL.md');
  fs.writeFileSync(f, 'custom');
  sdd(r, 'init');
  assert.strictEqual(fs.readFileSync(f, 'utf8'), 'custom');
  sdd(r, 'init', '--force');
  assert.notStrictEqual(fs.readFileSync(f, 'utf8'), 'custom');
});

test('parsers ignore code fences and read ids', () => {
  const s = parseSpec('Status: approved\n- REQ-001: a\n```\n- REQ-999: example\n```\n- **REQ-002**: b\n[NEEDS CLARIFICATION: x]');
  assert.deepStrictEqual(s.reqs, ['REQ-001', 'REQ-002']);
  assert.strictEqual(s.open.length, 1);
  assert.ok(s.approved);
  const t = parseTasks('- [x] T-001 Do it (covers: REQ-001, REQ-002)\n- [ ] T-002 Other');
  assert.deepStrictEqual(t[0].covers, ['REQ-001', 'REQ-002']);
  assert.ok(t[0].done && !t[1].done);
});

function feature(root, { spec, plan, tasks }) {
  const d = '.sdd/specs/f1/';
  if (spec) write(root, d + 'spec.md', spec);
  if (plan) write(root, d + 'plan.md', plan);
  if (tasks) write(root, d + 'tasks.md', tasks);
}

test('verify: fresh template spec has placeholder requirements and open-question markers do not error before planning', () => {
  const r = tmp(); sdd(r, 'init'); sdd(r, 'new', 'f1');
  const v = verifyFeature(r, 'f1');
  assert.deepStrictEqual(v.errors, []);
  assert.ok(v.warnings.some((w) => /placeholder text/.test(w)));
  assert.ok(v.stats.requirements >= 2);
  assert.strictEqual(phaseOf(v.stats), 'CLARIFY / awaiting spec approval');
});

test('verify: uncovered requirement, orphan task and unknown id are errors', () => {
  const r = tmp(); sdd(r, 'init');
  feature(r, { spec: 'Status: approved\n- REQ-001: a\n- REQ-002: b', plan: '# plan', tasks: '- [ ] T-001 x (covers: REQ-001)\n- [ ] T-002 y\n- [ ] T-003 z (covers: REQ-009)' });
  const { errors } = verifyFeature(r, 'f1');
  assert.ok(errors.some((e) => /REQ-002 is not covered/.test(e)));
  assert.ok(errors.some((e) => /T-002 references no requirement/.test(e)));
  assert.ok(errors.some((e) => /unknown REQ-009/.test(e)));
});

test('verify: plan before approval, and open questions after plan, are errors', () => {
  const r = tmp(); sdd(r, 'init');
  feature(r, { spec: 'Status: draft\n- REQ-001: a\n[NEEDS CLARIFICATION: q]', plan: '# plan' });
  const { errors } = verifyFeature(r, 'f1');
  assert.ok(errors.some((e) => /not "Status: approved"/.test(e)));
  assert.ok(errors.some((e) => /NEEDS CLARIFICATION/.test(e)));
});

test('verify: done task without a REQ-tagged test warns, errors in strict, passes when tagged', () => {
  const r = tmp(); sdd(r, 'init');
  feature(r, { spec: 'Status: approved\n- REQ-001: a', plan: '# plan', tasks: '- [x] T-001 x (covers: REQ-001)' });
  assert.ok(verifyFeature(r, 'f1').warnings.some((w) => /REQ-001 has completed task/.test(w)));
  assert.ok(verifyFeature(r, 'f1', { strict: true }).errors.some((e) => /REQ-001/.test(e)));
  write(r, 'test/a.test.js', "it('REQ-001: works', () => {})");
  const v = verifyFeature(r, 'f1', { strict: true });
  assert.deepStrictEqual(v.errors, []);
  assert.strictEqual(phaseOf(v.stats), 'VERIFY / SHIP');
});

test('CLI exit codes: verify fails (1) on errors, passes (0) when clean; unknown command is 2', () => {
  const r = tmp(); sdd(r, 'init');
  feature(r, { spec: 'Status: approved\n- REQ-001: a', plan: '# p', tasks: '- [ ] T-001 x' });
  assert.strictEqual(sdd(r, 'verify', 'f1').status, 1);
  feature(r, { tasks: '- [ ] T-001 x (covers: REQ-001)' });
  assert.strictEqual(sdd(r, 'verify', 'f1').status, 0);
  assert.strictEqual(sdd(r, 'bogus').status, 2);
});

test('new rejects bad names and duplicates', () => {
  const r = tmp(); sdd(r, 'init');
  assert.notStrictEqual(sdd(r, 'new', 'Bad Name').status, 0);
  assert.strictEqual(sdd(r, 'new', 'ok-name').status, 0);
  assert.notStrictEqual(sdd(r, 'new', 'ok-name').status, 0);
});

test('every shipped template parses: tasks template covers a REQ id format', () => {
  const t = parseTasks(fs.readFileSync(path.join(__dirname, '..', 'templates', 'tasks.md'), 'utf8'));
  assert.ok(t.length >= 1 && t[0].covers.length === 1);
});

test('parseSpec: scenario references with a dash are not definitions; bold and colon forms are', () => {
  const s = parseSpec('- REQ-001: a\n- **REQ-002:** b\n- **REQ-003**: c\n- REQ-001 — Given x, when y, then z');
  assert.deepStrictEqual(s.reqs, ['REQ-001', 'REQ-002', 'REQ-003']);
});

test('verify: approving a spec that still has placeholders is an error', () => {
  const r = tmp(); sdd(r, 'init');
  feature(r, { spec: 'Status: approved\n- REQ-001: When …, the app shall …' });
  assert.ok(verifyFeature(r, 'f1').errors.some((e) => /placeholder/.test(e)));
});
