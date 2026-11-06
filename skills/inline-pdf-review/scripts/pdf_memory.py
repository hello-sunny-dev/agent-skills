#!/usr/bin/env python3
"""Report what a PDF costs in RAM when a browser renders it.

File size is not the cost. A viewer unpacks every embedded image to raw pixels
and holds them for as long as the document is open, and a canvas-based viewer
(pdf.js) rasterises each page on top of that. Both are pixel counts, not bytes
on disk, so compression does not help.

Requires `pdfimages` (poppler): brew install poppler
"""
import argparse
import re
import shutil
import subprocess
import sys

BYTES_PER_PIXEL = 4  # RGBA
MB = 1024 * 1024

# A page drawn at 96 CSS ppi needs no more than ~150 ppi of source image to look
# sharp. Well above that is pixels the screen can never show.
SCREEN_PPI_BUDGET = 150


def run_pdfimages(path):
    if not shutil.which("pdfimages"):
        sys.exit("pdfimages not found. Install poppler: brew install poppler")
    proc = subprocess.run(
        ["pdfimages", "-list", path], capture_output=True, text=True
    )
    if proc.returncode != 0:
        sys.exit(f"pdfimages failed: {proc.stderr.strip()}")
    return proc.stdout


def parse(listing):
    """Yield one dict per embedded image.

    An smask is the alpha channel of the image above it. It is a real decode
    cost, so it is counted, but it is not reported as a separate offender.
    """
    images = []
    for line in listing.splitlines():
        cols = line.split()
        if len(cols) < 15 or not cols[0].isdigit():
            continue
        try:
            images.append(
                {
                    "page": int(cols[0]),
                    "kind": cols[2],
                    "w": int(cols[3]),
                    "h": int(cols[4]),
                    "ppi": _ppi(cols[12]),
                    "disk": cols[14],
                }
            )
        except (ValueError, IndexError):
            continue
    return images


def _ppi(raw):
    m = re.match(r"^\d+", raw)
    return int(m.group()) if m else 0


def canvas_cost(pages, dpr, page_w=794, page_h=1123, live=None):
    """Cost of the rasterised pages themselves.

    `live` caps how many pages hold a canvas at once, which is what
    virtualization buys you. Without it, every page stays mounted.
    """
    mounted = pages if live is None else min(live, pages)
    return mounted * page_w * dpr * page_h * dpr * BYTES_PER_PIXEL


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf")
    ap.add_argument(
        "--budget",
        type=float,
        default=40.0,
        help="Fail above this many MB of decoded image pixels (default 40)",
    )
    ap.add_argument(
        "--dpr",
        type=float,
        default=2.0,
        help="Device pixel ratio for the canvas estimate (default 2)",
    )
    ap.add_argument(
        "--live-canvases",
        type=int,
        default=None,
        help="Pages holding a canvas at once. Omit to assume all of them.",
    )
    args = ap.parse_args()

    images = parse(run_pdfimages(args.pdf))
    if not images:
        print("No embedded images found.")
        return 0

    total = sum(i["w"] * i["h"] * BYTES_PER_PIXEL for i in images)
    pages = max(i["page"] for i in images)

    print(f"{args.pdf}\n")
    print(f"Embedded images   {len(images)} across {pages} pages")
    print(f"Decoded to RAM    {total / MB:.1f} MB   (budget {args.budget:.0f} MB)")

    canvas_all = canvas_cost(pages, args.dpr)
    line = f"Page canvases     {canvas_all / MB:.1f} MB at DPR {args.dpr:g}, every page mounted"
    if args.live_canvases:
        held = canvas_cost(pages, args.dpr, live=args.live_canvases)
        line += f"\n                  {held / MB:.1f} MB with {args.live_canvases} live"
    print(line)

    # Worst offenders: biggest decoded cost, skipping the alpha masks that
    # merely shadow the image above them.
    real = [i for i in images if i["kind"] != "smask"]
    real.sort(key=lambda i: i["w"] * i["h"], reverse=True)

    print("\nLargest images")
    print(f"  {'page':>4}  {'pixels':>11}  {'RAM':>8}  {'disk':>7}  {'ppi':>6}")
    for i in real[:8]:
        cost = i["w"] * i["h"] * BYTES_PER_PIXEL
        flag = "  <-- oversized" if i["ppi"] > SCREEN_PPI_BUDGET * 2 else ""
        print(
            f"  {i['page']:>4}  {i['w']:>5}x{i['h']:<5}  "
            f"{cost / MB:>6.1f}MB  {i['disk']:>7}  {i['ppi']:>6}{flag}"
        )

    over = [i for i in real if i["ppi"] > SCREEN_PPI_BUDGET * 2]
    if over:
        print(
            f"\n{len(over)} image(s) above {SCREEN_PPI_BUDGET * 2} ppi. "
            "Print-resolution assets, most likely straight out of the design file. "
            "Downscale to the size the page actually draws them at."
        )

    if total / MB > args.budget:
        print(
            f"\nFAIL  {total / MB:.1f} MB of decoded pixels exceeds the "
            f"{args.budget:.0f} MB budget."
        )
        return 1

    print(f"\nPASS  within the {args.budget:.0f} MB budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
