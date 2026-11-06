---
name: verify-sheet
description: Use when a ticket hands over a Google Sheet or CSV of rows to action in bulk (redirects, URL swaps, metadata, price or content updates), before writing any script or touching data. Turns a raw export into a verified, deduplicated change set and surfaces the defects in it. Also use when re-checking a sheet after its author says they have fixed something.
---

# Verify a sheet before acting on it

Marketing and SEO hand over spreadsheets meant to drive a bulk change. Those
sheets are usually crawl exports or hand-maintained lists, which means the
labels lie, the rows repeat, and a few values are wrong in ways that only show
up against live data.

Do this before writing the script that consumes the sheet. A bad row that
reaches a bulk command hits production content.

## 1. Get the real data out

Never work from what the grid looks like in a browser. Export it.

```bash
curl -sL -o sheet.csv "https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>"
```

- `<GID>` is the tab, visible in the URL as `#gid=...`. It is not always `0`.
- A 400 means the sheet is not link-shared. Ask for access, or if the tab is
  open in a signed-in browser, read it from there.
- Google Search Console exports have a `Chart` tab first and the actual rows on
  a `Table` tab. `gviz/tq?tqx=out:csv&sheet=Table` fetches a tab by name when
  you do not know the gid.
- Check for a `Metadata` tab. It often states what the export actually is, which
  may contradict what the ticket calls it.

## 2. Decode the columns against the data

Column headers describe what the author meant, not what the values are. Read
several real rows and work out what each column holds.

Signals that a header is misleading:

- A column named like a source URL whose values are unrelated to the target
  column on the same row. In a crawl export this usually means "the page the
  link was found on", not "the old URL".
- Row counts far larger than the number of distinct changes. Crawl exports
  carry one row per occurrence.
- A sheet called a redirect list whose `Metadata` tab says `Not found (404)`.

State your reading of each column back to the ticket author before building on
it. Getting this wrong inverts the entire change.

## 3. Collapse to the real change set

```python
import csv, collections
rows = list(csv.DictReader(open('sheet.csv')))
pairs = collections.Counter((r['<from>'].strip(), r['<to>'].strip()) for r in rows)
print(f"{len(rows)} rows -> {len(pairs)} unique pairs")
```

Then check the set for defects:

- **Conflicts**: same source, two different targets. Needs a human decision.
- **No-ops**: source equals target. Drop them.
- **Chains**: a target that is itself a source elsewhere. Order-dependent, and
  usually means the sheet's "final" value is not final.
- **Near-duplicates**: trailing slash, case, or query-string variants of the
  same URL. These need both forms in the map, longest first, or one will
  half-replace the other.
- **Odd ones out**: a row whose target breaks the pattern every sibling row
  follows. Often a copy-paste slip a row up or down.

## 4. Check every target against live data

This is the step that catches what inspection cannot. Do not skip it because
the values look well-formed.

```bash
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "<target-url>"
```

Run it over every distinct target. A 404 in that list is a row that would send
real traffic or real content to a dead page.

Also check the sources: some may already be fixed, which shrinks the job and
tells you the sheet is stale.

## 5. Measure the real scope, not the sheet's

The sheet's row count is not the work. Count occurrences in the actual system
you are about to change, whether that is the database, the codebase, or the
rendered site.

Two traps worth naming:

- **Relative versus absolute.** A sheet of absolute URLs hides every
  site-relative occurrence of the same path. Count both. Relative can easily
  outnumber absolute several times over.
- **Rendered pages versus stored records.** A crawl counts a shared module's
  link once per page it appears on. One stored record can be hundreds of crawl
  rows.

## 6. Take the defects back to the author

Ask about what blocks the work, not everything you noticed. For each defect
give the value, the evidence, and your reading of what it should be, so the
answer is a confirmation rather than an investigation.

Offer options where the fix is a judgement call:

> a) Move the pages to the new paths. The sheet stays correct.
> b) Drop the redirects so the old paths work again. The sheet needs redoing.
> c) Something else?

Do not ask who made the mistake. Ask what they want the outcome to be.

If a fix is small and you can make it yourself, say so and ask whether to go
ahead rather than editing the source of truth silently. Someone will read that
sheet again later.

## 7. Re-verify after they say it is fixed

Always. Re-export, diff against your saved copy, and re-run the live checks.

```bash
curl -sL -o sheet_v2.csv "<same export URL>"
md5 -q sheet.csv sheet_v2.csv     # cheap "did anything change at all"
```

Then confirm each claimed fix landed as described, and that nothing else moved.
A hand-typed correction can introduce a new bad value: a fix that is confirmed
in chat is not a fix that is confirmed in the sheet.

## Output

Hand back a short summary:

- What the columns actually mean
- Row count versus real change count
- Real scope measured against the live system
- Defects found, with evidence
- What you need answered before proceeding

Keep the verified pairs in a committed file (a small CSV) rather than
hardcoding them, so the change set is reviewable and re-runnable.
