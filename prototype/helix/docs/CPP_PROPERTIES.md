# Workspace C/C++ configuration

The editor reads `.vscode/c_cpp_properties.json` automatically when starting
clangd. It translates the selected configuration into clangd compile commands
in memory. It does not generate or rewrite project configuration files.
Diagnostics, definition navigation, references and other clangd features use
these commands. Tree-sitter lexical highlighting remains independent of the
compiler configuration.

## Configuration selection and precedence

The configuration in the opened working directory governs files under that
workspace, including nested directories that contain another configuration.
When that directory has no configuration, the editor searches the opened
file's ancestors for the nearest owner. Files from external projects use a
separate server when their configuration differs.

By default, the selected entry is named `Linux`, `Mac` or `Win32` for the host
platform, falling back to the last entry. This follows the C/C++ extension's
initial selection. Its saved VS Code UI selection is not shared with Helix.
An exact name can be selected when launching:

```bash
DEVTUI_CPP_CONFIGURATION=Custom devtui-helix
```

A matching `compileCommands` entry takes precedence over manual compiler,
include, macro and standard fields. The editor preserves its arguments and
working directory. Files without a matching entry use the selected manual
configuration. Missing or invalid databases produce a warning and allow manual
fallback. A malformed properties file leaves the existing clangd configuration
available and reports a warning.

## Supported fields

| Field | clangd behavior |
| --- | --- |
| `compilerPath` | Compiler driver and exact query-driver allowlist |
| `compilerArgs` | Ordered compiler arguments |
| `defines` | Preprocessor definitions |
| `includePath` | Ordered include paths; trailing `/**` expands directories |
| `forcedInclude` | Forced header inclusion |
| `cStandard`, `cppStandard` | Language-specific standard |
| `intelliSenseMode` | x86/x64 bitness; other targets require compiler arguments |
| `macFrameworkPath` | Framework search paths |
| `compileCommands` | One database or an ordered list; first file match wins |
| Top-level `env` | String and array variable expansion |

JSON comments, trailing commas, UTF-8 BOMs, workspace variables, environment
variables and custom variables are supported. Expansion does not invoke a
shell. Compiler paths retain their driver spelling, including `clang++`
symlinks. Database `arguments` and POSIX-quoted `command` entries are supported.
Recursive includes do not follow directory symlinks and are bounded to avoid
unbounded scans. Configuration and database reads also have size bounds.

The existing clangd `.clangd` and user configuration remain active. A VS Code
`configurationProvider` extension cannot execute inside clangd; this is shown
as a warning, and database/manual configuration is used. VS Code settings
substitution and extension-specific IntelliSense engines are not emulated.

## Inspecting and reloading

Press `Space c i` to inspect Language Servers. The view shows the selected
configuration, source file, database entry count, current command source,
compiler and configuration warnings. After editing the configuration, run
`:lsp-restart` or restart the editor to reload it.

## Upstream references

The official [C/C++ settings reference](https://code.visualstudio.com/docs/cpp/customize-cpp-settings)
and [IntelliSense configuration guide](https://code.visualstudio.com/docs/cpp/configure-intellisense)
describe database precedence and manual fallback. The initial configuration
selection and JSONC schema were checked against the C/C++ extension source.
The in-memory command updates use clangd's
[protocol extension](https://clangd.llvm.org/extensions#compilation-commands).
Six pinned source files, revisions, URLs and SHA-256 hashes are recorded in
[cpp-properties-references.json](cpp-properties-references.json).

## Validation

The translator has 12 Rust unit tests. The new PTY suite has 14 methods, covering
configuration selection, first-parse protocol ordering, database precedence,
manual fallback, separate C/C++ standards, workspace boundaries, warnings,
existing settings and configuration reload. Real clangd cases verify that
macros select the expected definition target and that includes, forced headers
and standards produce no diagnostics in the controlled fixtures.

The read-only project audit checks exact database commands for C++ and CUDA,
and the manual configuration of an unmatched header. Only generic counts and
outcomes are recorded; project content and paths are not included.

Release build provenance and executed regression outcomes are recorded in
[cpp-properties-results.json](cpp-properties-results.json).

All 43 patches were applied to a fresh pinned upstream checkout, verified
against the canonical tree, and built as a locked offline Release. The installed
binary passed 126 application test methods, with 6 additional isolated deployment
checks, for 132 Python methods in total. The 12 translator Rust tests also passed.
The runtime sources are unchanged.

Installed source tree: `1668c00e3d78fa0f5dc8bd329c6664d330b5e101`.
Binary SHA-256: `74569f931ab1bcf6decd8f76321019421f783a688d649d3795bd359a2a417ae6`.

Restart `devtui-helix` to load the updated binary.
