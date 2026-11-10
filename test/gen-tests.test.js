'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { genTests } = require('../lib/gen-tests');
const { parseScenarios } = require('../lib/spec');

const CLI = path.join(__dirname, '..', 'bin', 'sdd.js');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sdd-gt-'));
const sddInit = (root) => execFileSync('node', [CLI, 'init', '--dir', root]);
const writeSpec = (root, feature, content) => {
  const dir = path.join(root, '.sdd', 'specs', feature);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'spec.md'), content);
};

test('parseScenarios reads Given/When/Then and tolerates a scenario with no breakdown', () => {
  const s = parseScenarios('- REQ-001 — Given a, when b, then c\n- REQ-002 — something unparsed');
  assert.deepStrictEqual(s[0], { req: 'REQ-001', given: 'a', when: 'b', then: 'c', raw: 'Given a, when b, then c' });
  assert.strictEqual(s[1].given, null);
  assert.strictEqual(s[1].raw, 'something unparsed');
});

test('genTests fails clearly without a spec or without requirements', () => {
  const r = tmp(); sddInit(r);
  assert.throws(() => genTests(r, 'missing'), /No spec\.md/);
  writeSpec(r, 'empty', 'Status: draft\nNo requirements here.');
  assert.throws(() => genTests(r, 'empty'), /no REQ- requirements/);
});

test('genTests produces one test per scenario, a fixme for uncovered requirements, and valid JS', () => {
  const r = tmp(); sddInit(r);
  writeSpec(r, 'f1', [
    'Status: approved',
    '- REQ-001: a',
    '- REQ-002: b',
    '## Acceptance scenarios',
    '- REQ-001 — Given x, when y, then z',
  ].join('\n'));
  const { file, created } = genTests(r, 'f1');
  assert.ok(created);
  const content = fs.readFileSync(file, 'utf8');
  assert.match(content, /test\("REQ-001: Given x, when y, then z"/);
  assert.match(content, /test\.fixme\(true, "REQ-002: acceptance scenario not yet specified"\)/);
  assert.doesNotThrow(() => execFileSync('node', ['--check', file]));
});

test('genTests regeneration preserves hand-written lines after the generated block, refreshes the rest', () => {
  const r = tmp(); sddInit(r);
  writeSpec(r, 'f1', 'Status: approved\n- REQ-001: a\n## Acceptance scenarios\n- REQ-001 — Given x, when y, then z');
  const { file } = genTests(r, 'f1');
  fs.appendFileSync(file, "\ntest('hand-written extra', () => {});\n");
  writeSpec(r, 'f1', 'Status: approved\n- REQ-001: a\n- REQ-002: new\n## Acceptance scenarios\n- REQ-001 — Given x, when y, then z');
  const { created } = genTests(r, 'f1');
  const content = fs.readFileSync(file, 'utf8');
  assert.strictEqual(created, false);
  assert.match(content, /hand-written extra/);
  assert.match(content, /REQ-002/);
});

test('CLI gen-tests writes a file consumed by verify as the requirement\'s test', () => {
  const r = tmp(); sddInit(r);
  writeSpec(r, 'f1', 'Status: approved\n- REQ-001: a\n## Acceptance scenarios\n- REQ-001 — Given x, when y, then z');
  execFileSync('node', [CLI, 'gen-tests', 'f1', '--dir', r]);
  const out = execFileSync('node', [CLI, 'verify', 'f1', '--dir', r], { encoding: 'utf8' });
  assert.match(out, /REQ with tests 1/); // the generated spec file already names REQ-001
  // Add a plan and mark the task done too, so --strict (which requires a task, not just a mention) is also clean.
  fs.writeFileSync(path.join(r, '.sdd/specs/f1/plan.md'), '# plan');
  fs.writeFileSync(path.join(r, '.sdd/specs/f1/tasks.md'), '- [x] T-001 x (covers: REQ-001)');
  const out2 = execFileSync('node', [CLI, 'verify', 'f1', '--strict', '--dir', r], { encoding: 'utf8' });
  assert.doesNotMatch(out2, /ERROR/);
});
