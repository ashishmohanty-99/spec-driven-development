# SpecPilot extensions

Put organisation- or team-specific behaviour here so core SpecPilot files stay unmodified and
can be upgraded safely. Nothing in this folder is overwritten by `sdd init`.

Supported extension points (all optional):

| File | Purpose | Read by |
|---|---|---|
| `rules.md` | Extra constraints appended to the constitution check (compliance, naming, tenancy) | plan, verify skills |
| `templates/spec.md` etc. | Override a core template; `sdd new` prefers `.sdd/templates/` | `sdd new` |
| `gates.md` | Extra human or tool gates, e.g. "security review ticket linked before SHIP" | ship skill |
| `tools.md` | How the agent should call your internal tooling (trackers, scanners, deploy) as command + expected output | build, verify, ship skills |
| `glossary.md` | Domain terms and their definitions | specify, clarify skills |

Keep secrets, hostnames and proprietary code out of these files if they are committed to a shared
repository. Reference them by name ("the internal scanner `scan-cli`") and keep credentials in your
secret manager. See docs/EXTENDING.md.
