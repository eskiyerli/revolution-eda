# `scripts/generate_devdocs.py`

**Module:** `scripts.generate_devdocs`

## Purpose

This generator — rebuilds the developmentDocs vault from the sources.

## Module docstring

Generate the developmentDocs Obsidian vault.

Walks the Python sources, extracts module docstrings / classes / functions /
internal imports via AST, and emits one Markdown note per file plus per-package
index notes. Links are path-qualified Obsidian wikilinks so they resolve
unambiguously even for files that share a basename.

Re-run after structural changes:  poetry run python scripts/generate_devdocs.py
Hand-written notes (Home.md, Architecture.md, DataFormats.md) are NOT touched.

## Functions

- `dottedName()`
- `notePath()` — Vault-relative note path for a source file.
- `wikiLink()`
- `mdText()` — Normalize RST-style markup in docstrings/purposes to Markdown.
- `teaser()` — First-clause teaser for index listings, without mid-word cuts.
- `extract()`
- `collectSources()`
- `main()`
