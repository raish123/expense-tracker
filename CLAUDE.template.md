# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!--
HOW TO USE THIS TEMPLATE
- Replace every <placeholder>. Delete sections that don't apply to your project.
- Keep only facts that are TRUE and NON-OBVIOUS for this repo. Delete generic advice.
- A good CLAUDE.md is short. If a line could apply to any project, it probably doesn't belong here.
- Mark genuinely-unknown items with: <!-- STUB: ... --> so they read as TODOs, not facts.
-->

## Project overview

<one or two sentences: what the app does, the core stack — `<language>`, `<framework>`, `<database>`, `<frontend approach>`>. <Any project-wide convention, e.g. currency/locale/units, that affects most code.>

<Optional: note the project's maturity — e.g. "early-stage; many routes are stubs awaiting Step N" — so Claude doesn't treat scaffolding as bugs.>

---

## Architecture
```
<project-root>/
├── <entry-point>            # <role, e.g. app/server entry, all routes>
├── <data-layer-dir>/        # <DB access / models / repositories>
├── <view-or-template-dir>/  # <UI / templates / components>
├── <static-or-assets-dir>/  # <css / js / images>
├── <tests-dir>/             # <test suite>
└── <dependency-manifest>    # <requirements.txt / package.json / etc.>
```

**Where things belong:**
- New <routes/endpoints> → `<file or layer>`
- <Data/DB logic> → `<file or layer>`, never inline in <routes>
- New <pages/components> → `<location + pattern, e.g. extend base layout>`
- <Styles/assets> → `<location + rule, e.g. no inline styles>`

---

## Code style

- <Language> conventions: <style guide + naming, e.g. PEP 8 / snake_case, or ESLint/Prettier + camelCase>
- <Framework-specific route/handler pattern — the exact signature shape Claude should copy>
- <Templating/markup rule — e.g. always use the framework's URL helper, never hardcode URLs>
- <Data-access rule — e.g. always parameterized queries; never string-built SQL>
- <Error-handling pattern — the idiomatic mechanism for this framework>

---

## Tech constraints

<!-- The most valuable section: hard "do NOT use X" rules prevent Claude drifting to defaults from its training data. -->
- **<Framework> only** — no <competing frameworks to explicitly forbid>
- **<Database/storage> only** — no <forbidden alternatives, e.g. no ORM, no other DB>
- **<Frontend approach> only** — no <forbidden libs / build steps>
- **<Dependency policy>** — e.g. no new packages without approval; keep `<manifest>` in sync
- <Runtime/version assumption — e.g. Python 3.10+ / Node 20+>

---

## Subagent policy
<!-- Optional. Keep only if you actually want this workflow enforced. -->
- Use a builtin Explore subagent for codebase exploration before implementing any new feature
- Use a subagent to verify test results after any implementation
- When asked to plan, delegate codebase research to a subagent before presenting the plan
- Use the builtin Plan subagent in plan mode

---

## Commands
```bash
# Setup
<install / venv / dependency-install commands>

# Run dev server
<dev run command>   # <port / URL>

# <Other useful endpoints, e.g. API docs URL>

# Tests
<run all tests>
<run one test file>
<run one test by name>
```

---

## Development

- <How to run locally + non-obvious dev details: port, hot-reload, watch mode>
- <Local data/DB bootstrap: how to create/seed the database or fixtures before first run>
- <Env/config setup for dev: .env file, required vars, sample config>
- <Any "this dir/file is empty/stubbed — don't assume it exists yet" warnings>

---

## Testing

- <Test framework + how to invoke; any config file (pyproject.toml/jest.config) and where it lives>
- <How to test the main unit type — e.g. how to spin up a test client / mock the DB>
- <Test-isolation rule — e.g. use a throwaway/in-memory DB, never the dev DB>
- <Fixtures/conftest/setup location and what they provide>

---

## Deployment

<!-- STUB until a target environment exists. Capture once decided: -->
- <Production run command / process manager / container entry>
- <Required environment variables (secrets, DB path/URL, ports)>
- <Database migration/init step on deploy>
- <Static asset / build / CDN strategy>
- <CI/CD pipeline or release process, if any>

---

## Implemented vs stub <routes/features>
<!-- Optional but high-value for step-by-step or in-progress projects. Delete if everything is built. -->

| <Route/Feature> | Status |
|---|---|
| `<item>` | Implemented — <detail> |
| `<item>` | Stub — <Step N / reason> |

**Do not implement a stub <item> unless the active task explicitly targets it.**

---

## Warnings and things to avoid

<!-- Project-specific gotchas only — the bugs someone WILL hit if not warned. Delete generic ones. -->
- <Footgun #1 — e.g. a default that must be overridden on every connection>
- <Footgun #2 — e.g. a fixed port / path that must not change>
- <Anything currently empty/stubbed that looks usable but isn't>
- <Convention that is easy to violate accidentally>
