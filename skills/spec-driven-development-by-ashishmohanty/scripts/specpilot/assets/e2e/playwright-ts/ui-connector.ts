/**
 * UI connector: the single place where spec language meets your application's UI.
 *
 * Generated tests (<feature>.spec.ts) never contain selectors. They hand each Given / When / Then
 * phrase from spec.md to this module, which finds a matching step and runs it with Playwright.
 *
 * Add your own steps at the bottom:
 *
 *   step(/the cart shows (?<count>\d+) items?/i, async (page, { count }) => {
 *     await expect(page.getByTestId('cart-count')).toHaveText(count);
 *   });
 *
 * Security: never hard-code credentials (read process.env), and point SDD_BASE_URL only at
 * environments you are allowed to test.
 */
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

export const BASE_URL = (process.env.SDD_BASE_URL || 'http://localhost:3000').replace(/\/+$/, '');
const STRICT = process.env.SDD_E2E_STRICT === '1';

type StepFn = (page: Page, groups: Record<string, string>) => Promise<void>;
const steps: Array<[RegExp, StepFn]> = [];

export function step(pattern: RegExp, fn: StepFn): void {
  steps.push([pattern, fn]);
}

/** A gap in coverage: skipped locally so you can see it, failed under SDD_E2E_STRICT=1 (CI). */
export function missing(reason: string): void {
  if (STRICT) throw new Error(reason);
  test.skip(true, reason);
}

/** Split "do X and they do Y" into steps, ignoring any "and" inside double quotes. */
export function splitActions(text: string): string[] {
  const parts: string[] = [];
  const and = /\s+and\s+(?=(?:the|a|an|they|user|I)\b)/gi;
  let start = 0;
  let match: RegExpExecArray | null;
  while ((match = and.exec(text)) !== null) {
    const quotes = (text.slice(0, match.index).match(/"/g) || []).length;
    if (quotes % 2 === 0) {
      parts.push(text.slice(start, match.index));
      start = match.index + match[0].length;
    }
  }
  parts.push(text.slice(start));
  return parts.map((p) => p.trim()).filter(Boolean);
}

export async function runStep(page: Page, phrase: string): Promise<void> {
  const text = phrase.trim().replace(/\.$/, '');
  for (const part of splitActions(text)) {
    const found = steps.find(([pattern]) => {
      const m = part.match(pattern);
      return m !== null && m[0] === part;
    });
    if (!found) {
      missing(`no UI step matches: "${part}" (add one with step() in ui-connector.ts)`);
      return;
    }
    await found[1](page, part.match(found[0])!.groups || {});
  }
}

export async function runScenario(page: Page, s: { given: string; when: string; then: string }): Promise<void> {
  if (!/^https?:\/\/[^/]+/.test(BASE_URL)) throw new Error(`SDD_BASE_URL must be an http(s) URL, got: ${BASE_URL}`);
  for (const phrase of [s.given, s.when, s.then]) await runStep(page, phrase);
}

// ── Built-in steps: scenarios phrased this way run with no extra code ───────────────────────

step(/(?:the |a )?(?:user|visitor|they|I) (?:opens?|visits?|is on|am on|are on) (?:the page )?(?<path>\/\S*)/i,
  async (page, { path }) => { await page.goto(BASE_URL + path); });

step(/(?:the |a )?(?:user|they|I) (?:is|am|are) (?:logged|signed) in(?: as (?<role>[\w-]+))?/i,
  async (page, { role }) => {
    // Project login flow: export `login(page, baseUrl, role)` from ./ui-login.ts next to this file.
    let login: undefined | ((p: Page, base: string, role?: string) => Promise<void>);
    try { login = (await import('./ui-login')).login; } catch { login = undefined; }
    if (!login) { missing('scenario needs a logged-in user: create ui-login.ts exporting login()'); return; }
    await login(page, BASE_URL, role);
  });

step(/(?:the user |they |I )?clicks? "(?<name>[^"]+)"/i,
  async (page, { name }) => {
    await page.getByRole('button', { name }).or(page.getByRole('link', { name })).first().click();
  });

step(/(?:the user |they |I )?(?:fills?|enters?|types?) "(?<value>[^"]*)" (?:in|into) "(?<label>[^"]+)"/i,
  async (page, { value, label }) => { await page.getByLabel(label).fill(value); });

step(/(?:the page|the user|they|I) (?:shows?|sees?|displays?) "(?<text>[^"]+)"/i,
  async (page, { text }) => { await expect(page.getByText(text).first()).toBeVisible(); });

step(/(?:the page|the user|they|I) (?:does not|do not|doesn't|don't) (?:show|see|display) "(?<text>[^"]+)"/i,
  async (page, { text }) => { await expect(page.getByText(text)).toHaveCount(0); });

step(/the (?:url|address) (?:is|becomes|contains) (?<path>\/\S*)/i,
  async (page, { path }) => { await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))); });

// ── Project steps: add yours below ──────────────────────────────────────────────────────────
