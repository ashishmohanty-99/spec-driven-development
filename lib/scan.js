'use strict';
const path = require('path');
const { exists, readText, readJson, walk } = require('./util');

const LANGS = {
  '.js': 'JavaScript', '.jsx': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
  '.ts': 'TypeScript', '.tsx': 'TypeScript', '.py': 'Python', '.go': 'Go', '.rs': 'Rust',
  '.java': 'Java', '.kt': 'Kotlin', '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#', '.swift': 'Swift',
  '.scala': 'Scala', '.c': 'C', '.cpp': 'C++', '.sh': 'Shell',
};
const JS_FRAMEWORKS = ['react', 'next', 'vue', 'nuxt', 'svelte', '@angular/core', 'express', 'fastify', '@nestjs/core', 'koa', 'hono', 'vite', 'electron'];
const JS_TEST = ['vitest', 'jest', 'mocha', 'playwright', '@playwright/test', 'cypress', 'ava'];
const JS_QUALITY = ['eslint', 'prettier', 'typescript', 'biome', '@biomejs/biome'];
const PY_HINTS = { django: 'Django', fastapi: 'FastAPI', flask: 'Flask', pytest: 'pytest', ruff: 'ruff', mypy: 'mypy', black: 'black', sqlalchemy: 'SQLAlchemy' };
const SENSITIVE = /(^|\/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa.*|.*credentials.*\.json|.*secrets?\.(ya?ml|json))$/i;
const TEST_FILE = /(\.(test|spec)\.[jt]sx?$|(^|\/)test_[^/]+\.py$|_test\.(go|py)$|Test\.java$|(^|\/)tests?\/|(^|\/)__tests__\/)/;

