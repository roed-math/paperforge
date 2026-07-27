"""paperforge build {web,arxiv,site}: deterministic build orchestration.

Encodes the required stage order in Python (review §12) instead of copied
shell scripts; postprocessing is portable (no BSD sed) and idempotent;
optional stages report WHY they were skipped; every build writes
output/build-provenance.json and never blocks on a dirty tool checkout.
"""
from __future__ import annotations

import shutil
import subprocess

from ..config import ConfigError
from ..provenance import short_stamp, write_provenance
from ..state import candidate_declmap
from . import _stages as st
from ..postprocess import web as ppweb
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("build", help="build the paper (web/arxiv/site)")
    p.add_argument("target", choices=["web", "arxiv", "site"])
    add_instance_arg(p)
    p.add_argument("--plan", action="store_true",
                   help="print the stage plan without changing files")
    p.add_argument("--pdf", action="store_true",
                   help="arxiv: also run latexmk on the generated LaTeX")
    p.set_defaults(func=run)


def _guard_accepted_maps(cfg) -> str | None:
    for fm in cfg.formalizations:
        if not fm.declmap.is_file():
            cand = candidate_declmap(fm.declmap)
            if cand.is_file():
                return (f"no accepted declaration map for {fm.name!r} at "
                        f"{fm.declmap.relative_to(cfg.root)}.\n"
                        f"A candidate exists at {cand.relative_to(cfg.root)} — "
                        f"review and `paperforge accept lean-decl-map`"
                        + ("" if fm.primary
                           else f" --formalization {fm.name}")
                        + ", or remove the formalization from paper.toml to "
                          "build without badges.")
            return (f"no declaration map for {fm.name!r} — run "
                    f"`paperforge ingest --bootstrap` first, or remove the "
                    f"formalization from paper.toml")
    return None


def build_web(cfg, plan: bool) -> int:
    if not plan and not cfg.draft.is_file():
        return fail(f"draft not found at {cfg.draft} — put the LaTeX draft "
                    f"in place (paper.toml [inputs] ai_draft), then "
                    f"`paperforge ingest --bootstrap`")
    msg = None if plan else _guard_accepted_maps(cfg)
    if msg:
        return fail(msg)
    r = st.Runner(plan_only=plan)
    raw = cfg.raw
    subs = raw.get("build", {}).get("web_substitutions", [])
    try:
        r.run("trust table", lambda: st.trust_table(cfg),
              skip=None if raw.get("trust_table") else "not configured")
        r.run("ingest draft", lambda: st.tex2ptx(cfg))
        r.run("author metadata", lambda: st.author_metadata(cfg))
        r.run("axiom census", lambda: st.lean_axioms(cfg),
              skip=None if cfg.formalizations else "no formalization configured")
        r.run("trust drift gate", lambda: st.trust_check(cfg),
              skip=None if raw.get("trust_table") else "not configured")
        r.run("notation far marks", lambda: st.notation_far(cfg))
        r.run("prose term links", lambda: st.prose_terms(cfg),
              skip=None if raw.get("notation", {}).get("prose_map")
              else "no prose map configured")
        r.run("pretext build web", lambda: st.pretext_build(cfg, "web"))
        r.run("mathjax lazy", lambda: ppweb.patch_mathjax_lazy(cfg.web_output))
        r.run("mathjax macros", lambda: st.mathjax_macros(cfg))
        r.run("toc default-open",
              lambda: ppweb.open_toc_by_default(cfg.web_output))
        r.run("html substitutions",
              lambda: ppweb.apply_substitutions(cfg.web_output, subs),
              skip=None if subs else "none configured")
        r.run("hover registries", lambda: st.registries(cfg))
        r.run("ui bundle",
              lambda: ppweb.assemble_bundle(cfg.root, cfg.web_output))
        r.run("assets", lambda: ppweb.copy_assets(cfg.root, cfg.web_output))
        r.run("provenance",
              lambda: str(write_provenance(cfg.web_output.parent, cfg.root,
                                           cfg.schema).name),
              skip="plan" if plan else None)
    except st.StageError as e:
        return fail(str(e))
    if not plan:
        print(f"\nWeb build complete: {cfg.web_output} "
              f"(paperforge {short_stamp()})")
    return 0


def build_arxiv(cfg, plan: bool, pdf: bool) -> int:
    r = st.Runner(plan_only=plan)
    try:
        r.run("pretext build arxiv", lambda: st.pretext_build(cfg, "arxiv"))
        out = cfg.root / "output" / "arxiv"
        if pdf:
            def latexmk() -> str:
                if not shutil.which("latexmk"):
                    raise RuntimeError("latexmk not installed")
                subprocess.run(["latexmk", "-pdf",
                                "-interaction=nonstopmode", "main.tex"],
                               cwd=out, check=True,
                               stdout=subprocess.DEVNULL)
                return "main.pdf"
            r.run("latexmk", latexmk)
        r.run("provenance",
              lambda: str(write_provenance(out.parent, cfg.root,
                                           cfg.schema).name),
              skip="plan" if plan else None)
    except st.StageError as e:
        return fail(str(e))
    return 0


def build_site(cfg, plan: bool) -> int:
    """Delegate to the instance's build-site script when it exists (the
    exercised path); a Python port of site assembly is deliberately not
    duplicated here yet."""
    script = cfg.root / "scripts" / "build-site.sh"
    if not script.is_file():
        return fail("no scripts/build-site.sh — site assembly is optional; "
                    "scaffold it from <paperforge>/templates/build-site.sh "
                    "(see docs/DEPLOYMENT.md)")
    if plan:
        print(f"would run: {script}")
        return 0
    try:
        subprocess.run(["bash", str(script)], cwd=cfg.root, check=True)
    except subprocess.CalledProcessError as e:
        return fail(f"build-site failed (exit {e.returncode})")
    write_provenance(cfg.root / "output", cfg.root, cfg.schema)
    return 0


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        return fail(str(e))
    if args.target == "web":
        return build_web(cfg, args.plan)
    if args.target == "arxiv":
        return build_arxiv(cfg, args.plan, args.pdf)
    return build_site(cfg, args.plan)
