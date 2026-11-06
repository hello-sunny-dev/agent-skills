# Reviewing an in-page PDF viewer or signing flow

Work through these before the build starts. Each one is a decision someone has
to make. Left undecided, whoever builds it (person or agent) will invent an
answer, and it will look finished while being wrong.

## Before anyone builds

**Does the document need to be in the page at all?**
Handing over a download link avoids every problem below. Inline viewing is a
real requirement when the customer has to read and sign in place, but it is a
choice with a cost, and the cost is that the document's memory becomes yours.

**What is the document made of?**
A document that is almost all text behaves nothing like one full of
high-resolution images. Ask before, not after.

**What is the pixel budget?**
If nobody sets one, print-resolution assets go in as they were. Design files
are built for print, so exports come out at print resolution and look correct
on screen. Set a number and assert it in CI.

**What is the coordinate contract?**
For anything placed over the document (a signature box, a highlight, a field),
the renderer must publish where those regions are, as fractions of the page
(0 to 1), measured against its own render. Note the origin: PDF libraries
often use bottom-left, the DOM uses top-left. Without this the frontend is
guessing, and every resize breaks it.

## Interactive elements

**A button printed into the PDF is not a button.**
A PDF annotation can hold a URL and nothing else, so nothing inside the
document can open a modal or call application code. If the flow needs a real
control, it has to be an HTML layer on top, positioned from the coordinate
map. This is a constraint, not a preference.

**Every field that looks fillable needs a real target.**
If several fields are printed pixels and only one control works,
a customer who reaches for the wrong one concludes the page is broken. Give
each its own target, and its own accessible name, not a row of identical
labels.

**Check the annotation layer for click conflicts.**
If real PDF links are enabled, react-pdf renders them with `pointer-events`
active. An overlay element sitting on top needs an explicit higher `z-index`
or the annotation eats the click.

## Instant feedback that has to match the server

If the frontend paints a result before the server re-renders the document,
that is a copy of the server's output and has to agree with it.

- Draw in the same coordinate space the server measured against, via a
  `viewBox`, so it scales with the page instead of being recomputed.
- Position from the server's own region map, never from a frontend
  measurement.
- Mirror the server's text-fitting rules exactly, including how it counts
  characters. Counting code points and counting UTF-16 units can give different
  results.
- Read how the server bakes it before writing the copy. Mask sizes, baselines
  and stroke weight all follow from that, and are found by comparing the two
  renders side by side.
- Point the agent or the harness at both repositories at once. It can only
  make the two renders agree if it can see both.

## Fonts in a generated asset

If a signature or label is rendered as a font and then embedded, check where it
ends up being drawn. Inside an `<img>` data URI, or any sandboxed context, the
asset cannot reach fonts the host page loaded, so it silently falls back to a
default face.

Convert to an SVG with the font embedded as a base64 `@font-face`. A fixed
`viewBox` also makes it scale with the page: live text at a fixed size stays
that size while the page shrinks around it, so it reads as oversized on a
narrow screen.

## Canvas and virtualization

**Virtualization is two halves, and you need both.** Mount only what is near
the viewport, and let everything else still occupy its space. Drop the second
half and it is lazy loading: scroll height changes under the reader and the
position jumps.

A PDF viewer does not give you virtualization. Build it:

- Every page keeps a fixed-size wrapper, sized from the measured page ratio, so
  scroll geometry and anchors are correct from the first paint.
- Only pages within a small window of the one in view mount a canvas.
- Any page that must be interactive (one carrying a signature region) stays
  mounted regardless of where the viewport is, on every device.
- Jump to those pages instantly rather than smooth-scrolling, or the reader
  watches a reel of empty placeholders fly past.
- Set `overflow-anchor: none` on the wrappers. If the browser anchors to a node
  inside a canvas that then unmounts, the scroll drops to the top with no JS
  scroll call involved, which makes it very hard to attribute.
- Moving focus out of an unmounting element first, likewise: losing the focused
  node sends the browser to the top of the document.

**Text layer.** Selectable text means a positioned DOM node per text run, for
every mounted page. Worth turning off on phones, where touch selection is
barely usable anyway.

**Device pixel ratio.** Phones report up to 3, and canvas memory scales with
its square, so 3 costs 2.25 times what 2 does. Cap it at 2 on phones; it still
looks crisp on a retina screen.
