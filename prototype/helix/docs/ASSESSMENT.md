# Helix migration architecture assessment

The initial prototype verified that native Helix multiple selections could replace replay-on-Escape editing. Subsequent work implemented persistent workspace behavior and passed the acceptance suites documented in [VALIDATION.md](VALIDATION.md).

The migration is a maintained, pinned source patch set, not configuration alone. Responsibilities are separated into editor lifecycle, sidebar/file operations, terminal navigation, input/clipboard transactions, visual annotations, command/search UI, language services and deployment. `patches/series` defines the reproducible order.

The remaining maintenance cost is tracking upstream Helix APIs and maintaining terminal input compatibility. The actual added-function audit is [MAIN_FEATURE_AUDIT.md](MAIN_FEATURE_AUDIT.md); implementation scope and host-dependent boundaries are in [PARITY.md](PARITY.md). Existing Neovim devtui remains a separate, unchanged fallback.
