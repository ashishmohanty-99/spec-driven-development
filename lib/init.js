'use strict';
const fs = require('fs');
const path = require('path');
const { exists, readText, mkdirp, copyDir } = require('./util');
const { scan, renderProfileKeeping } = require('./scan');

const PKG = path.resolve(__dirname, '..');
const BEGIN = '<!-- SPECPILOT:BEGIN (managed block; edit outside it) -->';
const END = '<!-- SPECPILOT:END -->';

const AGENT_TARGETS = {
  claude: { skills: '.claude/skills', commands: '.claude/commands', agents: '.claude/agents', instr: 'CLAUDE.md' },
  generic: { skills: '.agents/skills', commands: null, agents: null, instr: 'AGENTS.md' },
};

function managedBlock(profile, target) {
  const cmd = profile.commands;
  const lines = Object.entries(cmd).map(([k, v]) => `- ${k}: \`${v}\``);
  return `${BEGIN}
## Spec-Driven Development (SpecPilot)
This repo uses gated SDD. Do not write feature code without an approved spec.

- Context: read \`.sdd/codebase-profile.md\` and \`.sdd/constitution.md\` before any SDD work.
- Lifecycle: discover → constitute → specify → clarify → plan → tasks → build → verify → ship.
- Each phase ends at a human gate. Never advance a phase in the same turn that produced its artifact.
- Artifacts live in \`.sdd/specs/<feature>/\` (spec.md, plan.md, tasks.md). Requirements are \`REQ-###\`, tasks \`T-###\`.
- Check state with \`npx specpilot status\`; check traceability with \`npx specpilot verify <feature>\`.
- Generate the Playwright regression suite for a feature from its spec: \`npx specpilot gen-tests <feature>\`. Fill in \`tests/support/ui-connector.js\` for your app's selectors; see docs/USER_GUIDE.md "UI connectors".
- Run the full regression sweep (unit + e2e + traceability gates): \`npx specpilot regression\`.
- Security: \`npx specpilot pentest --target <path-or-url>\` wraps Strix (https://github.com/usestrix/strix); requires Docker and an LLM key, see docs/USER_GUIDE.md "Penetration testing".
- Skills: \`${AGENT_TARGETS[target].skills}/\`. Start with \`using-sdd\`.
${lines.length ? '\nDetected commands (confirm in the profile):\n' + lines.join('\n') + '\n' : ''}${END}
`;
}

function upsertBlock(file, block) {
  const cur = readText(file);
  if (cur == null) { fs.writeFileSync(file, block); return 'created'; }
  const a = cur.indexOf(BEGIN), b = cur.indexOf(END);
  if (a >= 0 && b > a) { fs.writeFileSync(file, cur.slice(0, a) + block.trimEnd() + cur.slice(b + END.length)); return 'updated'; }
  fs.writeFileSync(file, cur.replace(/\s*$/, '\n\n') + block);
  return 'appended';
}

function writeProfile(root) {
  const profile = scan(root);
  const sdd = path.join(root, '.sdd');
  mkdirp(sdd);
  const mdPath = path.join(sdd, 'codebase-profile.md');
  fs.writeFileSync(mdPath, renderProfileKeeping(profile, readText(mdPath)));
  fs.writeFileSync(path.join(sdd, 'codebase-profile.json'), JSON.stringify(profile, null, 2) + '\n');
  return profile;
}

function init(root, { agent = 'claude', force = false } = {}) {
  const t = AGENT_TARGETS[agent];
  if (!t) throw new Error(`Unknown --agent "${agent}". Use: ${Object.keys(AGENT_TARGETS).join(', ')}`);
  const log = [];
  const profile = writeProfile(root);
  log.push(`profiled codebase (${profile.fileCount} files, ${profile.languages.map((l) => l.name).slice(0, 3).join('/') || 'no code detected'})`);

  const sdd = path.join(root, '.sdd');
  for (const d of ['specs', 'extensions', 'adr']) mkdirp(path.join(sdd, d));
  const cfgPath = path.join(sdd, 'config.json');
  if (!exists(cfgPath)) {
    fs.writeFileSync(cfgPath, JSON.stringify({ version: 1, agent, specsDir: '.sdd/specs', strict: false, requireTestsPerRequirement: true, e2eDir: 'tests/e2e' }, null, 2) + '\n');
    log.push('wrote .sdd/config.json');
  }
  const consPath = path.join(sdd, 'constitution.md');
  if (force || !exists(consPath)) {
    fs.writeFileSync(consPath, readText(path.join(PKG, 'templates', 'constitution.md')).replace('{{PROJECT}}', profile.name));
    log.push('wrote draft .sdd/constitution.md (needs human ratification)');
  }
  copyDir(path.join(PKG, 'templates'), path.join(sdd, 'templates'), { force });
  fs.writeFileSync(path.join(sdd, 'extensions', 'README.md'), readText(path.join(PKG, 'templates', 'extensions-README.md')));

  const uiRoot = path.join(PKG, 'ui');
  if (force || !exists(path.join(root, 'playwright.config.js'))) { fs.copyFileSync(path.join(uiRoot, 'playwright.config.js'), path.join(root, 'playwright.config.js')); log.push('wrote playwright.config.js (regression suite config)'); }
  const uiConnDest = path.join(root, 'tests', 'support', 'ui-connector.js');
  if (force || !exists(uiConnDest)) { mkdirp(path.dirname(uiConnDest)); fs.copyFileSync(path.join(uiRoot, 'tests', 'support', 'ui-connector.js'), uiConnDest); log.push('wrote tests/support/ui-connector.js (fill in your selectors)'); }
  fs.copyFileSync(path.join(uiRoot, 'ui-login.example.js'), path.join(sdd, 'extensions', 'ui-login.example.js'));

  const w = copyDir(path.join(PKG, 'skills'), path.join(root, t.skills), { force });
  log.push(`installed skills → ${t.skills} (${w.length} files written)`);
  if (t.commands) { copyDir(path.join(PKG, 'commands'), path.join(root, t.commands), { force }); log.push(`installed commands → ${t.commands}`); }
  if (t.agents) { copyDir(path.join(PKG, 'agents'), path.join(root, t.agents), { force }); log.push(`installed subagents → ${t.agents}`); }
  log.push(`${upsertBlock(path.join(root, t.instr), managedBlock(profile, agent))} ${t.instr} managed block`);
  if (agent === 'claude' && !exists(path.join(root, 'AGENTS.md'))) { /* CLAUDE.md is enough for Claude Code */ }
  return { log, profile };
}

module.exports = { init, writeProfile, upsertBlock, managedBlock, BEGIN, END };
