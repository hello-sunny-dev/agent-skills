# Agent Skills

Skills I use with Claude Code for recurring frontend work. Each one turns a check I do by hand, or a mistake I have seen, into a repeatable process.

## Skills

| Skill | Use it when | What it adds |
| --- | --- | --- |
| [`inline-pdf-review`](skills/inline-pdf-review/SKILL.md) | Rendering a PDF with many images in the page, or building a DocuSign-style signing flow | Measures real browser memory cost, with a script that can act as a CI gate, and lists the design decisions to settle first |
| [`a11y`](skills/a11y/SKILL.md) | Reviewing a component or page for accessibility | A WCAG 2.2 AA audit ranked by user impact, with fixes and manual checks |
| [`verify-sheet`](skills/verify-sheet/SKILL.md) | A spreadsheet is about to drive a bulk change | Finds what the columns really mean, reduces rows to the real change set, and checks targets against live data |
| [`security-audit`](skills/security-audit/SKILL.md) | `npm audit` or Snyk flags vulnerabilities | Reduces the count to root advisories, separates production from dev exposure, and picks the least invasive fix |

## Why they are built this way

- **Evidence over assumptions.** Each skill says how to verify its result and what to do when something cannot be verified.
- **Scripts for repeatable work.** Parsing and measuring are done by code, so they give the same answer each time.
- **Plain trade-offs.** The skills say when not to use them and which decisions belong to a person.

## Using a skill

Copy a skill's folder into `~/.claude/skills/`, or `.claude/skills/` in a project.

`inline-pdf-review` needs `pdfimages` from Poppler. `security-audit` needs Node.
