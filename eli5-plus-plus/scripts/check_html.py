#!/usr/bin/env python3
"""Deterministic checks for standalone ELI5++ HTML artifacts.

Derived from eli5's checker, with one added rule: an inline <svg> must carry an
accessible name (<title>, role="img" + aria-label, or aria-hidden="true" for
decorative art). The original script passed unlabelled SVG silently even though
its own quality gate required diagram labels.
"""

from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path


REMOTE_URL = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}|\bREPLACE_ME\b|\bTBD\b", re.IGNORECASE)
REMOTE_CSS_URL = re.compile(r"url\(\s*(['\"]?)(?:https?:)?//", re.IGNORECASE)
REMOTE_CSS_IMPORT = re.compile(
    r"@import\s+(?:url\(\s*)?['\"]?(?:https?:)?//",
    re.IGNORECASE,
)
EXTERNAL_API = re.compile(r"\b(?:fetch|WebSocket|EventSource)\s*\(|\bXMLHttpRequest\b")
DOCUMENT_OVERFLOW = re.compile(
    r"(?:^|[},])\s*(?:html|body|main)(?:\s*,\s*(?:html|body|main))*\s*"
    r"\{[^{}]*\boverflow(?:-x)?\s*:\s*hidden\b",
    re.IGNORECASE | re.DOTALL,
)
PLAY_GLYPHS = ("▶", "⏵", "►", "⏯")

STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def steps_dimmed_by_default(source: str) -> list[str]:
    """Return opacity declarations that dim a bare `.stage-step` rule.

    Parsed structurally rather than with one clever regex: a step dimmed by
    default is invisible whenever JavaScript never runs, so motion must be
    opt-in. The correct form is `.stage--armed .stage-step { opacity:.28 }`,
    where the selector is ancestor-qualified — that must NOT be flagged.
    Matching the exact selector string is the only way to tell those apart
    reliably.
    """
    hits: list[str] = []
    for block in STYLE_BLOCK.findall(source):
        css = CSS_COMMENT.sub("", block)
        for rule in CSS_RULE.finditer(css):
            selector = rule.group(1).strip()
            if selector != ".stage-step":
                continue
            declaration = re.search(r"\bopacity\s*:\s*(0?\.\d+|0)", rule.group(2))
            if declaration and float(declaration.group(1)) < 0.5:
                hits.append(declaration.group(0).strip())
    return hits


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.has_viewport = False
        self.main_count = 0
        self.h1_count = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stack: list[str] = []
        self.executable_chunks: list[str] = []
        self.style_chunks: list[str] = []
        self._open_svgs: list[dict[str, object]] = []

    def finish(self) -> None:
        """Flush state that handle_endtag never sees (e.g. unclosed <svg>)."""
        for record in self._open_svgs:
            self._close_svg(record)
        self._open_svgs.clear()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {name.lower(): value or "" for name, value in attrs}
        self.stack.append(tag)

        # ELI5++ addition: inline SVG is this skill's primary diagram medium, so
        # an unlabelled <svg> is a real accessibility defect. A purely
        # decorative SVG must opt out explicitly with aria-hidden="true" or
        # role="presentation"/"none".
        if tag == "svg":
            self._open_svgs.append(
                {
                    "line": self.getpos()[0],
                    "explicit": bool(
                        attributes.get("aria-label", "").strip()
                        or attributes.get("aria-labelledby", "").strip()
                        or attributes.get("role", "").lower() in {"img", "presentation", "none"}
                        or attributes.get("aria-hidden", "").strip().lower() == "true"
                    ),
                    "title": False,
                    "desc": False,
                }
            )
        elif tag in {"title", "desc"} and self._open_svgs and "svg" in self.stack:
            self._open_svgs[-1][tag] = True

        if tag == "html":
            self.lang = attributes.get("lang", "").strip()
        elif tag == "meta" and attributes.get("name", "").lower() == "viewport":
            self.has_viewport = bool(attributes.get("content", "").strip())
        elif tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1

        if tag == "img" and "alt" not in attributes:
            self.errors.append("Image is missing an alt text equivalent.")

        if attributes.get("role", "").lower() == "img":
            if not attributes.get("aria-label", "").strip() and not attributes.get("aria-labelledby", "").strip():
                self.errors.append('Element with role="img" is missing an aria-label or aria-labelledby text equivalent.')

        for attribute, value in self._runtime_resources(tag, attributes):
            if any(REMOTE_URL.match(candidate) for candidate in self._resource_candidates(attribute, value)):
                self.errors.append(f"Remote runtime resource is not allowed: <{tag}> {attribute}={value!r}.")

        style = attributes.get("style", "")
        if REMOTE_CSS_URL.search(style):
            self.errors.append(f"Remote runtime resource is not allowed in the style attribute of <{tag}>.")

        for name, value in attributes.items():
            if name.startswith("on") and EXTERNAL_API.search(value):
                self.executable_chunks.append(value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "svg" and self._open_svgs:
            self._close_svg(self._open_svgs.pop())
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def _close_svg(self, record: dict[str, object]) -> None:
        if record["explicit"] or record["title"] or record["desc"]:
            return
        self.errors.append(
            f'Inline <svg> at line {record["line"]} has no accessible name: '
            'add <title>, or role="img" with aria-label, '
            'or mark it decorative with aria-hidden="true".'
        )

    def handle_data(self, data: str) -> None:
        if "script" in self.stack:
            self.executable_chunks.append(data)
        if "style" in self.stack:
            self.style_chunks.append(data)

        if "script" not in self.stack and "style" not in self.stack and any(glyph in data for glyph in PLAY_GLYPHS) and not any(
            tag in {"button", "a"} for tag in self.stack
        ):
            self.warnings.append("Visible play glyph appears outside a working button or link; this may be a false affordance.")

    @staticmethod
    def _runtime_resources(tag: str, attributes: dict[str, str]) -> list[tuple[str, str]]:
        resources: list[tuple[str, str]] = []
        if tag in {"script", "img", "source", "video", "audio", "iframe", "embed", "track", "input"}:
            for name in ("src", "srcset", "poster"):
                if attributes.get(name):
                    resources.append((name, attributes[name]))
        if tag == "object" and attributes.get("data"):
            resources.append(("data", attributes["data"]))
        if tag == "form" and attributes.get("action"):
            resources.append(("action", attributes["action"]))
        if tag == "base" and attributes.get("href"):
            resources.append(("href", attributes["href"]))
        if tag == "link" and "stylesheet" in attributes.get("rel", "").lower().split():
            if attributes.get("href"):
                resources.append(("href", attributes["href"]))
        return resources

    @staticmethod
    def _resource_candidates(attribute: str, value: str) -> list[str]:
        if attribute != "srcset":
            return [value.strip()]
        return [candidate.strip().split()[0] for candidate in value.split(",") if candidate.strip()]


def analyze_html(path: Path) -> tuple[list[str], list[str]]:
    """Return deterministic errors and warnings for one HTML artifact."""
    source = path.read_text(encoding="utf-8")
    parser = ArtifactParser()
    parser.feed(source)
    parser.close()

    # Unclosed <svg> elements never reach handle_endtag.
    parser.finish()

    errors = list(parser.errors)
    warnings = list(parser.warnings)

    if PLACEHOLDER.search(source):
        errors.append("Unresolved template placeholder found.")
    if REMOTE_CSS_URL.search(source):
        errors.append("Remote runtime resource is not allowed in CSS url(...).")
    if any(REMOTE_CSS_IMPORT.search(chunk) for chunk in parser.style_chunks):
        errors.append("Remote CSS import is not allowed.")
    if any(EXTERNAL_API.search(chunk) for chunk in parser.executable_chunks):
        errors.append("External API or socket call found in the standalone artifact.")
    if not parser.lang:
        errors.append("Document language is missing from the html element.")
    if not parser.has_viewport:
        errors.append("Viewport metadata is missing.")
    if parser.main_count != 1:
        errors.append(f"Expected exactly one main element; found {parser.main_count}.")
    if parser.h1_count != 1:
        errors.append(f"Expected exactly one h1 element; found {parser.h1_count}.")
    if DOCUMENT_OVERFLOW.search(source):
        warnings.append("Document-level overflow:hidden may mask clipping instead of fixing reflow.")

    # Only flag dimming when the page actually ships a script; without one the
    # A step dimmed by default is invisible when JS never runs. Strip comments
    # first so documentation quoting the bad pattern is not itself flagged.
    scan = HTML_COMMENT.sub("", source)
    dimmed = steps_dimmed_by_default(scan)
    if dimmed and "<script" not in scan.lower():
        errors.append(
            "A .stage-step is dimmed by default but the page has no script to "
            "reveal it: with JavaScript disabled the step stays invisible. "
            "Default steps to opacity:1 and let the script opt into the dimmed state."
        )
    elif dimmed:
        warnings.append(
            "A .stage-step is dimmed by default. Verify that the script arms it "
            "only after load, and that steps stay readable when JS is disabled."
        )

    return _deduplicate(errors), _deduplicate(warnings)


def _deduplicate(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Standalone HTML artifact to inspect")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    try:
        errors, warnings = analyze_html(args.path)
    except (OSError, UnicodeError) as error:
        print(f"[ERROR] Could not read {args.path}: {error}")
        return 1

    for item in errors:
        print(f"[ERROR] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    if errors or (args.strict and warnings):
        return 1

    print(f"[PASS] {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
