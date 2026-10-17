# Permanent Explorer deletion and terminal status geometry

## VS Code behavior

VS Code supports desktop trash. The Explorer uses it only if both
`files.enableTrash` is enabled and the selected resource's provider advertises
`FileSystemProviderCapabilities.Trash`. Otherwise the Delete key and context
menu use the permanent-delete handler and show the permanent-delete confirmation.
The remote server uses the Node disk provider, which does not advertise Trash.

Reviewed source at `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`:

- `explorerView.ts`: `onFocusChanged` updates `resourceMoveableToTrash` from
  configuration and file-service capability.
- `fileActions.contribution.ts`: routes the Delete key and context action using
  that context key.
- `fileActions.ts`: `deleteFiles`, permanent confirmation and failure handling.
- `remoteFileSystemProviderServer.ts` / Node `diskFileSystemProvider.ts`: remote
  provider construction and advertised capability set.

Pinned URLs and hashes are in [vscode-reference-manifest.json](vscode-reference-manifest.json).

## Reproduced failure

The previous terminal provider always invoked `gio trash`, independent of an
advertised trash capability. A disposable `gio` stub returned an unsupported
trash error ending in newlines. The error was copied verbatim into the bottom
status row. The terminal emitted those line feeds, scrolled the physical screen,
and retained the old in-memory mouse coordinates. The visible permanent-delete
choice no longer matched its hit target, so clicking it could dismiss the modal
without deleting the file. Incremental redraw left parts of the old dialog.

This reproduces the failure, residual popup, red status and shifted editor in
one sequence. It was not a filesystem-delete failure after the permanent action
had been successfully activated.

## Corrected behavior

The terminal file provider has no native trash capability. Delete now asks once
for permanent deletion with Delete Permanently / Cancel. It never launches GIO,
and the installer no longer requires its package for this operation.

Successfully deleted entries have their corresponding buffers closed and copied
paths removed. A failure keeps that entry and its buffer. A concurrently absent
entry is treated as already deleted. Symbolic links are unlinked without
recursively deleting their target; directories and multiple selections retain
their existing confirmation and parent/child deduplication behavior.

All status messages are rendered as a single line: control characters become
spaces and drawing is clipped to the editor's status-row width. This also covers
asynchronously assigned status messages. The underlying logged diagnostic can
retain its original text. Dialog coordinates and editor layout stay aligned.

## Validation

A clean upstream checkout accepted all 36 ordered patches and matched source
fingerprint `90d4c2046c996649b91280d39cbc08f1f1763b4d`. Its locked offline
Release build was installed with an atomic executable replacement. Existing
sessions were not terminated.

| Validation | Result |
| --- | --- |
| Installed deletion / failure / status geometry | 9 methods, 12 case combinations passed |
| Installed existing terminal interactions | 31/31 passed |
| Installed strict behavior | 38/38 passed |
| Installed Unicode column editing | 8 methods, 96 case combinations passed |
| Deployment / environment isolation | 6/6 passed |

This is 92 Python unittest methods, with explicit subcase counts above.
The deletion suite includes a real permission-denied failure in a disposable
unprivileged child editor, not a simulated successful unlink. All tests use
isolated projects; no user file is deleted for validation.

Exact method names and provenance are in [delete-results.json](delete-results.json).
Installed binary SHA-256:
`3690bac3578012b5a1d52252730ed08e0bf4478c015abe0db64d903a912902db`.
Restart an existing editor to load the new executable, and verify it with
`devtui-helix --version`.
