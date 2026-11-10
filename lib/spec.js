'use strict';
const fs = require('fs');
const path = require('path');
const { exists, readText, readJson, mkdirp, walk } = require('./util');

// A definition is `REQ-001:` (optionally bold). Scenario lines use `REQ-001 —` and are references only.
const REQ_DEF = /^\s*(?:[-*]|\d+\.)\s+\**(REQ-[A-Z0-9]+(?:-\d+)?)(?:\*\*)?:/;
const REQ_REF = /\bREQ-[A-Z0-9]+(?:-\d+)?\b/g;
const TASK_LINE = /^\s*[-*]\s+\[([ xX])\]\s+\**(T-\d+)\**[\s:.)-]+(.*)$/;
const TEST_FILE = /(\.(test|spec)\.[jt]sx?$|(^|\/)test_[^/]+\.py$|_test\.(go|py)$|Test\.java$|(^|\/)tests?\/|(^|\/)__tests__\/|_spec\.rb$)/;

function config(root) { return readJson(path.join(root, '.sdd', 'config.json')) || {}; }
function specsDir(root) { return path.join(root, config(root).specsDir || '.sdd/specs'); }

function listFeatures(root) {
  const d = specsDir(root);
  if (!exists(d)) return [];
  return fs.readdirSync(d, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name).sort();
}

function newFeature(root, name) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) throw new Error('Feature name must be kebab-case (a-z, 0-9, hyphens).');
  const dir = path.join(specsDir(root), name);
  if (exists(dir)) throw new Error(`Feature "${name}" already exists at ${dir}`);
  mkdirp(dir);
  const tpl = path.join(root, '.sdd', 'templates');
  const pkgTpl = path.join(__dirname, '..', 'templates');
  const src = (f) => readText(path.join(tpl, f)) ?? readText(path.join(pkgTpl, f));
  fs.writeFileSync(path.join(dir, 'spec.md'), src('spec.md').replace(/\{\{FEATURE\}\}/g, name));
  return dir;
}

function stripCode(text) { return text.replace(/```[\s\S]*?```/g, '').replace(/<!--[\s\S]*?-->/g, ''); }

function parseSpec(text) {
  const clean = stripCode(text);
  const reqs = [];
  const placeholders = [];
  for (const line of clean.split('\n')) {
    const m = line.match(REQ_DEF);
    if (m) { reqs.push(m[1]); if (/…|<[^>]+>|\bTBD\b/.test(line)) placeholders.push(m[1]); }
  }
  const open = (clean.match(/\[NEEDS CLARIFICATION[^\]]*\]/g) || []);
  const approved = /^\s*(?:\*\*)?Status(?:\*\*)?\s*:\s*(?:\*\*)?approved/im.test(clean);
  return { reqs, open, approved, placeholders };
}

function parseTasks(text) {
  const clean = stripCode(text);
  const tasks = [];
  for (const line of clean.split('\n')) {
    const m = line.match(TASK_LINE);
    if (!m) continue;
    const covers = (m[3].match(REQ_REF) || []);
    tasks.push({ id: m[2], done: m[1].toLowerCase() === 'x', covers, text: m[3].trim() });
  }
  return tasks;
}

function testRefs(root) {
  const map = {};
  for (const f of walk(root).filter((f) => TEST_FILE.test(f) && !f.startsWith('.sdd/'))) {
    const t = readText(path.join(root, f));
    if (!t) continue;
    for (const id of new Set(t.match(REQ_REF) || [])) (map[id] ||= []).push(f);
  }
  return map;
}

