"""paperforge init: deterministic instance scaffolding (review §5-P0).

Everything judgment-free that skills/paper-init used to narrate happens
here, testably: copy the scaffold, fill placeholders, create every sidecar
the build assumes (valid and empty), write a conservative .gitignore and a
minimal paper.toml, keep machine-local values out of committed files, leave
no @@PLACEHOLDER@@ markers, self-check, and print the next commands. The
agent skill wraps this command and keeps only the judgment work.

Machine-local core-XSL handling: the committed conversions import
xsl/core-local/{html,latex,latex-classic}.xsl — one-line, GITIGNORED shims
this command (re)generates to point at the machine's installed PreTeXt
core. Committed files never carry machine paths.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .. import tool_root
from ..config import LOCAL_CONFIG_NAME
from ._common import fail

_SIDECARS: dict[str, str] = {
    "notation/notation-map.json": "{}\n",
    "notation/disambiguation.json": "{}\n",
    "references/bib-labels.json": "{}\n",
    "references/bib-aliases.json": "{}\n",
    "crosswalk/lean-annotations.json": '{"annotations": {}}\n',
    "references/extra-biblio.xml": (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!-- Bibliography additions merged into <references> at ingest\n"
        "     (paperforge docs/REFERENCES.md); one <biblio> child per\n"
        "     entry, provenance in references/PROVENANCE.md. -->\n"
        "<references-extra>\n</references-extra>\n"),
}

_DIRS = [
    "inputs/draft", "content/insertions", "crosswalk", "notation",
    "references", "style-corpus", "directives/applied", "scripts",
]

_GITIGNORE = """\
output/
.cache/
__pycache__/
*.egg-info/
vendor/
logs/
.DS_Store
._*
*~

# Machine-local configuration + core-XSL shims (paperforge init/doctor
# regenerate these; committed files carry no machine paths)
.paperforge.local.toml
xsl/core-local/

