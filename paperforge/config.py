"""Normalized instance configuration.

Three layers, merged in order:

1. committed ``paper.toml`` (the instance's durable choices);
2. optional gitignored ``.paperforge.local.toml`` (machine-local values:
   the PreTeXt core XSL location, development overrides);
3. explicit CLI/environment overrides (handled by the commands).

The loader accepts BOTH config generations:

- the original shape (``[inputs] lean_project`` / ``lean_docs_base`` +
  ``[inputs.formalizations.<name>]`` for additional projects), still used
  by the first instance;
- the normalized shape (``[formalizations.<key>]`` records with ``name`` /
  ``root`` / ``module`` / ``docs_root`` / ``declmap`` / ``badge_cap``,
  the primary listed first via key ``primary``).

Old keys are normalized internally and recorded in ``deprecations`` —
surfaced by ``paperforge doctor`` and ``paperforge migrate config
--check``, deliberately not spammed on every build.

Every consumer should use the typed fields for identity/paths and may read
``raw`` for subsystem blocks the tool passes through untouched
([site], [trust_table], [validators], ...).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:      # Python < 3.11 (setup guards this anyway)
    import tomli as tomllib

from . import SUPPORTED_SCHEMAS
from .paths import resolve_instance_path

LOCAL_CONFIG_NAME = ".paperforge.local.toml"

#: The one numbering convention the simulator currently implements.
DEFAULT_NUMBERING_PROFILE = "amsart-shared-section-theorems-global-equations"


class ConfigError(Exception):
    """A configuration problem the user must fix (actionable message)."""


@dataclass(frozen=True)
class FormalizationConfig:
    name: str                    # badge project key (lean-proj-<name>, /lean/<name>/)
    root: Path                   # local checkout (resolved absolute)
    module: str | None           # top module dir (census/docs subset), if declared
    docs_root: str | None        # deployed docs URL prefix (URL-ish, NOT a path)
    declmap: Path                # accepted decl map (may not exist yet)
    badge_cap: int | None
    primary: bool


@dataclass(frozen=True)
class InstanceConfig:
    root: Path
    schema: int
    title: str
    slug: str
    document_id: str
    draft: Path
    formalizations: tuple[FormalizationConfig, ...]   # primary first (may be empty)
    mathbb_letters: str
    literal_rewrites: tuple[tuple[str, str], ...]      # (from, to) ingest rewrites
    numbering_profile: str
    authors: tuple[str, ...]     # tex2ptx --author specs ('Name|Affil|...', '@draft')
    web_output: Path
    print_output: Path
    pretext_core_xsl: Path | None    # machine-local when set
    raw: dict = field(repr=False)
    local: dict = field(repr=False)  # the machine-local layer, merged into raw
    deprecations: tuple[str, ...] = ()

    def path(self, value: str | Path) -> Path:
        return resolve_instance_path(self.root, value)

    def formalization(self, name: str | None = None) -> FormalizationConfig | None:
        if name is None:
            return self.formalizations[0] if self.formalizations else None
        for f in self.formalizations:
            if f.name == name:
                return f
        return None


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def find_instance_root(start: Path) -> Path | None:
    """The nearest ancestor (inclusive) containing paper.toml."""
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "paper.toml").is_file():
            return p
    return None


def load_instance(root: str | Path) -> InstanceConfig:
    root = Path(root).resolve()
    toml_path = root / "paper.toml"
    if not toml_path.is_file():
        raise ConfigError(
            f"no paper.toml at {root} — not a paperforge instance "
            f"(run `paperforge init` to create one)")
    raw = _load_toml(toml_path)
    local: dict = {}
    local_path = root / LOCAL_CONFIG_NAME
    if local_path.is_file():
        local = _load_toml(local_path)
        raw = _deep_merge(raw, local)

    deprecations: list[str] = []

    schema = raw.get("paperforge", {}).get("instance_schema", 1)
    if schema not in SUPPORTED_SCHEMAS:
        supported = ", ".join(str(s) for s in sorted(SUPPORTED_SCHEMAS))
        raise ConfigError(
            f"instance_schema {schema} is not supported by this paperforge "
            f"(supports: {supported}) — update the tool, or migrate the instance")

    paper = raw.get("paper", {})
    title = paper.get("title", "")
    slug = paper.get("slug") or paper.get("instance_name") or root.name
    if "instance_name" in paper and "slug" not in paper:
        deprecations.append("[paper] instance_name — rename to slug")
    document_id = paper.get("document_id") or slug

    inputs = raw.get("inputs", {})
    draft_val = inputs.get("ai_draft", "inputs/draft/main.tex")
    draft = resolve_instance_path(root, draft_val)

    # ---- formalizations: new shape first, else normalize the old one
    fms: list[FormalizationConfig] = []
    new_fms = raw.get("formalizations")
    if isinstance(new_fms, dict) and new_fms:
        ordered = sorted(new_fms.items(), key=lambda kv: kv[0] != "primary")
        for key, rec in ordered:
            fms.append(FormalizationConfig(
                name=rec.get("name", key),
                root=resolve_instance_path(root, rec["root"]),
                module=rec.get("module"),
                docs_root=rec.get("docs_root"),
                declmap=resolve_instance_path(
                    root, rec.get("declmap", "crosswalk/lean-decl-map.json")),
                badge_cap=rec.get("badge_cap"),
                primary=(key == "primary" or not fms),
            ))
    else:
        lp = inputs.get("lean_project")
        if lp:
            deprecations.append(
                "[inputs] lean_project / lean_docs_base — move to "
                "[formalizations.primary] (name/root/module/docs_root/declmap)")
            proot = resolve_instance_path(root, lp)
            fms.append(FormalizationConfig(
                name=inputs.get("lean_project_name") or proot.name,
                root=proot,
                module=inputs.get("lean_module"),
                docs_root=inputs.get("lean_docs_base"),
                declmap=resolve_instance_path(
                    root, "crosswalk/lean-decl-map.json"),
                badge_cap=None,
                primary=True,
            ))
        for name, rec in inputs.get("formalizations", {}).items():
            fms.append(FormalizationConfig(
                name=name,
                root=resolve_instance_path(root, rec["root"]),
                module=rec.get("module"),
                docs_root=rec.get("docs_root"),
                declmap=resolve_instance_path(
                    root, rec.get("declmap",
                                  f"crosswalk/lean-decl-map-{name}.json")),
                badge_cap=rec.get("badge_cap"),
                primary=False,
            ))
        if inputs.get("formalizations"):
            deprecations.append(
                "[inputs.formalizations.*] — rename the table to "
                "[formalizations.*]")

    ingest = raw.get("ingest", {})
    rewrites = tuple(
        (r["from"], r["to"]) for r in ingest.get("literal_rewrites", []))
    build = raw.get("build", {})
    core_xsl = build.get("pretext_core_xsl")

    return InstanceConfig(
        root=root,
        schema=schema,
        title=title,
        slug=slug,
        document_id=document_id,
        draft=draft,
        formalizations=tuple(fms),
        mathbb_letters=ingest.get("mathbb_letters", ""),
        literal_rewrites=rewrites,
        numbering_profile=ingest.get("numbering_profile",
                                     DEFAULT_NUMBERING_PROFILE),
        authors=tuple(ingest.get("authors", [])),
        web_output=resolve_instance_path(
            root, build.get("web_output", "output/web")),
        print_output=resolve_instance_path(
            root, build.get("print_output", "output/print")),
        pretext_core_xsl=(resolve_instance_path(root, core_xsl)
                          if core_xsl else None),
        raw=raw,
        local=local,
        deprecations=tuple(deprecations),
    )
