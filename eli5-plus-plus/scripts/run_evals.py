#!/usr/bin/env python3
"""Mechanical checks for an ELI5++ artifact against an eval case's assertions.

This deliberately does NOT call an LLM. The community eval runners (e.g.
DreambigOu/ELI5) shell out to `claude -p` and then use another model to grade.
That works in Claude Code but not here, and an LLM grader that shares the
author's blind spots is weak evidence anyway.

So this runner checks only what is mechanically decidable, and prints the
remaining assertions as MANUAL — to be judged by a human reading the artifact.
Reporting "3 passed, 2 manual" is honest; reporting "5 passed" would not be.

Usage:
    python3 scripts/run_evals.py <artifact.html> --eval-id 0
    python3 scripts/run_evals.py <artifact.html> --eval-id 0 --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
EVALS_FILE = SKILL_DIR / "evals" / "evals.json"
CHECK_HTML = SKILL_DIR / "scripts" / "check_html.py"
CHECK_JS = SKILL_DIR / "scripts" / "check_js.py"
CHECK_GEOMETRY = SKILL_DIR / "scripts" / "check_geometry.py"


def load_eval(eval_id: int) -> dict:
    data = json.loads(EVALS_FILE.read_text(encoding="utf-8"))
    for case in data["evals"]:
        if case["id"] == eval_id:
            return case
    raise SystemExit(f"No eval with id={eval_id}")


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def check_static(artifact: Path) -> tuple[bool, str]:
    code, out = run([sys.executable, str(CHECK_HTML), "--strict", str(artifact)])
    return code == 0, out


def check_js(artifact: Path) -> tuple[bool, str]:
    code, out = run([sys.executable, str(CHECK_JS), str(artifact)])
    return code == 0, out


def check_geometry(artifact: Path) -> tuple[bool, str, int]:
    code, out = run([sys.executable, str(CHECK_GEOMETRY), str(artifact)])
    # 2 means "not measured", which is neither pass nor fail.
    return code == 0, out, code


def has_script(source: str) -> bool:
    return bool(re.search(r"<script\b(?![^>]*type=\"(?:application/ld\+json|application/json|importmap)\")", source, re.I))


def has_svg_with_name(source: str) -> bool:
    for match in re.finditer(r"<svg\b[^>]*>", source, re.I):
        tag = match.group(0)
        if re.search(r'aria-label\s*=\s*["\'][^"\']+', tag, re.I):
            return True
        if re.search(r'aria-labelledby\s*=\s*["\'][^"\']+', tag, re.I):
            return True
        if re.search(r'role\s*=\s*["\'](?:img|presentation|none)', tag, re.I):
            return True
        if re.search(r'aria-hidden\s*=\s*["\']true', tag, re.I):
            return True
        # look ahead for a <title> before the matching </svg>
        rest = source[match.end():]
        end = re.search(r"</svg>", rest, re.I)
        inner = rest[: end.start()] if end else rest
        if re.search(r"<title\b", inner, re.I):
            return True
    return False


def has_reduced_motion(source: str) -> bool:
    return bool(re.search(r"prefers-reduced-motion\s*:\s*reduce", source, re.I))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--eval-id", type=int, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    artifact: Path = args.artifact.resolve()
    if not artifact.is_file():
        print(f"[ERROR] artifact not found: {artifact}")
        return 1

    case = load_eval(args.eval_id)
    source = artifact.read_text(encoding="utf-8")

    static_ok, static_out = check_static(artifact)
    js_ok, js_out = check_js(artifact) if has_script(source) else (True, "no <script>")
    geo_ok, geo_out, geo_code = check_geometry(artifact)

    # Mechanical verdicts keyed by the phrases the assertions use.
    mechanical: list[dict] = []

    def add(name: str, passed: bool, evidence: str) -> None:
        mechanical.append({"check": name, "verdict": "PASS" if passed else "FAIL", "evidence": evidence})

    add("check_html --strict exits 0", static_ok, static_out.splitlines()[-1] if static_out else "")
    if has_script(source):
        add("check_js exits 0 (artifact has <script>)", js_ok, js_out.splitlines()[-1] if js_out else "")
    add(
        "geometry measured (exit 0, not 2)",
        geo_code == 0,
        "measured" if geo_code == 0 else ("NOT MEASURED — Playwright missing" if geo_code == 2 else "layout defects found"),
    )
    add("has inline <svg> with accessible name", has_svg_with_name(source), "scanned <svg> tags")
    add("has prefers-reduced-motion branch", has_reduced_motion(source), "searched CSS")

    manual = [
        a for a in case["assertions"]
        if not any(
            k in a.lower()
            for k in ("check_html", "check_js", "self-contained", "inline <svg>", "prefers-reduced-motion")
        )
    ]

    result = {
        "eval_id": case["id"],
        "eval_name": case["name"],
        "artifact": str(artifact),
        "mechanical": mechanical,
        "manual_assertions": manual,
        "geometry_status": {0: "measured", 1: "failed", 2: "not measured"}[geo_code],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all(m["verdict"] == "PASS" for m in mechanical) else 1

    print(f"Eval {case['id']}: {case['name']}")
    print(f"Artifact: {artifact.name}\n")
    print("— Mechanical —")
    for m in mechanical:
        print(f"  [{m['verdict']}] {m['check']}")
        if m["evidence"]:
            print(f"           {m['evidence'][:110]}")
    print("\n— Manual (must be judged by reading the artifact) —")
    for a in manual:
        print(f"  [ ] {a}")
    print("\n— Geometry —")
    if geo_code == 2:
        print("  NOT MEASURED: Playwright missing. Do not claim visual verification.")
    else:
        print(f"  {geo_out.splitlines()[-1] if geo_out else ''}")

    failed = [m for m in mechanical if m["verdict"] == "FAIL"]
    print(f"\n{len(mechanical) - len(failed)}/{len(mechanical)} mechanical passed, {len(manual)} manual pending")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
