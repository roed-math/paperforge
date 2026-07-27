"""Portable post-build mutations (Python replacements for the shell seds
that were BSD-only). Every transformation detects its expected upstream
pattern, is idempotent, and reports honestly: 'already applied', 'applied',
or an error when PreTeXt's emitted output no longer matches expectations —
never silently shipping unpatched output."""
