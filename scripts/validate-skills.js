#!/usr/bin/env node
'use strict';
// Lints skills/ and agents/: frontmatter contract and required sections.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const REQUIRED = ['## Overview', '## Common Rationalizations', '## Red Flags', '## Verification'];
let errors = 0;
const fail = (m) => { console.log(`  ERROR ${m}`); errors++; };

function front(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!m) return null;
  const o = {};
  for (const l of m[1].split('\n')) { const i = l.indexOf(':'); if (i > 0) o[l.slice(0, i).trim()] = l.slice(i + 1).trim(); }
  return o;
}

for (const d of fs.readdirSync(path.join(ROOT, 'skills')).sort()) {
  const f = path.join(ROOT, 'skills', d, 'SKILL.md');
  if (!fs.existsSync(f)) { fail(`${d}: SKILL.md missing`); continue; }
  const t = fs.readFileSync(f, 'utf8'); const fm = front(t);
  console.log(`skill ${d}`);
  if (!fm) { fail(`${d}: no frontmatter`); continue; }
  if (fm.name !== d) fail(`${d}: name "${fm.name}" must match directory`);
  if (!fm.description) fail(`${d}: description missing`);
  else {
    if (fm.description.length > 1024) fail(`${d}: description over 1024 chars`);
    if (!/\bUse (when|at|after|before|for|on|during|in)\b/i.test(fm.description)) fail(`${d}: description needs a "Use when…" trigger`);
  }
  for (const k of Object.keys(fm)) if (!['name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'].includes(k)) fail(`${d}: disallowed frontmatter key ${k}`);
  for (const s of REQUIRED) if (!t.includes(s)) fail(`${d}: missing section "${s}"`);
}
for (const d of ['agents', 'commands']) {
  for (const f of fs.readdirSync(path.join(ROOT, d)).filter((x) => x.endsWith('.md'))) {
    console.log(`${d.slice(0, -1)} ${f}`);
    const fm = front(fs.readFileSync(path.join(ROOT, d, f), 'utf8'));
    if (!fm || !fm.description) fail(`${d}/${f}: frontmatter description required`);
    if (d === 'agents' && fm && fm.name !== f.replace(/\.md$/, '')) fail(`${d}/${f}: name must match filename`);
  }
}
// Every skill referenced by a command or the router must exist.
const skills = new Set(fs.readdirSync(path.join(ROOT, 'skills')));
for (const d of ['commands', 'skills']) {
  const walkDir = (p) => fs.readdirSync(p, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walkDir(path.join(p, e.name)) : [path.join(p, e.name)]);
  for (const f of walkDir(path.join(ROOT, d)).filter((x) => x.endsWith('.md'))) {
    for (const m of fs.readFileSync(f, 'utf8').matchAll(/`([a-z][a-z-]+)` skill/g)) if (!skills.has(m[1])) fail(`${path.relative(ROOT, f)}: references unknown skill ${m[1]}`);
  }
}
console.log(errors ? `\n${errors} error(s)` : '\nAll skills valid');
process.exit(errors ? 1 : 0);
