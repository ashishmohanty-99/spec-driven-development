# Security Policy

## Reporting a vulnerability

Report privately through GitHub: **Security → Report a vulnerability** on this repository. Please do not open a public issue. Include the version, steps to reproduce, and impact.

## Scope

The `specpilot` package and the assets it installs. Strix is a separate project; report its issues at https://github.com/usestrix/strix.

## Handling credentials

This tool never needs your model API key and has no way to receive one. If a key was pasted into a chat, a spec, a commit or a CI log, revoke it at the provider first, then clean up.

The threat model, controls and their tests are described in [skills/spec-driven-development-by-ashish-mohanty/references/Security-Model.md](skills/spec-driven-development-by-ashish-mohanty/references/Security-Model.md).
