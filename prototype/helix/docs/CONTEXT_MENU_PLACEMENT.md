# Pointer-anchored context menus

Explorer, editor-symbol and selection right-click menus now use the triggering
mouse position. Their previous Select component centered every menu and the
context requests discarded the mouse coordinates.

## Behavior and source alignment

Mouse coordinates travel explicitly in each context request, and only the
corresponding Select receives that anchor. Normal confirmations remain dialogs;
keyboard requests do not retain an old pointer position.

Placement follows the default vertical rules in VS Code `layout2d`: prefer
below the anchor with its left edge aligned to the pointer, flip above or left
when the menu fits there, and overlap within the viewport if neither side has
enough space. A terminal mouse anchor is normalized to one cell. A resized
viewport clamps an existing anchor to its new visible bounds before layout.
These are terminal-cell semantics, not a claim of GUI pixel equivalence.

The menu is re-laid out when the viewport changes. Its list receives the actual
remaining height after the title so all actions remain reachable by scrolling
in a short terminal. Right-clicking outside an open context menu dismisses it
and dispatches the same press to the new target; right-clicking inside does not
execute an action. The opening release cannot activate the default action.

Pinned VS Code revision: `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`.
Relevant sources are `layout.ts`, its `range.ts` dependency, `contextview.ts`,
editor `contextmenu.ts` and platform `contextMenuHandler.ts`. Their exact paths,
URLs and hashes are in [vscode-reference-manifest.json](vscode-reference-manifest.json).

## Executable evidence

`vscode_context_menu_oracle.mjs` executes the upstream TypeScript layout and
range code directly after hash verification. It does not reimplement the layout
algorithm. The 14 fixtures cover top/middle/bottom locations, both horizontal
edges, selection menus, live resize, constrained height and context retargeting.

Real PTY checks compare the rendered rectangle with those fixtures, then click
menu items to verify their actual target and clipboard result. Other checks
preserve multiple selections, dismiss menus without residual frames and keep
permanent-delete confirmations independent of the pointer anchor. There are
8 methods and 16 case combinations in the new suite.

## Release validation

All 38 patches were applied to a fresh pinned upstream checkout. The canonical
source tree was verified before an offline, locked Release build. The installed
binary matches that build; the runtime sources are unchanged.

| Installed-binary suite | Methods | Result |
| --- | ---: | --- |
| Pointer context menus | 8 | PASS |
| Terminal interaction | 31 | PASS |
| Strict parity | 38 | PASS |
| Permanent deletion | 9 | PASS |
| Unicode column selection | 8 | PASS |
| Total | 94 | PASS |

The pointer suite covers 16 case combinations, including all 14 source-derived
geometry fixtures. The Unicode suite retains its 96 case combinations. The
feature manifest also passes with 160 checkpoints and 35 source references.
Exact test methods, durations, patch hashes and build fingerprints are recorded
in [context-menu-results.json](context-menu-results.json).

Installed source tree: `81f8c9ff70c9eca7b1be3018ea06e29347f15cae`.
Binary SHA-256: `6c6054f20c680ed8724be3e2a730241b8a400b83deacbf9b25a00b66e94ac2df`.

Restart `devtui-helix` to use the updated binary. Existing sessions continue
running their previous process.
