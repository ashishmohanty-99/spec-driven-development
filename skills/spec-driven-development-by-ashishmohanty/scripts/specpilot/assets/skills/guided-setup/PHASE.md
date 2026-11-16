---
name: guided-setup
description: Walks a person through setting up spec-driven development in a repository - explains in plain language what was detected, asks only the questions the tool could not answer, and lets them keep or switch off each lifecycle check with its consequence stated. Use after `sdd init`, when `sdd questions` lists open questions, when someone asks to change which checks are on, or when a new teammate asks how this repository is set up.
---

# Guided Setup

## Overview
Setup should feel like a short conversation, not a form. The tool has already read the repository; your job is to say what it found, ask only what it could not know, and record the answers. Every question has a safe default, so a person can say "use the defaults" and be done.

## Process
1. **Say what was found, in three or four plain lines.** Read `.sdd/codebase-profile.md`. For example: "This is a TypeScript and React project using pnpm, with Vitest tests and GitHub Actions. I'll generate acceptance tests as Playwright TypeScript." No jargon, no file dumps.
2. **Get the open questions.** Run `sdd questions --json`.
3. **Ask them one at a time**, in the order given. For each: the question, one line on why it matters, the options with the recommended one first. Use your question tool if you have one; otherwise ask in chat and wait. Never answer for the person.
4. **Record each answer immediately:** `sdd answer <id> "<value>"`. If it is refused, show the reason and ask again.
5. **The lifecycle question is the person's choice, not yours.** Show the checks as a short list with what each one protects. Recommend keeping all of them. If they want one off:
   - State the consequence in the tool's own words (`sdd lifecycle` prints it).
   - Ask for a one-line reason a teammate could read in six months.
   - Run `sdd lifecycle skip <check> --reason "<their reason>"` and show the warning it prints.
   - If they keep everything: `sdd answer lifecycle all`.
6. **Empty repository?** If the profile shows no code, load `project-scaffold` next.
7. **Close with one screen:** what is set up, which checks are on or off, and the single next action from `sdd next`.

## Changing your mind later
- See the checks: `sdd lifecycle`
- Switch one back on: `sdd lifecycle enable <check>`
- Switch one off: `sdd lifecycle skip <check> --reason "..."`

Writing an approved spec before code is the one step that cannot be switched off; it is what the whole method is.

## Rules
- Never switch a check off on your own, and never suggest it to save time. Only a person decides, after hearing the consequence.
- Never ask for passwords, tokens or API keys. No setup question needs one.
- One question per message. Short. Recommended option first.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "I'll pick sensible answers to save them time" | Wrong test command or wrong test form costs more than five questions. Ask. |
| "This check will slow them down, I'll turn it off" | That is their decision, with the consequence in front of them. |
| "Ask everything in one message" | Walls of questions get skimmed and half-answered. |

## Red Flags
- A check switched off with no recorded reason
- Answers recorded that the person never gave
- A setup summary that hides which checks are off

## Verification
- [ ] `sdd questions` reports nothing left to ask
- [ ] Every switched-off check has the person's reason in `.sdd/config.json`
- [ ] The person saw the next action from `sdd next`
