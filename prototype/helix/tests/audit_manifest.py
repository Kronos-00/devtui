#!/usr/bin/env python3
"""Check immutable baseline, reference hashes, patch inventory and test links."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'prototype/helix/docs'


def git(*args: str, source: Path = ROOT) -> bytes:
    return subprocess.check_output(['git', '-C', str(source), *args])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Applied Helix source to verify against HELIX_TREE')
    args = parser.parse_args()
    baseline = json.loads((DOCS / 'main-baseline.json').read_text())
    revision = baseline['commit']
    paths = git('ls-tree', '-r', '--name-only', revision).decode().splitlines()
    require(sorted(paths) == sorted(f['path'] for f in baseline['files']), 'Baseline file inventory changed')
    for item in baseline['files']:
        actual = hashlib.sha256(git('show', revision + ':' + item['path'])).hexdigest()
        require(actual == item['sha256'], f'Baseline hash mismatch: {item["path"]}')

    refs = json.loads((DOCS / 'vscode-reference-manifest.json').read_text())
    ref_names = {item['key'] for item in refs['sources']}
    require(len(ref_names) == len(refs['sources']), 'Duplicate reference keys')
    for item in refs['sources']:
        require(bool(re.fullmatch(r'[0-9a-f]{64}', item['sha256'])), f'Invalid source hash: {item["key"]}')
        require(item['revision'] in item['url'], f'Unpinned reference: {item["key"]}')

    patch_dir = ROOT / 'prototype/helix/patches'
    names = [line for line in (patch_dir / 'series').read_text().splitlines() if line and not line.startswith('#')]
    require(len(names) == len(set(names)), 'Duplicate patches in series')
    touched = set()
    for name in names:
        require(Path(name).name == name and '..' not in name, 'Invalid patch path')
        patch = (patch_dir / name).read_text()
        touched.update(re.findall(r'^diff --git a/\S+ b/(\S+)$', patch, re.M))
    expected_tree = (ROOT / 'prototype/helix/HELIX_TREE').read_text().strip()
    require(bool(re.fullmatch(r'[0-9a-f]{40}', expected_tree)), 'Invalid canonical Helix tree')
    if args.source:
        actual_tree = git('write-tree', source=args.source).decode().strip()
        require(actual_tree == expected_tree, 'Applied Helix tree does not match HELIX_TREE')
        require(not git('diff', '--name-only', source=args.source).strip(), 'Unstaged Helix source changes')

    audit = json.loads((DOCS / 'feature-audit.json').read_text())
    require(audit['baseline_commit'] == revision, 'Audit baseline mismatch')
    require(audit['vscode_commit'] == refs['revision'], 'Audit reference mismatch')
    ids, checked_sources = set(), set()
    test_defs = {}
    for group in audit['groups']:
        for feature in group['features']:
            label = feature['id']
            require(label not in ids, 'Duplicate feature ID: ' + label)
            ids.add(label)
            require(bool(feature['baseline_sources']), 'Missing baseline for ' + label)
            require(all(p in paths for p in feature['baseline_sources']), 'Invalid baseline source: ' + label)
            require(all(r in ref_names for r in feature['reference_sources']), 'Unknown reference: ' + label)
            require(bool(feature['helix_sources'] and feature['verification']), 'Missing evidence: ' + label)
            for entry in feature['helix_sources']:
                if entry.startswith('prototype/'):
                    require((ROOT / entry).exists(), 'Missing migration file: ' + entry)
                else:
                    require(any(p == entry or p.startswith(entry.rstrip('/') + '/') for p in touched),
                            'Migration source absent from patches: ' + entry)
                    if args.source:
                        require((args.source / entry).exists(), 'Missing applied source: ' + entry)
                checked_sources.add(entry)
            for evidence in feature['verification']:
                filename, _, method = evidence.partition(':')
                if not filename.endswith('.py'):
                    continue
                test = Path(__file__).parent / filename
                require(test.is_file(), 'Missing evidence suite: ' + filename)
                if method:
                    if filename not in test_defs:
                        tree = ast.parse(test.read_text())
                        test_defs[filename] = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                    require(method in test_defs[filename], 'Missing named regression: ' + evidence)
    print(json.dumps({'baseline_files': len(paths), 'feature_checkpoints': len(ids),
                      'source_references': len(ref_names), 'ordered_patches': len(names),
                      'implementation_paths': len(checked_sources),
                      'applied_source_tree_verified': bool(args.source), 'result': 'PASS'}, indent=2))


if __name__ == '__main__':
    main()
