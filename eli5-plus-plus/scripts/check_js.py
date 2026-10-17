#!/usr/bin/env python3
"""Syntax-check every inline and local <script> in a standalone HTML artifact.

ELI5++ adds this because both parent skills asked for it in prose and neither
shipped a tool: a page can pass every static HTML check and still throw on load.

Uses `node --check` on a temporary .js file per script block. Remote scripts are
already rejected by check_html.py, so only inline and local blocks are checked.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


SKIP_TYPES = {
    "application/ld+json",
    "application/json",
    "text/template",
    "text/x-template",
    "importmap",
    "speculationrules",
}


class ScriptCollector(HTMLParser):
    """Collect inline script bodies and local script src paths."""

    def __init__(self, base: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.inline: list[tuple[int, str]] = []
        self.local_src: list[str] = []
        self._capturing = False
        self._buffer: list[str] = []
        self._skip = False
        self._line = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = {name.lower(): (value or "") for name, value in attrs}
        self._line = self.getpos()[0]

        script_type = attributes.get("type", "").strip().lower()
        if script_type in SKIP_TYPES:
            self._skip = True
            return

        src = attributes.get("src", "").strip()
        if src:
            if not src.startswith(("http://", "https://", "//", "data:")):
                self.local_src.append(src)
            self._skip = True
            return

        self._skip = False
        self._capturing = True
        self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script":
            return
        if self._capturing:
            body = "".join(self._buffer)
            if body.strip():
                self.inline.append((self._line, body))
        self._capturing = False
        self._skip = False
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)


def node_available() -> str | None:
    return shutil.which("node")


def check_with_node(node: str, source: str, label: str) -> str | None:
    """Return an error message, or None when the source parses."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        result = subprocess.run(
            [node, "--check", temp_path],
            capture_output=True,
            text=True,
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

    if result.returncode == 0:
        return None

    detail = (result.stderr or result.stdout).strip().splitlines()
    # Keep the diagnostic lines, drop the temp path and the Node stack frames.
    kept = [
        line.strip()
        for line in detail
        if temp_path not in line
        and not line.strip().startswith("at ")
        and not line.strip().startswith("Node.js v")
        and line.strip()
    ]
    message = " | ".join(kept[:3]) if kept else "unknown syntax error"
    return f"{label}: {message}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Standalone HTML artifact to check")
    args = parser.parse_args()

    path: Path = args.path
    if not path.is_file():
        print(f"[ERROR] Not a file: {path}")
        return 1

    node = node_available()
    if node is None:
        print("[ERROR] `node` not found on PATH; cannot syntax-check JavaScript.")
        print("        Install Node.js, or state explicitly that JS was not validated.")
        return 1

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"[ERROR] Could not read {path}: {error}")
        return 1

    collector = ScriptCollector(path.parent)
    collector.feed(source)
    collector.close()

    if not collector.inline and not collector.local_src:
        print(f"[PASS] {path} — no JavaScript to check")
        return 0

    errors: list[str] = []
    for line, body in collector.inline:
        problem = check_with_node(node, body, f"inline <script> at line {line}")
        if problem:
            errors.append(problem)

    for src in collector.local_src:
        target = (path.parent / src).resolve()
        if not target.is_file():
            errors.append(f"local <script src={src!r}>: file not found at {target}")
            continue
        problem = check_with_node(node, target.read_text(encoding="utf-8"), f"local script {src}")
        if problem:
            errors.append(problem)

    for item in errors:
        print(f"[ERROR] {item}")
    if errors:
        return 1

    total = len(collector.inline) + len(collector.local_src)
    print(f"[PASS] {path} — {total} script block(s) parsed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
