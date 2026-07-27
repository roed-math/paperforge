"""Shared config + path resolution for the records pipelines.

Every tool takes the instance's records config as an optional positional
argument (default: records-pipeline/config.json under the cwd). The config's
directory is the pipeline home: exclusions.json sits beside it and work/
(gitignored scratch) lives under it; the instance root is its parent, and
the dashboard tree defaults to web-assets/site/development under that
(override with the config's "site_dev_dir", instance-root-relative).

Pipelines are optional per instance: each stage runs only when its config
section exists ("categories" -> ledger, "cleanup_corpus" -> corpus,
"research_archives" -> research bundles, "apply_site" -> dashboard apply,
"check_site" -> dashboard checks).
"""
import json
import os


class RecordsConfig:
    def __init__(self, config_path):
        self.config_path = os.path.abspath(config_path)
        with open(self.config_path) as fh:
            self.cfg = json.load(fh)
        self.records_dir = os.path.dirname(self.config_path)
        self.root = os.path.dirname(self.records_dir)
        self.site_dev = os.path.normpath(os.path.join(
            self.root, self.cfg.get("site_dev_dir", "web-assets/site/development")))
        self.work = os.path.join(self.records_dir, "work")
        self.exclusions_path = os.path.join(self.records_dir, "exclusions.json")

    def __getitem__(self, key):
        return self.cfg[key]

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    @property
    def project_dirs(self):
        return [os.path.expanduser(p) for p in self.cfg["project_dirs"]]


def load(argv):
    """Resolve the config path from argv (first non-flag arg, else default)."""
    args = [a for a in argv if not a.startswith("-")]
    path = args[0] if args else os.path.join("records-pipeline", "config.json")
    return RecordsConfig(path)
