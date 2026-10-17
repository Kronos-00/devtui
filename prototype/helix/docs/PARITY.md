# Migration parity and evidence

The authoritative item-by-item inventory is [MAIN_FEATURE_AUDIT.md](MAIN_FEATURE_AUDIT.md), with machine-readable data in [feature-audit.json](feature-audit.json). It is derived from the frozen `main` files in [main-baseline.json](main-baseline.json), not from recollection or package names alone.

## Status terminology

- **Implemented**: the feature has an identified code/configuration path in the Helix edition.
- **Automated regression covered**: representative semantics have assertions on terminal cells, disk contents, OSC 52 output, process state or protocol results in the bundled suites.
- **Reused component**: existing pinned Zellij/Lazygit/Helix infrastructure is reused instead of reimplemented.
- **Host/project dependent**: terminal key reporting, clipboard permission, compiler flags, build databases, language-server capability and debug permissions are prerequisites, not something an editor can certify for every project.

The presence of a menu entry or a successful `cargo check` alone is not a functional pass. Final suite totals, source fingerprints and publication validation are in [VALIDATION.md](VALIDATION.md).

## Explicit scope boundaries

This is migration of the portable additions/configuration in Neovim devtui, with known semantic mismatches corrected against [VS Code source](VSCODE_REFERENCES.md). It is not the entire VS Code product, the Vim command language, or every installed extension. The physical terminal UI remains character-cell based. Custom SDK paths and device-specific compatibility shims are not included.

Persistent regions, modal `i`/`Esc`, session Ctrl-Q, Alt-G, alternate tree Alt-click, visible ignored files and root-relative `.` are retained user choices. Terminal plaintext paste cannot preserve VS Code-private rich clipboard metadata. Named document marks retain navigation/overview behavior without importing Vim Shada files. Tree drag/drop moving and multi-selected tab actions were not part of the Neovim custom baseline.

## Main areas

Editor/Preview/Pinned/Untitled lifecycle; persistent Explorer and safe file operations; multi-selection and native per-keystroke edits; mouse/keyboard context actions; search/replace/navigation; clipboard/IPC; Git workspace; scrollbar and annotations; language/debug integration; isolated deployment. All are mapped individually in the audit, including source and test links. The audit is intended to remain maintainable when further differences are reported, not to assert that no possible edge case can exist.
