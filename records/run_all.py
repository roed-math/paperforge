#!/usr/bin/env python3
"""Run the records/cost pipelines end to end, gated on config presence.

    python3 records/run_all.py [records-config.json]
    python3 records/run_all.py [config] --validate   # also run the instance's
                                                     # ground-truth validation
    python3 records/run_all.py [config] --force      # publish past audit findings

Stages (each optional — skipped when its config block is absent):
 1. ledger.py            "categories"          per-session token ledger
 2. corpus.py            "cleanup_corpus"      sanitized corpus + archive + audit
 3. (pause) if work/cleanup/audit-report.txt is non-empty, print it and stop
    unless --force: findings need human review before publication.
 4. research_archive.py  "research_archives"   frozen record bundles
 5. apply_site.py        "apply_site"          dashboard data/content/cost pages
 6. check_site.py        "check_site"          consistency checks (nonzero on fail)

--validate additionally runs the instance's own validation script (config
"validate_script", a path relative to the pipeline home — e.g. gq2's
validate_formalization.py, which re-derives the 20 published records).
"""
import os
import subprocess
import sys

from _config import load

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, config_path):
    print("== %s" % script)
    subprocess.check_call([sys.executable, os.path.join(HERE, script),
                           config_path])


def main():
    argv = sys.argv[1:]
    rc = load(argv)
    cp = rc.config_path

    if rc.get("categories"):
        run("ledger.py", cp)
    if rc.get("cleanup_corpus"):
        run("corpus.py", cp)
        audit = os.path.join(rc.work, "cleanup", "audit-report.txt")
        if os.path.getsize(audit) > 0 and "--force" not in argv:
            sys.stderr.write(
                "\naudit-report.txt has findings that need human review:\n\n")
            sys.stderr.write(open(audit).read())
            sys.stderr.write(
                "\nResolve them (edit exclusions.json / extend the sanitize "
                "config), or re-run with --force to publish anyway.\n")
            sys.exit(2)
    if rc.get("research_archives"):
        run("research_archive.py", cp)
    if rc.get("apply_site"):
        run("apply_site.py", cp)
    if rc.get("check_site"):
        run("check_site.py", cp)
    if "--validate" in argv and rc.get("validate_script"):
        script = os.path.join(rc.records_dir, rc["validate_script"])
        print("== %s" % script)
        subprocess.check_call([sys.executable, script])
    print("\npipeline complete")


if __name__ == "__main__":
    main()
