#!/usr/bin/env node
'use strict';
const path = require('path');
const fs = require('fs');
const { init, writeProfile } = require('../lib/init');
const { listFeatures, newFeature, verifyFeature, phaseOf } = require('../lib/spec');
const { genTests } = require('../lib/gen-tests');
const { regression } = require('../lib/regression');
const { pentest, INSTALL_HINT } = require('../lib/pentest');
const { exists } = require('../lib/util');
const pkg = require('../package.json');

const HELP = `specpilot ${pkg.version} — codebase-aware Spec-Driven Development

Usage: sdd <command> [options]

  init [--agent claude|generic] [--force]   Profile this repo and install skills, commands, templates
  scan                                      Re-profile the codebase (.sdd/codebase-profile.md)
  new <feature-name>                        Create .sdd/specs/<feature-name>/spec.md from the template
  status                                    Show each feature's phase and progress
  verify [feature] [--strict]               Gate check: REQ → task → test traceability, open questions
  gen-tests <feature>                       Generate/refresh a Playwright e2e spec from spec.md
  regression [--strict] [--pentest <target>]  Run unit tests + e2e suite + all gates (CI entry point)
  pentest --target <path|url> [--fail-on <level>] [--instruction <text>]
                                             Run a Strix security scan (https://github.com/usestrix/strix)
  doctor                                    Check installation health
  help | version

Run from the repository root. Options: --dir <path> to target another directory.`;

function parse(argv) {
  const a = { _: [], flags: {} };
  for (let i = 0; i < argv.length; i++) {
    const x = argv[i];
    if (x.startsWith('--')) {
      const k = x.slice(2);
      if (['agent', 'dir', 'target', 'fail-on', 'instruction', 'diff-base', 'pentest', 'scan-mode'].includes(k)) {
        (a.flags[k] = a.flags[k] || []).push(argv[++i]);
      } else a.flags[k] = true;
    } else a._.push(x);
  }
  for (const k of Object.keys(a.flags)) if (Array.isArray(a.flags[k]) && a.flags[k].length === 1 && k !== 'target') a.flags[k] = a.flags[k][0];
  return a;
}

