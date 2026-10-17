#!/usr/bin/env python3
"""Record independent workspace and shortcut-plugin build fingerprints."""
import hashlib
import json
from pathlib import Path
import sys
root,prefix,plugin=map(Path,sys.argv[1:4])
paths=['patches/zellij-0.45.1-mouse-passthrough.patch','prototype/helix/zellij/cheatsheet-window.patch','patches/zellij-link-devtui.patch','prototype/helix/zellij/link-paths.patch','prototype/helix/shortcuts/Cargo.toml','prototype/helix/shortcuts/src/main.rs','prototype/helix/shortcuts/shortcuts.json']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
versions=dict(line.split('=',1) for line in (root/'versions.env').read_text().splitlines() if '=' in line)
info={'zellij_version':versions['ZELLIJ_VERSION'],'upstream_archive_sha256':versions['ZELLIJ_SOURCE_SHA256'],'rust':versions['RUST_VERSION'],'binary_sha256':sha(prefix/'bin/zellij'),'shortcuts_plugin_sha256':sha(plugin),'inputs':{path:sha(root/path) for path in paths},'builtin_plugins':{p.name:sha(p) for p in sorted((prefix/'share/zellij/plugins').glob('*.wasm'))}}
target=prefix/'workspace-build-info.json'
temporary=target.with_suffix('.json.new');temporary.write_text(json.dumps(info,indent=2)+'\n');temporary.replace(target)
