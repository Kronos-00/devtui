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

## What this does not validate

The prototype does not claim parity for the persistent Explorer, Preview/Pinned tabs, bufferline mouse controls, dirty-close dialog, editor scrollbar, project Replace UI, inactive-region extension, or running-editor IPC. Those remain explicit follow-up items in `ASSESSMENT.md`.
