"""CI gate: run every validator, print findings, exit non-zero on any error.

    python -m paperforge_validators.run_all [instance_root]

Warnings do not fail the build; errors do. Stub validators emit a warning so the
report honestly shows which checks are not yet active.
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import Finding, load_config
from . import (
    lean_links,
    section_summaries,
    directives,
    notation_order,
    references,
    plagiarism,
)

CHECKS = [
    lean_links,
    section_summaries,
    directives,
    notation_order,
    references,
    plagiarism,
]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(argv[0]) if argv else Path.cwd()
    config = load_config(root)

    findings: list[Finding] = []
    for mod in CHECKS:
        try:
            findings.extend(mod.check(config))
        except Exception as e:  # a broken validator must not hide the others
            findings.append(Finding(mod.__name__.split(".")[-1], "error",
                                    f"validator crashed: {e!r}"))

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    for f in errors + warnings:
        print(f)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
