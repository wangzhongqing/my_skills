#!/usr/bin/env python3
"""Measure a standalone HTML artifact in a real browser at two viewports.

This closes the gap that both parent skills left open. eli5's static checker can
only *warn* about `overflow: hidden` because text parsing cannot tell whether it
fixed reflow or hid a clip. ELI5+ required desktop/mobile rendering checks but
shipped no tool to perform them.

Requires Playwright (`pip install playwright && playwright install chromium`).
When it is unavailable this script exits 2 and prints the exact limitation, so a
caller can never mistake "not run" for "passed".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VIEWPORTS = [
    ("narrow", 320, 720),
    ("mobile", 375, 812),
    ("desktop", 1440, 900),
]

# Report an element as overflowing only when it exceeds the viewport by more
# than this many CSS pixels; sub-pixel layout noise is not a defect.
TOLERANCE = 1


PROBE = """
() => {
  const doc = document.documentElement;
  const body = document.body;
  const vw = window.innerWidth;

  const overflowing = [];
  const all = document.querySelectorAll('main *');
  for (const el of all) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const right = rect.right;
    const left = rect.left;
    if (right > vw + TOLERANCE_PROBE || left < -TOLERANCE_PROBE) {
      overflowing.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className || '').toString().slice(0, 60),
        left: Math.round(left),
        right: Math.round(right),
        text: (el.textContent || '').trim().slice(0, 40)
      });
    }
  }

  // Interactive controls that escape the viewport.
  const controls = [];
  for (const el of document.querySelectorAll('button, a, input, select, textarea, summary')) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (rect.right > vw + TOLERANCE_PROBE || rect.left < -TOLERANCE_PROBE) {
      controls.push({
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || el.value || '').trim().slice(0, 40),
        left: Math.round(rect.left),
        right: Math.round(rect.right)
      });
    }
  }

  return {
    scrollWidth: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0),
    clientWidth: doc.clientWidth,
    innerWidth: vw,
    overflowing: overflowing.slice(0, 15),
    overflowCount: overflowing.length,
    controls: controls.slice(0, 10),
    controlCount: controls.length,
    h1: document.querySelectorAll('h1').length,
    main: document.querySelectorAll('main').length,
    external: performance.getEntriesByType('resource')
      .map(r => r.name)
      .filter(n => !n.startsWith('file:') && !n.startsWith('data:')),
    title: document.title
  };
}
"""


def run() -> int:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("[ERROR] Playwright is not installed, so geometry was NOT verified.")
        print("        Install it with:")
        print("          pip install playwright && playwright install chromium")
        print("        Until then, report only static validation — never claim")
        print("        that layout, overflow, or visual quality was checked.")
        return 2

    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Standalone HTML artifact to measure")
    parser.add_argument("--json", action="store_true", help="Emit raw measurements as JSON")
    args = parser.parse_args()

    path: Path = args.path.resolve()
    if not path.is_file():
        print(f"[ERROR] Not a file: {path}")
        return 1

    url = path.as_uri()
    failures: list[str] = []
    warnings: list[str] = []
    report: dict[str, object] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for label, width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(url, wait_until="load")
                page.wait_for_timeout(150)

                probe = PROBE.replace("TOLERANCE_PROBE", str(TOLERANCE))
                data = page.evaluate(probe)
                report[label] = data

                if data["scrollWidth"] > data["clientWidth"] + TOLERANCE:
                    failures.append(
                        f"{label} ({width}px): horizontal scroll — "
                        f"scrollWidth {data['scrollWidth']} > clientWidth {data['clientWidth']}"
                    )

                if data["overflowCount"]:
                    sample = "; ".join(
                        f"<{item['tag']}.{item['cls']}> right={item['right']}"
                        for item in data["overflowing"][:4]
                    )
                    failures.append(
                        f"{label} ({width}px): {data['overflowCount']} element(s) outside the viewport — {sample}"
                    )

                if data["controlCount"]:
                    failures.append(
                        f"{label} ({width}px): {data['controlCount']} interactive control(s) outside the viewport"
                    )

                if data["external"]:
                    failures.append(
                        f"{label} ({width}px): external runtime request(s): {data['external'][:3]}"
                    )

                if data["h1"] != 1:
                    failures.append(f"{label} ({width}px): expected exactly one <h1>, found {data['h1']}")
                if data["main"] != 1:
                    failures.append(f"{label} ({width}px): expected exactly one <main>, found {data['main']}")

                # Overlap detection for sibling blocks that both carry text.
                overlaps = page.evaluate(
                    """
                    () => {
                      const out = [];
                      const blocks = [...document.querySelectorAll('.scene, .visual, .callout, .boundary')];
                      for (let i = 0; i < blocks.length; i++) {
                        for (let j = i + 1; j < blocks.length; j++) {
                          const a = blocks[i].getBoundingClientRect();
                          const b = blocks[j].getBoundingClientRect();
                          if (a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top) continue;
                          if (blocks[i].contains(blocks[j]) || blocks[j].contains(blocks[i])) continue;
                          out.push([blocks[i].className, blocks[j].className]);
                        }
                      }
                      return out.slice(0, 5);
                    }
                    """
                )
                if overlaps:
                    warnings.append(f"{label} ({width}px): {len(overlaps)} overlapping block pair(s): {overlaps}")

                page.close()
        finally:
            browser.close()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not failures else 1

    if failures:
        for item in failures:
            print(f"[ERROR] {item}")
        for item in warnings:
            print(f"[WARN] {item}")
        return 1

    if warnings:
        # Warnings are not auto-failures, but a bare "[PASS]" next to a real
        # overlap report reads as approval and gets skimmed. Say PASS WITH
        # WARNINGS so nobody mistakes "checked" for "clean".
        for item in warnings:
            print(f"[WARN] {item}")
        widths = ", ".join(f"{label}={width}px" for label, width, _ in VIEWPORTS)
        print(
            f"[PASS-WITH-WARNINGS] {path.name} — measured at {widths}; "
            f"{len(warnings)} warning(s) above need a human decision before delivery"
        )
        return 0

    widths = ", ".join(f"{label}={width}px" for label, width, _ in VIEWPORTS)
    print(f"[PASS] {path.name} — measured at {widths}; no overflow, no escaping controls, no external requests")
    return 0


if __name__ == "__main__":
    sys.exit(run())
