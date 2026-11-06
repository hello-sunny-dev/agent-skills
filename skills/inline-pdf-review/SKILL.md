---
name: inline-pdf-review
description: Check what a PDF costs in RAM when rendered in the browser, and review the design of an in-page PDF viewer or signing flow. Use when a project embeds a PDF viewer (pdf.js, react-pdf), builds a DocuSign-style inline signing or annotation flow, renders a PDF with many or high-resolution images, generates PDFs server-side from design assets, or when a page showing a PDF crashes, blanks, or reloads on mobile. Also use before handing PDF work to an agent or another team, to settle the decisions a spec leaves out.
---

# PDF memory and inline viewer review

Two failures keep recurring with in-page PDFs. Both are cheap to catch up front
and expensive to find from a bug report.

## When to use

- A project renders a PDF inside the page with pdf.js, react-pdf or similar,
  rather than linking to a download.
- Building a DocuSign-style flow: signing, annotating or overlaying controls on
  a document.
- A PDF contains many or high-resolution images. Its browser memory cost can be
  far larger than its file size suggests.
- A PDF is generated server-side from design-tool assets, so nobody has decided
  what the images may cost.
- A page showing a PDF crashes, blanks its pages, or reloads on mobile.
- Before handing PDF work to an agent or another team, to settle the decisions
  a spec leaves out.

## When NOT to use

- Parsing, extracting text from, splitting or merging PDFs. This skill is about
  rendering one in a browser.
- Filling native PDF form fields, which is a different mechanism from an HTML
  overlay.
- A download link with no in-page viewer. None of the costs here apply.
- General page performance work unrelated to a document viewer.

## 1. Measure the memory cost

File size tells you nothing. A viewer unpacks every embedded image to raw
pixels and holds them while the document is open, and pdf.js rasterises each
page onto a canvas on top of that. Both costs are `width x height x 4 bytes`,
so compression does not reduce them. Only fewer pixels does.

Run `scripts/pdf_memory.py` from this skill's directory:

```bash
python3 scripts/pdf_memory.py document.pdf --live-canvases 3
```

Needs `pdfimages` (`brew install poppler`, or `apt install poppler-utils`).
Exits non-zero over budget, so it works as a CI gate. Flags: `--budget` MB
(default 40), `--dpr` (default 2), `--live-canvases` (omit to assume every
page mounted).

It prints decoded image total, canvas cost, and the largest images with their
ppi. A screen needs about 150 ppi; the script flags anything over 300, which
is a print-resolution asset no screen can show, usually exported straight from
the design file.

**Assume nothing is fine because it looks fine.** A 100KB image at 2400x2400
drawn small costs 22MB of RAM and renders perfectly.

## 2. Review the viewer design

Run through [references/viewer-review.md](references/viewer-review.md) when a
project renders a PDF in the page. It covers the decisions to make before the
work starts: who owns the signature coordinates, why a printed button can never
be wired up, what must be settled for instant feedback to match the server's
render, and the canvas/virtualization rules.

## When the page already crashes on mobile

1. Run the script. If decoded images are tens of MB, that is the cause.
2. Check whether every page mounts a canvas at once. `pages x w x h x dpr^2 x 4`.
3. iOS gives you nothing useful: Safari says "A problem repeatedly occurred"
   whether the tab died from memory, a loop, or a crash. **Open the same page
   in Chrome or Edge on Android**, which says "To save memory, [browser]
   removed some content" and names the cause. The device that fails hardest
   tells you the least.
4. Device farms do not reproduce memory pressure. Use a real low-RAM handset.

Fixes, in the order that pays off: cap device pixel ratio at 2 on phones
(canvas memory scales with its square), mount only the pages near the viewport,
and downscale embedded images server-side to the size the page draws them at.
Then assert a raw-pixel ceiling in CI so the next oversized asset fails the
build instead of a customer's phone.
