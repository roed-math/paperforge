"""paperforge validators: deterministic, CI-gating checks.

Every check is a callable ``check(config: dict) -> list[Finding]``. Checks never
mutate the source; they only report. ``run_all`` aggregates them and sets the exit
code. See ../../docs/ARCHITECTURE.md for the validator-vs-skill split.
"""
from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:      # Python < 3.11
    import tomli as tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    validator: str
    severity: str  # "error" | "warning"
    message: str
    location: str = ""  # xml:id, file path, or "file:line" when known

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.severity.upper()} ({self.validator}){loc}: {self.message}"


def load_config(root: Path | None = None) -> dict:
    """Load ``paper.toml`` from the instance root (defaults to cwd)."""
    root = Path(root or Path.cwd())
    with open(root / "paper.toml", "rb") as fh:
        data = tomllib.load(fh)
    data["_root"] = str(root)
    return data


def instance_root(config: dict) -> Path:
    return Path(config["_root"])


def formalization_roots(config: dict) -> dict[str, Path]:
    """Badge-project name -> local checkout, for both config generations.

    New shape (what ``paperforge init`` writes)::

        [formalizations.primary]
        name = "my-lean" ; root = "../my-lean"

    Old shape (the first instance)::

        [inputs]
        lean_project = "../my-lean"
        [inputs.formalizations.other]
        root = "formalizations/other"

    The primary project is also registered under ``""`` — badges with no
    ``project=`` attribute validate against it. An instance with no
    formalization returns an empty mapping, and the Lean checks skip.
    """
    base = instance_root(config)

    def _resolve(value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else base / p

    roots: dict[str, Path] = {}
    new = config.get("formalizations")
    if isinstance(new, dict) and new:
        # `primary` first, so it wins the "" default slot
        for key, rec in sorted(new.items(), key=lambda kv: kv[0] != "primary"):
            if not isinstance(rec, dict) or "root" not in rec:
                continue
            name = rec.get("name", key)
            roots[name] = _resolve(rec["root"])
            roots.setdefault("", roots[name])
        return roots

    inputs = config.get("inputs", {})
    primary = inputs.get("lean_project")
    if primary:
        path = _resolve(primary)
        name = inputs.get("lean_project_name") or path.name
        roots[name] = path
        roots[""] = path
    for name, rec in inputs.get("formalizations", {}).items():
        if isinstance(rec, dict) and "root" in rec:
            roots[name] = _resolve(rec["root"])
            roots.setdefault("", roots[name])
    return roots


def ptx_files(config: dict) -> list[Path]:
    """All PreTeXt source files of the instance."""
    src = instance_root(config) / "source"
    return sorted(src.rglob("*.ptx")) if src.exists() else []
