'use strict';
// Copy to .sdd/extensions/ui-login.js and adapt. Read credentials from env vars, never commit them.
async function login(page, baseURL) {
  await page.goto(`${baseURL}/login`);
  await page.fill('[name=email]', process.env.SDD_UI_USER || '');
  await page.fill('[name=password]', process.env.SDD_UI_PASS || '');
  await page.click('button[type=submit]');
  await page.waitForURL((u) => !u.pathname.includes('/login'));
}
module.exports = { login };
