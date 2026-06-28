---
description: Generate a sequential, implementation-ready specification markdown file in .claude/specs/ from a feature name.
argument-hint: "<feature name>  e.g. \"user login\" or \"expense add form\""
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Generate a feature specification for Spendly

Take a **feature name** as input and produce a detailed, specification-driven
markdown document saved under `.claude/specs/`, following the exact conventions
already used in this repository (see `.claude/specs/001-database-setup.md`).

**Feature name (input):** `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the user for the feature name before continuing.

---

## Step 1 — Determine the next sequence number (unique + sequential)

1. List every existing spec: `Glob` `.claude/specs/*.md`.
2. Parse the leading 3-digit numeric prefix of each filename (`NNN-...`).
3. The next number = **(highest existing prefix) + 1**, zero-padded to 3 digits.
   - If `.claude/specs/` is empty, start at `001`.
   - Never reuse or skip a number; the prefix must be unique and strictly sequential.
4. Build the slug from the feature name: lowercase, trim, replace any run of
   non-alphanumeric characters with a single hyphen, strip leading/trailing
   hyphens (e.g. `"User Login!"` → `user-login`).
5. **Final filename:** `.claude/specs/<NNN>-<slug>.md`
   (matches the existing format, e.g. `.claude/specs/001-database-setup.md`).

## Step 2 — Create and check out a new feature branch

Before writing the spec, create a dedicated git branch for this feature so the
spec and its eventual implementation live on their own branch.

1. Confirm the working tree is a git repo and check the current state:
   `git rev-parse --abbrev-ref HEAD` and `git status --porcelain`.
2. **Branch name:** `feature/<NNN>-<slug>` — reuse the exact `<NNN>` and `<slug>`
   computed in Step 1 (e.g. `feature/002-login-and-logout`).
3. Create **and** check out the branch off the current branch in one step:
   `git checkout -b feature/<NNN>-<slug>`.
   - If a branch with that name already exists, do **not** overwrite it — switch
     to it with `git checkout feature/<NNN>-<slug>` instead, and note this in the
     final output.
4. Verify you are on the new branch (`git rev-parse --abbrev-ref HEAD`) before
   proceeding. Do **not** commit or push — only create and switch the branch; the
   user controls commits.

## Step 3 — Read the rules and the codebase before writing

- **Read `CLAUDE.md`** in full and honor every constraint it states (FastAPI +
  Jinja2 + SQLite only, all SQL in `database/db.py`, parameterized queries,
  `url_for()` in templates, port 5001, no new pip packages, the
  "Implemented vs stub routes" table, etc.). The spec must not contradict it.
- **Analyze the existing codebase** so the spec aligns with reality, not assumptions:
  - `database/db.py` — live schema, tables, columns, constraints, and the
    available helpers (`get_db`, `init_db`, `seed_db`, `seed_dummy_data`,
    `hash_password`, `verify_password`).
  - `app.py` — existing routes, which are implemented vs stubbed, route naming
    and `url_for()` resolution, the `lifespan` bootstrap.
  - `templates/` — `base.html` and per-page templates the feature would touch.
  - `static/`, `scripts/`, `tests/` — existing patterns to reuse.
  - Read the existing `.claude/specs/001-database-setup.md` to mirror its
    section structure, tone, and formatting.
- **Reuse, don't reinvent.** Before specifying anything new, check whether a
  table, column, helper, route, template, or script already exists that the
  feature should *extend* rather than duplicate. Call out the reuse explicitly
  in the spec. If the feature already exists, say so and stop instead of
  generating a duplicate.
- If the feature maps to a known stub step in the CLAUDE.md route table
  (e.g. logout, profile, add/edit/delete expense), reference that step.

## Step 4 — Write the specification file

Create the file at the path from Step 1 using `Write`. Use this section
structure (the same shape as `001-database-setup.md` — keep, drop, or add
sections to fit the feature, but cover all of the following):

```markdown
# Spec: <Feature Title> (<NNN>)

**Feature ID:** <NNN>
**Status:** Draft (<today's date>)
**Owner:** <git user / repo owner>
**Target file(s):** <files this feature will create or modify>
**Created:** <today's date>

---

<dynamically chosen sections — see "Choosing the sections" below>
```

### Choosing the sections (dynamic format)

**Do not emit a fixed list of sections.** First classify the feature, then
assemble only the sections that are relevant — number them sequentially
(`## 1.`, `## 2.`, …) in the order you choose. The header block above and the
**Summary** section are the only ones that are always present.

**Always include (the spine of every spec):**
- **Summary** — what the feature is, why it exists, how it fits Spendly.
- **Acceptance Criteria** — `- [ ]` checklist of verifiable outcomes.
- **Definition of Done** — final completion checklist.

**Classify the feature, then pull in the matching sections:**

| If the feature involves… | Include sections such as… |
|---|---|
| New/changed routes or pages | API / Route Specification, Technical Design, User Stories |
| New/changed data | Database Changes, Data Model, Migration/Backfill notes |
| Forms or user input | Validation Rules, Error Handling, UX / Template Notes |
| Auth / sessions / sensitive data | Security Considerations, Threat notes |
| Behavior worth guarding | Testing Scenarios, Edge Cases |
| Depends on other steps/specs | Dependencies, Constraints (from CLAUDE.md) |
| Real unknowns or trade-offs | Risks & Considerations, Open Questions |
| Scope worth bounding | Goals, Non-Goals |

**Rules for the dynamic selection:**
- Pick the sections the feature actually needs — a pure DB feature has no
  "Validation Rules / UX" section; a static-page feature has no "Database
  Changes" section. **Omit** what doesn't apply rather than padding it with
  "N/A".
- If a borderline section adds real value, include it; if it would only repeat
  another section, fold it in instead.
- You may rename a section or add a feature-specific one not in the table when it
  communicates better — the goal is the clearest spec for *this* feature, not
  conformance to a fixed outline.
- Keep the look and tone of `001-database-setup.md` (tables, checklists, fenced
  code, ER sketches) wherever they fit.

Fill every chosen section with **concrete, codebase-specific** detail (real
table/column names, real route names, real helper names) — never generic
placeholder text. The result must be implementation-ready for Product,
Engineering, QA, Claude Code, Codex, or Cursor to pick up directly.

## Step 5 — Output

After writing the file, report to the user in this order:
1. The **branch** that was created and checked out (or reused).
2. The **generated filename** (the full `.claude/specs/<NNN>-<slug>.md` path).
3. The **complete markdown specification document** that was written.

---

## Constraints (must follow)

- Follow the existing naming convention exactly: `NNN-slug.md`, prefix unique and
  sequential, zero-padded to 3 digits.
- Match the **tone and formatting** of the existing spec(s) (tables, checklists,
  fenced code), but choose the **sections dynamically** per the feature — do not
  force a fixed outline.
- The spec must comply with every rule in `CLAUDE.md` and must not contradict the
  actual codebase — analyze before writing.
- Prefer reusing/extending existing tables, helpers, routes, templates, and
  scripts over inventing new ones; never duplicate existing functionality.
- Always create and check out the `feature/<NNN>-<slug>` branch (Step 2) before
  writing the spec; never commit or push automatically — leave commits to the user.
- Do not implement the feature — only produce the specification document.