/** Mechanical gate checks for one feature. Returns {errors, warnings, stats}. */
function verifyFeature(root, name, opts = {}) {
  const dir = path.join(specsDir(root), name);
  const errors = [], warnings = [];
  const specText = readText(path.join(dir, 'spec.md'));
  if (specText == null) return { errors: [`spec.md missing for "${name}"`], warnings, stats: {} };
  const spec = parseSpec(specText);
  const planText = readText(path.join(dir, 'plan.md'));
  const tasksText = readText(path.join(dir, 'tasks.md'));
  const tasks = tasksText ? parseTasks(tasksText) : [];
  const strict = !!(opts.strict || config(root).strict);

  if (!spec.reqs.length) errors.push('spec.md defines no requirements (expected lines like "- REQ-001: When …, the system shall …")');
  if (spec.placeholders.length) (spec.approved || planText || tasksText ? errors : warnings).push(`placeholder text left in ${spec.placeholders.join(', ')} (replace "…", <…> or TBD with real wording)`);
  const dupes = spec.reqs.filter((r, i) => spec.reqs.indexOf(r) !== i);
  for (const d of new Set(dupes)) errors.push(`duplicate requirement id ${d}`);
  if (spec.open.length) (planText || tasksText ? errors : warnings).push(`${spec.open.length} unresolved [NEEDS CLARIFICATION] marker(s) in spec.md`);
  if ((planText || tasksText) && !spec.approved) errors.push('plan/tasks exist but spec.md is not "Status: approved" (gate skipped)');
  if (tasksText && !planText) errors.push('tasks.md exists without plan.md (gate skipped)');

  const known = new Set(spec.reqs);
  const covered = new Set();
  for (const t of tasks) {
    if (!t.covers.length) errors.push(`${t.id} references no requirement (orphan task; add "covers: REQ-…")`);
    for (const r of t.covers) { if (!known.has(r)) errors.push(`${t.id} references unknown ${r}`); else covered.add(r); }
  }
  if (tasksText) { for (const r of spec.reqs) if (!covered.has(r)) errors.push(`${r} is not covered by any task`); }
  else if (planText) warnings.push('plan.md exists but tasks.md does not yet');

  const refs = testRefs(root);
  const wantTests = config(root).requireTestsPerRequirement !== false;
  const doneCovers = new Set(tasks.filter((t) => t.done).flatMap((t) => t.covers));
  for (const r of spec.reqs) {
    if (wantTests && doneCovers.has(r) && !refs[r]) (strict ? errors : warnings).push(`${r} has completed task(s) but no test file mentions it (name or tag tests with the id)`);
  }
  const stats = {
    requirements: spec.reqs.length, tasks: tasks.length, tasksDone: tasks.filter((t) => t.done).length,
    reqsWithTests: spec.reqs.filter((r) => refs[r]).length, approved: spec.approved, hasPlan: !!planText, hasTasks: !!tasksText,
  };
  return { errors, warnings, stats };
}

function phaseOf(stats) {
  if (!stats.requirements && !stats.approved) return 'SPECIFY (draft)';
  if (!stats.approved) return 'CLARIFY / awaiting spec approval';
  if (!stats.hasPlan) return 'PLAN';
  if (!stats.hasTasks) return 'TASKS';
  if (stats.tasks && stats.tasksDone < stats.tasks) return 'BUILD';
  return 'VERIFY / SHIP';
}

module.exports = { listFeatures, newFeature, verifyFeature, phaseOf, parseSpec, parseTasks, specsDir, config };

// ── Acceptance scenarios (section 6) and Playwright generation support ────

const SCENARIO_LINE = /^\s*[-*]\s+\**(REQ-[A-Z0-9]+(?:-\d+)?)\**\s*[—-]\s*(.+)$/;

/** Parse "- REQ-001 — Given X, when Y, then Z" lines from a spec's acceptance-scenarios section. */
function parseScenarios(text) {
  const clean = stripCode(text);
  const scenarios = [];
  for (const line of clean.split('\n')) {
    const m = line.match(SCENARIO_LINE);
    if (!m) continue;
    const body = m[2].trim();
    const g = body.match(/^Given\s+(.+?),\s*when\s+(.+?),\s*then\s+(.+)$/i);
    scenarios.push(g
      ? { req: m[1], given: g[1].trim(), when: g[2].trim(), then: g[3].trim(), raw: body }
      : { req: m[1], given: null, when: null, then: null, raw: body });
  }
  return scenarios;
}

module.exports.parseScenarios = parseScenarios;
