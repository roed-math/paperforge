"""Portable post-build work (Python replacements for shell that was
BSD-only: in-place seds, rsync, perl). ``web`` patches the built pages;
``site`` assembles the project site. Every transformation detects its
expected upstream pattern, is idempotent, and reports honestly: 'already
applied', 'applied', or an error when PreTeXt's emitted output no longer
matches expectations — never silently shipping unpatched output."""