# LaTeX intermediates
*.aux
*.log
*.out
*.synctex.gz
*.fls
*.fdb_latexmk
"""

_SHIM_BUILD_WEB = """\
#!/usr/bin/env bash
set -euo pipefail
exec python3 -m paperforge build web "$(cd "$(dirname "$0")/.." && pwd)" "$@"
"""

_SHIM_BUILD_SITE = """\
#!/usr/bin/env bash
set -euo pipefail
exec python3 -m paperforge build site "$(cd "$(dirname "$0")/.." && pwd)" "$@"
"""

#: committed XSL -> (placeholder it carries, gitignored local shim, core file)
_XSL_WIRING = {
    "custom-html.xsl": ("@@PRETEXT_CORE_XSL@@",
                        "core-local/html.xsl", "pretext-html.xsl"),
    "print-latex.xsl": ("@@PRETEXT_CORE_LATEX_XSL@@",
                        "core-local/latex.xsl", "pretext-latex.xsl"),
    "arxiv-latex.xsl": ("@@PRETEXT_CORE_LATEX_CLASSIC_XSL@@",
                        "core-local/latex-classic.xsl",
                        "pretext-latex-classic.xsl"),
}


def add_parser(sub) -> None:
    p = sub.add_parser("init", help="scaffold a new instance (deterministic)")
    p.add_argument("path", nargs="?", default=".", metavar="PATH")
    p.add_argument("--title", default="Title of the paper")
    p.add_argument("--slug", default=None,
                   help="short identifier (default: the directory name)")
    p.add_argument("--draft", default="inputs/draft/main.tex",
                   help="where the AI LaTeX draft will live")
    p.add_argument("--lean-root", default=None,
                   help="path to the Lean project (omit or --no-lean for none)")
    p.add_argument("--lean-project-name", default=None,
                   help="badge project name (default: basename of --lean-root)")
    p.add_argument("--no-lean", action="store_true",
                   help="no formalization linkage for this paper")
    p.add_argument("--mathbb", default="", metavar="LETTERS",
                   help="restyle \\mathbf X -> \\mathbb{X} for these letters")
    p.add_argument("--detail-default", type=int, default=1)
    p.add_argument("--detail-max", type=int, default=3)
    p.add_argument("--pretext-core-xsl", default=None,
                   help="path to the installed pretext-html.xsl "
                        "(default: newest under ~/.ptx/*/core/xsl)")
    p.add_argument("--site", action="store_true",
                   help="also scaffold the project-site build script")
    p.add_argument("--force", action="store_true",
                   help="scaffold into a non-empty directory")
    p.add_argument("--non-interactive", action="store_true",
                   help="never prompt; use flag values and defaults")
    p.set_defaults(func=run)


def discover_core_xsl() -> Path | None:
    hits = sorted(Path.home().glob(".ptx/*/core/xsl/pretext-html.xsl"))
    if hits:
        return hits[-1]
    # fresh machine: the pretext wheel materializes its core on demand
    try:
        import pretext.resources as resources
        resources.install()
        candidate = Path(resources.resource_base_path()) / "core" / "xsl" \
            / "pretext-html.xsl"
        if candidate.is_file():
            return candidate
    except Exception:  # noqa: BLE001 — no pretext, or a changed API
        pass
    return None


def write_core_shims(root: Path, core_html: Path) -> list[str]:
    """(Re)generate xsl/core-local/*.xsl pointing at the machine's core.
    Returns warnings for missing core siblings."""
    warnings = []
    shim_dir = root / "xsl" / "core-local"
    shim_dir.mkdir(parents=True, exist_ok=True)
    for _, (_, shim_rel, core_name) in _XSL_WIRING.items():
        core = core_html.parent / core_name
        if not core.is_file():
            warnings.append(f"core XSL sibling missing: {core}")
        (root / "xsl" / shim_rel).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<!-- GENERATED machine-local shim (gitignored): regenerate with\n"
            "     `paperforge init` / `paperforge doctor`. -->\n"
            '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" '
            'version="1.0">\n'
            f'  <xsl:import href="{core}"/>\n'
            "</xsl:stylesheet>\n")
    return warnings


def _paper_toml(a, slug: str, lean_root: str | None, lean_name: str | None) -> str:
    lines = [
        "# paperforge instance config — the annotated catalogue of every knob",
        "# lives in <paperforge>/templates/paper.toml; docs/CONFIGURATION.md",
        "# documents the semantics. Machine-local values (the PreTeXt core",
        f"# XSL path) belong in {LOCAL_CONFIG_NAME}, not here.",
        "",
        "[paperforge]",
        "instance_schema = 1",
        "",
        "[paper]",
        f'title = "{a.title}"',
        f'slug = "{slug}"',
        f'document_id = "{slug}"',
        "",
        "[inputs]",
        f'ai_draft = "{a.draft}"',
        "",
    ]
    if lean_root:
        lines += [
            "[formalizations.primary]",
            f'name = "{lean_name}"',
            f'root = "{lean_root}"',
            '# module = "TopModuleDir"      # census/docs subset inside root',
            '# docs_root = "../lean/"       # deployed docs URL prefix',
            f'declmap = "crosswalk/lean-decl-map.json"',
            "",
        ]
    lines += [
        "[ingest]",
        f'mathbb_letters = "{a.mathbb}"',
        'numbering_profile = "amsart-shared-section-theorems-global-equations"',
        "# authors = [\"Jane Doe|Dept|University\", \"@draft\"]",
        "# [[ingest.literal_rewrites]]     # structural draft macros",
        '# from = "\\\\MyMacro"',
        '# to = "\\\\cref{prop:target}"',
        "",
        "[style]",
        'corpus = "style-corpus/"',
        'advice = "style-corpus/ADVICE.md"',
        "",
        "[references]",
        'pdf_dir = "references/"',
        'bib = "source/references.ptx"',
        'labels = "references/bib-labels.json"',
        "",
        "[notation]",
        "far_words = 1500",
        "near_hover_delay_ms = 200",
        "far_hover_delay_ms = 500",
        "defsite_highlight_delay_ms = 120",
        "",
        "[detail]",
        f"default_level = {a.detail_default}",
        f"max_level = {a.detail_max}",
        "",
        "[plagiarism]",
        "ngram = 7",
        "error_run = 12",
        'sources = ["references/"]',
        "",
        "[build]",
        'web_output = "output/web"',
        'print_output = "output/print"',
        "",
        "[site]",
        'dir = "web-assets/site"',
    ]
    return "\n".join(lines) + "\n"


def run(args, extra) -> int:
    target = Path(args.path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    existing = [p.name for p in target.iterdir() if p.name != ".git"]
    if existing and not args.force:
        return fail(f"{target} is not empty ({', '.join(sorted(existing)[:5])}"
                    f"{', ...' if len(existing) > 5 else ''}) — pass --force "
                    f"to scaffold anyway (existing files are never overwritten)")

    slug = args.slug or target.name
    lean_root = None if args.no_lean else args.lean_root
    lean_name = None
    if lean_root:
        lean_name = args.lean_project_name or Path(lean_root).name
    elif not args.no_lean and not args.non_interactive and sys.stdin.isatty():
        answer = input("Lean project path (empty for none): ").strip()
        if answer:
            lean_root = answer
            lean_name = args.lean_project_name or Path(answer).name

    core = (Path(args.pretext_core_xsl).expanduser()
            if args.pretext_core_xsl else discover_core_xsl())

    template = tool_root() / "pretext-template"
    copied, skipped = [], []

    def copy(rel_src: str, rel_dst: str | None = None) -> None:
        src = template / rel_src
        dst = target / (rel_dst or rel_src)
        if dst.exists():
            skipped.append(str(dst.relative_to(target)))
            return
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        copied.append(str(dst.relative_to(target)))

    for item in ("source", "xsl", "publication", "content", "web-assets",
                 "project.ptx"):
        copy(item)

    for rel in _DIRS:
        (target / rel).mkdir(parents=True, exist_ok=True)
    for rel, content in _SIDECARS.items():
        p = target / rel
        if not p.exists():
            p.write_text(content)
            copied.append(rel)

    # committed XSLs import the gitignored machine-local shims
    for xsl_name, (placeholder, shim_rel, _) in _XSL_WIRING.items():
        f = target / "xsl" / xsl_name
        if f.is_file():
            f.write_text(f.read_text().replace(placeholder, shim_rel))
    warnings = []
    if core and core.is_file():
        warnings += write_core_shims(target, core)
        local = target / LOCAL_CONFIG_NAME
        if not local.exists():
            local.write_text(
                "# Machine-local paperforge values (gitignored).\n"
                "[build]\n"
                f'pretext_core_xsl = "{core}"\n')
            copied.append(LOCAL_CONFIG_NAME)
    else:
        warnings.append(
            "no installed PreTeXt core XSL found — install pretext, run a "
            "first `pretext build` once (it fetches the core), then "
            "`paperforge doctor` regenerates xsl/core-local/")

    # remaining scaffold placeholders that have config-independent values
    html_xsl = target / "xsl" / "custom-html.xsl"
    if html_xsl.is_file():
        text = html_xsl.read_text()
        text = text.replace("@@LEAN_DOCS_ROOT@@", "../lean/")
        text = text.replace("@@LEAN_DEFAULT_PROJECT@@", lean_name or "")
        html_xsl.write_text(text)

    if not (target / "paper.toml").exists():
        (target / "paper.toml").write_text(
            _paper_toml(args, slug, lean_root, lean_name))
        copied.append("paper.toml")
    if not (target / ".gitignore").exists():
        (target / ".gitignore").write_text(_GITIGNORE)
        copied.append(".gitignore")

    shims = {"scripts/build-web.sh": _SHIM_BUILD_WEB}
    if args.site:
        shims["scripts/build-site.sh"] = _SHIM_BUILD_SITE
    for rel, content in shims.items():
        p = target / rel
        if not p.exists():
            p.write_text(content)
            p.chmod(0o755)
            copied.append(rel)

    # ---- self-checks: no placeholders, sidecars parse
    problems = []
    for f in list(target.rglob("*.xsl")) + list((target / "scripts").glob("*")) \
            + [target / "project.ptx", target / "paper.toml"]:
        if f.is_file() and "@@" in f.read_text(errors="ignore"):
            problems.append(f"unresolved placeholder in {f.relative_to(target)}")
    for rel in _SIDECARS:
        if rel.endswith(".json"):
            try:
                json.load(open(target / rel))
            except Exception as e:  # noqa: BLE001 — report whatever broke
                problems.append(f"{rel} does not parse: {e}")
    try:
        from ..config import load_instance
        load_instance(target)
    except Exception as e:  # noqa: BLE001
        problems.append(f"paper.toml does not load: {e}")

    print(f"scaffolded {target}")
    print(f"  created: {len(copied)} paths"
          + (f"; left untouched: {len(skipped)}" if skipped else ""))
    for w in warnings:
        print(f"  WARN: {w}")
    for p in problems:
        print(f"  ERROR: {p}")
    if problems:
        return 1
    print("\nNext:")
    print(f"  1. put the LaTeX draft at {args.draft}")
    print("  2. drop prior papers under style-corpus/ and cited PDFs under references/")
    print("  3. paperforge doctor")
    print("  4. paperforge ingest --bootstrap")
    return 0
