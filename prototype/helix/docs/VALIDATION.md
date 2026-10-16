# Prototype validation

The prototype is pinned to the Helix commit in `HELIX_COMMIT`.

## Source/build validation

- The middle-drag patch applies cleanly to a detached clean worktree of the pinned commit.
- `cargo check -p helix-term --bin hx` passes with Rust 1.95.0.
- `cargo build -p helix-term --bin hx` passes with Rust 1.95.0.
- `cargo build --release -p helix-term --bin hx` passes with Rust 1.95.0.
- The prototype `config.toml` loads successfully and reports `termcode` as the clipboard provider.

## End-to-end multi-selection test

A PTY test opened this file:

```text
aaaaaa
bbbbbb
cccccc
```

The test then sent real SGR terminal mouse events:

1. middle-button press on line 1;
2. middle-button drag to line 3 at the same screen column;
3. middle-button release;
4. `i` to enter Insert mode;
5. type `X`;
6. press Right while still in Insert mode;
7. type `Y`;
8. save and quit.

The saved file was:

```text
XaYaaaaa
XbYbbbbb
XcYccccc
```

This verifies the critical architectural goal: the mouse patch creates native Helix selections, typed characters update every selection immediately, and Insert-mode cursor movement acts on all selections without replay-on-Escape behavior.

## Picker and editor mouse test

The prototype also validates the initial Helix file-explorer overlay with real SGR mouse events:

- left-clicking a picker row updates the selected item and preview;
- mouse wheel moves the picker selection by three entries;
- double-clicking a row opens it and closes the overlay;
- clicking the preview opens the current selection and closes the overlay;
- after a file is open, left-clicking the actual editor text moves the real Helix cursor.

PTY verification opened `a.txt` by double-click and changed `AAAA` to `DAAAA`; a wheel step selected `03.txt` and changed `F03` to `SF03`; editor text clicking moved the insertion point inside `0123456789ABCDEFGHIJ`, producing `0123456Q789ABCDEFGHIJ`.

## Broader parity validation

Subsequent migration commits added and separately regression-tested the persistent Explorer, Preview/Pinned lifecycle, bufferline mouse controls, dirty-close/Save As flow, Explorer file actions and multi-selection, editor scrollbar, current-file and project Replace UI, inactive-region protocol handling, and running-editor IPC. Save As accepts the entered path on the first Enter instead of letting filename completion consume the confirmation. The authoritative current matrix is `PARITY.md`; this file preserves the original PTY evidence for the prototype's core multi-selection and mouse assumptions.
