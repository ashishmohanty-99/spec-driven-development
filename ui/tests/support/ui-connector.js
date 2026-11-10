'use strict';
// UI connector: the one place generated Playwright tests go through to reach your app, so the
// generator doesn't need to know your login flow, selectors or routing. Fill in the three
// functions for your UI; generated tests call them with the plain-English Given/When/Then text
// from spec.md so you can see what each line was trying to do while you write the real selector.
//
// Override per-project without touching this file: if `.sdd/extensions/ui-login.js` exports an
// async `login(page, baseURL)`, `ui()` calls it before each scenario that mentions "logged in"
// or "authenticated". Keep real credentials out of this file and out of git — read them from
// environment variables (see docs/USER_GUIDE.md "UI connectors").

const path = require('path');
const BASE_URL = process.env.SDD_BASE_URL || 'http://localhost:3000';

function loadProjectLogin() {
  try { return require(path.resolve(process.cwd(), '.sdd/extensions/ui-login.js')); } catch { return null; }
}

/** Given: put the page into the starting state the scenario describes. */
async function ui(page, givenText) {
  if (!page.url() || page.url() === 'about:blank') await page.goto(BASE_URL);
  if (/logged in|authenticated|signed in/i.test(givenText)) {
    const project = loadProjectLogin();
    if (project && project.login) await project.login(page, BASE_URL);
    else test_fixme_login();
  }
}

function test_fixme_login() {
  // No .sdd/extensions/ui-login.js login() found. Add one, or edit the generated test directly —
  // see docs/USER_GUIDE.md "UI connectors".
}

/** When: perform the action. Replace with real locators; this default is a no-op placeholder. */
async function act(_page, _whenText) { /* fill in per scenario */ }

/** Then: assert the outcome. Replace with a real Playwright expect(); default just documents intent. */
async function expectFn(_page, _thenText) { /* fill in per scenario */ }

module.exports = { ui, act, expect: expectFn, BASE_URL };