function scan(root) {
  const files = walk(root);
  const has = (f) => files.includes(f) || exists(path.join(root, f));
  const p = {
    root: path.resolve(root), name: path.basename(path.resolve(root)), fileCount: files.length,
    languages: [], frameworks: [], testTools: [], qualityTools: [], packageManagers: [],
    commands: {}, ci: [], docs: [], topDirs: [], monorepo: null, testFileCount: 0,
    sensitiveFiles: [], existingSdd: has('.sdd/config.json'), agentFiles: [], notes: [],
  };

  // languages
  const counts = {};
  for (const f of files) { const l = LANGS[path.extname(f)]; if (l) counts[l] = (counts[l] || 0) + 1; }
  p.languages = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([name, files]) => ({ name, files }));

  // top-level dirs
  p.topDirs = [...new Set(files.filter((f) => f.includes('/')).map((f) => f.split('/')[0]))].sort();

  // JS/TS
  const pkg = readJson(path.join(root, 'package.json'));
  if (pkg) {
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    const pick = (list) => list.filter((d) => deps[d]);
    p.frameworks.push(...pick(JS_FRAMEWORKS));
    p.testTools.push(...pick(JS_TEST));
    p.qualityTools.push(...pick(JS_QUALITY));
    const pm = has('pnpm-lock.yaml') ? 'pnpm' : has('yarn.lock') ? 'yarn' : has('bun.lockb') || has('bun.lock') ? 'bun' : 'npm';
    p.packageManagers.push(pm);
    const run = pm === 'npm' ? 'npm run' : pm;
    const s = pkg.scripts || {};
    for (const k of ['dev', 'start', 'build', 'test', 'lint', 'typecheck', 'format']) {
      if (s[k]) p.commands[k] = k === 'test' && pm === 'npm' ? 'npm test' : `${run} ${k}`;
    }
    if (!p.commands.test && p.testTools.length === 0) p.notes.push('package.json has no test script and no known test tool.');
    if (pkg.workspaces) p.monorepo = 'npm/yarn workspaces';
  }
  if (has('pnpm-workspace.yaml')) p.monorepo = 'pnpm workspaces';
  for (const [f, n] of [['lerna.json', 'lerna'], ['nx.json', 'nx'], ['turbo.json', 'turborepo'], ['go.work', 'go workspace']]) if (has(f)) p.monorepo = n;

  // Python
  const py = [readText(path.join(root, 'pyproject.toml')), readText(path.join(root, 'requirements.txt')), readText(path.join(root, 'requirements-dev.txt'))].filter(Boolean).join('\n').toLowerCase();
  if (py || has('setup.py') || has('Pipfile')) {
    p.packageManagers.push(has('poetry.lock') ? 'poetry' : has('uv.lock') ? 'uv' : has('Pipfile') ? 'pipenv' : 'pip');
    for (const [k, v] of Object.entries(PY_HINTS)) if (py.includes(k)) (['pytest'].includes(k) ? p.testTools : ['ruff', 'mypy', 'black'].includes(k) ? p.qualityTools : p.frameworks).push(v);
    if (py.includes('pytest') && !p.commands.test) p.commands.test = 'pytest';
    if (py.includes('ruff') && !p.commands.lint) p.commands.lint = 'ruff check .';
  }
  // Other ecosystems
  if (has('go.mod')) { p.packageManagers.push('go modules'); p.commands.test ||= 'go test ./...'; p.commands.build ||= 'go build ./...'; p.commands.lint ||= 'go vet ./...'; }
  if (has('Cargo.toml')) { p.packageManagers.push('cargo'); p.commands.test ||= 'cargo test'; p.commands.build ||= 'cargo build'; p.commands.lint ||= 'cargo clippy'; }
  if (has('pom.xml')) { p.packageManagers.push('maven'); p.commands.test ||= 'mvn test'; p.commands.build ||= 'mvn package'; }
  if (has('build.gradle') || has('build.gradle.kts')) { p.packageManagers.push('gradle'); p.commands.test ||= has('gradlew') ? './gradlew test' : 'gradle test'; p.commands.build ||= has('gradlew') ? './gradlew build' : 'gradle build'; }
  if (has('Gemfile')) { p.packageManagers.push('bundler'); p.commands.test ||= 'bundle exec rspec'; }
  if (has('composer.json')) p.packageManagers.push('composer');
  if (files.some((f) => f.endsWith('.csproj') || f.endsWith('.sln'))) { p.packageManagers.push('dotnet'); p.commands.test ||= 'dotnet test'; p.commands.build ||= 'dotnet build'; }

  // Makefile targets
  const mk = readText(path.join(root, 'Makefile'));
  if (mk) {
    const targets = [...mk.matchAll(/^([a-zA-Z][\w-]*):/gm)].map((m) => m[1]);
    for (const t of ['test', 'build', 'lint', 'dev', 'check']) if (targets.includes(t)) p.commands[t] ||= `make ${t}`;
  }

  // CI
  if (files.some((f) => f.startsWith('.github/workflows/'))) p.ci.push('GitHub Actions');
  for (const [f, n] of [['.gitlab-ci.yml', 'GitLab CI'], ['Jenkinsfile', 'Jenkins'], ['azure-pipelines.yml', 'Azure Pipelines'], ['.circleci/config.yml', 'CircleCI'], ['bitbucket-pipelines.yml', 'Bitbucket Pipelines']]) if (has(f)) p.ci.push(n);

  // Docs and agent files
  for (const f of ['README.md', 'CONTRIBUTING.md', 'ARCHITECTURE.md', 'SECURITY.md', 'CHANGELOG.md']) if (has(f)) p.docs.push(f);
  if (files.some((f) => /^docs?\//.test(f))) p.docs.push('docs/');
  if (files.some((f) => /(^|\/)(adr|adrs|decisions)\//i.test(f))) p.docs.push('ADR directory');
  for (const f of ['AGENTS.md', 'CLAUDE.md', '.cursorrules', '.github/copilot-instructions.md', 'GEMINI.md']) if (has(f)) p.agentFiles.push(f);

  // Tests and sensitive
  p.testFileCount = files.filter((f) => TEST_FILE.test(f)).length;
  p.sensitiveFiles = files.filter((f) => SENSITIVE.test(f) && !/\.(example|sample|template)$/.test(f));

  // Dedupe
  for (const k of ['frameworks', 'testTools', 'qualityTools', 'packageManagers', 'ci', 'docs']) p[k] = [...new Set(p[k])];
  if (!p.testFileCount) p.notes.push('No test files detected: the VERIFY gate will need tests introduced as part of the first feature.');
  if (!p.ci.length) p.notes.push('No CI detected: gates run only locally until CI is added.');
  if (!p.agentFiles.length) p.notes.push('No agent instruction file found (AGENTS.md / CLAUDE.md).');
  return p;
}

function renderProfile(p) {
  const list = (a) => (a.length ? a.join(', ') : '_none detected_');
  const cmds = Object.keys(p.commands).length
    ? Object.entries(p.commands).map(([k, v]) => `| ${k} | \`${v}\` |`).join('\n')
    : '| _none detected_ | Confirm with the team and fill in |';
  return `# Codebase Profile — ${p.name}

> Generated by \`sdd scan\`. Facts below were detected from file names and manifests only.
> Items marked **CONFIRM** are inferences: a human must verify them before the constitution is ratified.
> Re-run \`sdd scan\` after structural changes; only the "Human-supplied context" section at the bottom is preserved across re-scans.

## Stack
- **Languages (by file count):** ${p.languages.length ? p.languages.map((l) => `${l.name} (${l.files})`).join(', ') : '_none detected_'}
- **Frameworks / libraries:** ${list(p.frameworks)}
- **Package managers:** ${list(p.packageManagers)}
- **Test tools:** ${list(p.testTools)}
- **Quality tools:** ${list(p.qualityTools)}
- **Monorepo:** ${p.monorepo || 'no'}
- **CI:** ${list(p.ci)}

## Commands (CONFIRM)
| Purpose | Command |
|---|---|
${cmds}

## Layout
- **Top-level directories:** ${list(p.topDirs)}
- **Files scanned:** ${p.fileCount}; **test files:** ${p.testFileCount}
- **Docs present:** ${list(p.docs)}
- **Agent instruction files:** ${list(p.agentFiles)}

## Protected paths (agents must not read or edit)
${p.sensitiveFiles.length ? p.sensitiveFiles.map((f) => `- \`${f}\``).join('\n') : '_No secret-like files detected._'}

## Observations
${p.notes.length ? p.notes.map((n) => `- ${n}`).join('\n') : '- None.'}

## Human-supplied context (preserved across re-scans)
<!-- Add: domain glossary, architectural invariants, ownership, things the scan cannot see. -->
`;
}

const HUMAN_HEADING = '## Human-supplied context (preserved across re-scans)';

/** Render a profile, carrying over any text a human wrote under the Human-supplied context heading. */
function renderProfileKeeping(p, previousMarkdown) {
  const fresh = renderProfile(p);
  if (!previousMarkdown) return fresh;
  const i = previousMarkdown.indexOf(HUMAN_HEADING);
  if (i < 0) return fresh;
  const kept = previousMarkdown.slice(i);
  return fresh.slice(0, fresh.indexOf(HUMAN_HEADING)) + kept;
}

module.exports = { scan, renderProfile, renderProfileKeeping };
