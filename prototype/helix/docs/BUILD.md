# Reproducible Helix source builds

`HELIX_COMMIT` identifies the unmodified upstream revision. `patches/series`
lists ordered, incremental patches. Do not apply a cumulative diff followed by
its component patches: that applies the same implementation twice.

Each patch has one responsibility (mouse, lifecycle, tree, file actions, IPC,
column editing, scrollbar, LSP, shortcuts, replace, language/debug services).
`apply-patches.sh` requires the pinned revision and a clean source tree, applies
the manifest with `git apply --index`, then verifies the resulting Git tree ID against `HELIX_TREE`. A mismatch
aborts the build before installation. Update `HELIX_TREE` together with an
intentional patch-series change, never to hide an unexplained mismatch.

`build-helix.sh` uses Cargo's lockfile, retains interrupted source checkouts,
installs the executable by atomic rename and writes `build-info.json` with the
upstream revision, final source-tree ID and SHA-256 of every applied patch.
No active editor is terminated by installation; restart the Helix session to
use the new executable. The Neovim launcher and configuration are not replaced.