function main(argv) {
  const { _: [cmd, ...rest], flags } = parse(argv);
  const root = path.resolve(flags.dir || process.cwd());
  const out = (s = '') => console.log(s);
  switch (cmd) {
    case undefined: case 'help': case '-h': out(HELP); return 0;
    case 'version': case '-v': out(pkg.version); return 0;
    case 'init': {
      const { log, profile } = init(root, { agent: flags.agent || 'claude', force: !!flags.force });
      out('SpecPilot initialised:'); log.forEach((l) => out(`  ✓ ${l}`));
      if (profile.notes.length) { out('\nObservations:'); profile.notes.forEach((n) => out(`  • ${n}`)); }
      out('\nNext steps:\n  1. Review .sdd/codebase-profile.md and fix anything marked CONFIRM\n  2. In your agent run /sdd-constitution to ratify .sdd/constitution.md\n  3. Start a feature: /sdd-spec <idea>   (or: npx specpilot new <feature-name>)\nFull guide: docs/USER_GUIDE.md');
      return 0;
    }
    case 'scan': { const p = writeProfile(root); out(`Profile updated: ${p.languages.map((l) => l.name).join(', ') || 'no code detected'} — .sdd/codebase-profile.md`); return 0; }
    case 'new': {
      if (!rest[0]) { out('Usage: sdd new <feature-name>'); return 2; }
      const dir = newFeature(root, rest[0]); out(`Created ${path.relative(root, dir)}/spec.md — now run /sdd-spec ${rest[0]} in your agent.`); return 0;
    }
    case 'status': {
      const fs_ = listFeatures(root);
      if (!exists(path.join(root, '.sdd'))) { out('Not initialised. Run: npx specpilot init'); return 1; }
      if (!fs_.length) { out('No features yet. Start one: npx specpilot new <feature-name>'); return 0; }
      for (const f of fs_) { const { stats, errors } = verifyFeature(root, f); out(`${f.padEnd(28)} ${phaseOf(stats).padEnd(34)} REQ ${stats.requirements ?? 0}  tasks ${stats.tasksDone ?? 0}/${stats.tasks ?? 0}  ${errors.length ? errors.length + ' gate issue(s)' : 'gates ok'}`); }
      return 0;
    }
    case 'verify': {
      const targets = rest[0] ? [rest[0]] : listFeatures(root);
      if (!targets.length) { out('No features to verify.'); return 0; }
      let bad = 0;
      for (const f of targets) {
        const r = verifyFeature(root, f, { strict: !!flags.strict });
        out(`\n${r.errors.length ? '✗' : '✓'} ${f}  (REQ ${r.stats.requirements ?? 0}, tasks ${r.stats.tasksDone ?? 0}/${r.stats.tasks ?? 0}, REQ with tests ${r.stats.reqsWithTests ?? 0})`);
        r.errors.forEach((e) => out(`   ERROR  ${e}`)); r.warnings.forEach((w) => out(`   warn   ${w}`));
        bad += r.errors.length;
      }
      return bad ? 1 : 0;
    }
    case 'gen-tests': {
      if (!rest[0]) { out('Usage: sdd gen-tests <feature-name>'); return 2; }
      const { file, created } = genTests(root, rest[0]);
      out(`${created ? 'Created' : 'Updated'} ${path.relative(root, file)}`);
      out('First time: npm i -D @playwright/test && npx playwright install chromium');
      out('Then fill in tests/support/ui-connector.js (or .sdd/extensions/ui-login.js for auth) with real selectors, and run: npx playwright test');
      return 0;
    }
    case 'regression': {
      const target = flags.pentest || null;
      const r = regression(root, { strict: !!flags.strict, pentestTarget: Array.isArray(target) ? target[0] : target });
      out('\nRegression summary:');
      for (const res of r.results) out(`  ${res.skipped ? '·' : res.status === 0 ? '✓' : '✗'} ${res.label}${res.note ? `  (${res.note})` : ''}`);
      return r.ok ? 0 : 1;
    }
    case 'pentest': {
      const target = flags.target;
      if (!target) { out('Usage: sdd pentest --target <path|url> [--target <another>] [--fail-on low|medium|high|critical] [--instruction "..."]'); return 2; }
      const p = pentest({ target, failOn: flags['fail-on'], instruction: flags.instruction, diffBase: flags['diff-base'], scanMode: flags['scan-mode'] });
      if (!p.ran) { out(p.reason || INSTALL_HINT); return 0; }
      return p.status ?? 1;
    }
    case 'doctor': {
      const checks = [
        ['.sdd/config.json', exists(path.join(root, '.sdd/config.json'))],
        ['.sdd/codebase-profile.md', exists(path.join(root, '.sdd/codebase-profile.md'))],
        ['.sdd/constitution.md', exists(path.join(root, '.sdd/constitution.md'))],
        ['skills installed', exists(path.join(root, '.claude/skills/using-sdd/SKILL.md')) || exists(path.join(root, '.agents/skills/using-sdd/SKILL.md'))],
      ];
      checks.forEach(([n, ok]) => out(`${ok ? '✓' : '✗'} ${n}`));
      const cons = exists(path.join(root, '.sdd/constitution.md')) && fs.readFileSync(path.join(root, '.sdd/constitution.md'), 'utf8');
      if (cons && /Status:\s*draft/i.test(cons)) out('⚠ constitution is still a draft — run /sdd-constitution and have a human ratify it');
      return checks.every(([, ok]) => ok) ? 0 : 1;
    }
    default: out(`Unknown command: ${cmd}\n`); out(HELP); return 2;
  }
}

try { process.exitCode = main(process.argv.slice(2)); } catch (e) { console.error(`sdd: ${e.message}`); process.exitCode = 1; }
