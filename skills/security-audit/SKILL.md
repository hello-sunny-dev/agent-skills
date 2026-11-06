---
name: security-audit
description: Triage and fix npm audit / Snyk vulnerabilities in a JS/TS repo — collapse fan-out to root advisories, decide override vs targeted vs force, flag DEV/BUILD vs PROD-RUNTIME impact, verify, and produce a ticket-ready summary. Use when a pipeline/Snyk flags npm vulnerabilities, `npm audit` reports high/critical, a security ticket lands, or the user says "security audit", "fix vulns", "npm audit fix".
---

# Security Audit — npm vuln triage & fix

Fix vulnerabilities **surgically**, never blindly. The count npm reports is inflated by
fan-out — a handful of root advisories showing up under every package that depends on
them. Find the roots, fix those, and tell the human what actually matters: **is it
prod-runtime or just build/dev tooling, and does the patch change real logic?**

## Golden rules

- **Never `npm audit fix --force` on a whim.** It installs semver-major breaking upgrades
  across the tree (silent prod breakage) and doesn't stop transitive churn. Reserve for
  planned, fully-QA'd windows only.
- **`fixAvailable: false` ≠ unfixable.** It usually means no *parent* published a
  compatible range yet → fix with an `overrides` floor bump (check `npm view <pkg> version`
  for the real patched version). This is the recurring-transitive strategy.
- **Bump the whole "trio" together** when a framework splits across packages (e.g. `next`
  + `@next/third-parties` + `eslint-config-next`) — keep versions aligned.
- **Prod vs dev is the single most important flag.** Verify, don't guess (see step 3).

## Workflow

Run these as a checklist (one todo each):

1. **Snapshot & triage.** Collapse fan-out to root advisories:
   ```bash
   npm audit --json | node <skill>/scripts/triage.mjs
   ```
   Output = root advisories (the real vulns), fix-availability buckets
   (needs-overrides / semver-major / safe), and per-root a dev/build guess. The "32 high"
   almost always collapses to 2–4 roots.

2. **Confirm fixed versions.** For each root: `npm ls <pkg>` (where it resolves) +
   `npm view <pkg> version` (latest) + read the advisory's fixed range.

3. **Classify prod exposure — VERIFY, don't guess.** Per root package, label one of:
   - `PROD-RUNTIME` — ships in the bundle / runs at runtime (framework core, form libs,
     http clients, carousel, anything imported in `src/`).
   - `BUILD` — runs at build only (postcss, tailwind, webpack, svgo, sharp-in-optimizer).
   - `DEV-ONLY` — test/lint/storybook tooling (jest, eslint, storybook, glob, minimatch).
   Verify with: `npm ls <pkg>` (tree parent) **and** `grep -rE "from ['\"]<pkg>" src/`
   (0 hits + dev/build tree = not prod-runtime). State **"Prod runtime exposure: NONE /
   <describe>"** with the evidence.

4. **Pick the fix method** (climb to the least-invasive that works):
   - safe bucket → `npm audit fix` (non-force).
   - `fixAvailable:false` → `overrides` floor bump in `package.json`.
   - specific breaking-but-needed → targeted `npm install <pkg>@<ver>`.
   - `--force` wants a **downgrade** of a prod framework → reject; override *above* the
     conservative range instead.

5. **Apply + reinstall.** Edit `overrides` / install, then `npm install`, then re-audit.
   Confirm resolved versions: `npm ls <pkg>` shows `overridden` at the patched version.

6. **Verify (all must pass) — run the EXACT CI commands, not your own shortcuts:**
   ```bash
   grep -rnE 'npm (run )?test|jest|npm ci' .github/workflows   # find what CI ACTUALLY runs; adjust for your CI
   npm ci                       # clean install from lockfile — resolves differently than `npm install`
   npm audit                    # target: 0 (or only accepted/unfixable, documented)
   rm -rf .next && npm run type-check
   npm run test -- --coverage   # if CI uses --coverage: it pulls istanbul→test-exclude→minimatch,
                                # a whole dep chain plain `npm test` NEVER loads. THIS is the gate.
   npm run lint                 # eslint has its own minimatch/brace-expansion chain
   npm run build                # only if a BUILD/PROD pkg changed
   ```
   **After ANY `overrides` change, run the exact CI test command** (check the config — it's often
   `--coverage`, `--ci`, or a custom reporter). Plain `npm test` passing ≠ CI passing: coverage
   instrumentation, lint, and clean `npm ci` each exercise dep paths a warm dev run skips.

7. **Summary (always) + doc (ask).** See below.

## What the summary MUST state (per vulnerability)

- Version `from → to`, CVE link, severity.
- **Type label: `PROD-RUNTIME` / `BUILD` / `DEV-ONLY`** ← most important.
- **Real-logic impact?** Does the patch change app behaviour, or is it inert?
- **Prod runtime exposure: NONE / <describe>** — verified, with evidence.
- Method (`npm audit fix` / targeted / `overrides` / why-not-`--force`).
- **⚠️ If it affects the real webapp → say so explicitly** + list the exact flows/pages to
  eyeball. If not: **"Manual checks: NONE"** + one-line why.
- Verification block: audit 0 / type-check / unit N/N / build.

## Summary output — ASK the user

Always **print** the summary to chat. Then ask:

> "Append this to a security doc? If yes, which path? Otherwise I'll leave it as printout only."

Don't hardcode a destination. If they name a rolling doc, append as a new dated round
(newest first).

## QA recommendation (report it in the summary)

Say whether the change needs a full QA pass or a lighter check:

- **Lighter check is reasonable** when the fix is patch or minor package updates, code review
  is done, and CI blocks on any surviving vulnerability.
- **Full smoke test** for a major-version upgrade or any judged breaking-change risk.

The team's release process decides. This is a recommendation with evidence, not a decision.

## Known traps

- **`overrides` unifying a package across majors can break API.** A CVE range like
  `<=5.0.7` may span every major line with the fix ONLY forward on the newest (no patched
  1.x/2.x). Forcing all consumers to the new major can break ones that expect the old
  export shape. Real case: `brace-expansion` v1 = callable default export, v5 = object with
  named `expand` → `minimatch@3` crashed ESLint (`TypeError: expand is not a function`).
  Fix = co-bump the *consumer* too (`minimatch` → v10, which speaks v5's export). **Always
  run `npm run lint` + `npm test` after an override — the pre-commit hook will catch it,
  but catch it yourself first.**
- **Version-selector override keys** (`"pkg@1.x": "…"`) only help if a non-vulnerable
  version exists on that line. If the maintainer fixed forward only, they don't.

## Scripts

- `scripts/triage.mjs` — parse `npm audit --json` → root advisories + fix-availability
  buckets + dev/build heuristic. Deterministic; use it instead of hand-writing audit-JSON
  parsers each round.
