#!/usr/bin/env python3
"""Permanent Explorer deletion and terminal geometry, using disposable fixtures."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr


def request_delete(t, name):
    x, y = t.find(name, True)
    t.click(x, y, 2)
    t.click_text('Delete', exact=True)
    t.wait_for(lambda: 'Permanently delete' in t.text, 'permanent deletion confirmation')
    if 'Move to Trash' in t.text:
        raise AssertionError(t.text)


def assert_clean_geometry(test, t):
    test.assertIn('EXPLORER', t.screen.display[0])
    test.assertIn('NOR', t.screen.display[28])
    body = '\n'.join(row[33:] for row in t.screen.display[:28])
    for text in ('Permanently delete', 'Delete Permanently', 'Trash unavailable', 'Cancel'):
        test.assertNotIn(text, body)
    test.assertFalse(any(ch in body for ch in '┌┐└┘─'), t.text)


@contextmanager
def failing_directory_editor():
    # Root bypasses chmod restrictions. Run only this fixture as an unprivileged
    # user, with an accessible hard link to the exact binary under test.
    with tempfile.TemporaryDirectory(prefix='devtui-delete-assets-') as folder:
        assets = Path(folder); assets.chmod(0o755)
        binary = assets/'hx'
        try: os.link(tr.BINARY, binary)
        except OSError: shutil.copy2(tr.BINARY, binary)
        runtime = assets/'runtime'; runtime.mkdir()
        shutil.copytree(tr.RUNTIME/'themes', runtime/'themes')
        if (tr.RUNTIME/'languages.toml').exists():
            shutil.copy2(tr.RUNTIME/'languages.toml', runtime/'languages.toml')
        real_exec = os.execve
        def execute(path, args, env):
            home = Path(env['HOME']); base = home.parent
            if os.geteuid() == 0:
                for item in [base, *base.rglob('*')]:
                    os.chown(item, 65534, 65534, follow_symlinks=False)
                base.chmod(0o755)
            (base/'workspace/locked').chmod(0o555)
            if os.geteuid() == 0:
                os.setgroups([]); os.setgid(65534); os.setuid(65534)
            real_exec(path, args, env)
        with mock.patch.object(tr, 'BINARY', binary), mock.patch.object(tr, 'RUNTIME', runtime), mock.patch.object(os, 'execve', execute):
            with tr.Terminal({'locked/victim.txt':'KEEP VICTIM\n','keep.txt':'KEEP EDITOR\n'}, 'keep.txt') as t:
                yield t


class DeleteTests(unittest.TestCase):
    def test_permanent_delete_does_not_invoke_gio(self):
        for exit_code in (0, 1):
            with self.subTest(gio_exit=exit_code), tempfile.TemporaryDirectory(prefix='devtui-delete-gio-') as folder:
                directory = Path(folder); marker = directory/'invoked'
                stub = directory/'gio'
                stub.write_text('#!/bin/sh\nprintf invoked > "'+str(marker)+'"\nprintf "trash unsupported\\nadditional detail\\n" >&2\nexit '+str(exit_code)+'\n')
                stub.chmod(0o755)
                with mock.patch.dict(os.environ, {'PATH':str(directory)+os.pathsep+os.environ['PATH']}):
                    with tr.Terminal({'victim.txt':'DELETE\n','keep.txt':'KEEP\n'}, 'victim.txt') as t:
                        request_delete(t, 'victim.txt')
                        t.click_text('Delete Permanently', exact=True)
                        t.wait_for(lambda: not (t.work/'victim.txt').exists(), 'permanent file removal')
                        self.assertFalse(marker.exists(), 'unadvertised trash provider was invoked')
                        self.assertTrue((t.work/'keep.txt').exists())
                        self.assertNotIn('victim.txt', t.screen.display[0])
                        self.assertNotIn('Delete failed', t.text)
                        assert_clean_geometry(self, t)

    def test_cancel_and_escape_leave_document_and_geometry_unchanged(self):
        for cancel in ('mouse', 'escape'):
            with self.subTest(cancel=cancel), tr.Terminal({'victim.txt':'KEEP\n'}, 'victim.txt') as t:
                t.file('victim.txt')
                before = t.screen.display[:29]
                request_delete(t, 'victim.txt')
                if cancel == 'mouse': t.click_text('Cancel', exact=True)
                else: t.send('\x1b')
                self.assertEqual((t.work/'victim.txt').read_text(), 'KEEP\n')
                self.assertEqual(t.screen.display[:29], before)
                assert_clean_geometry(self, t)

    def test_directory_deletion_closes_affected_buffers(self):
        with tr.Terminal({'folder/nested/child.txt':'CHILD\n','folder/other.txt':'OTHER\n','keep.txt':'KEEP\n'}, 'folder/nested/child.txt') as t:
            request_delete(t, 'folder')
            t.click_text('Delete Permanently', exact=True)
            t.wait_for(lambda: not (t.work/'folder').exists(), 'recursive deletion')
            self.assertTrue((t.work/'keep.txt').exists())
            self.assertNotIn('child.txt', t.screen.display[0])
            self.assertNotIn('folder', '\n'.join(row[:32] for row in t.screen.display))
            assert_clean_geometry(self, t)

    def test_multi_selection_deletes_confirmed_items_only(self):
        with tr.Terminal({'a.txt':'A\n','b.txt':'B\n','keep.txt':'KEEP\n'}, 'keep.txt') as t:
            t.file('a.txt'); t.file('b.txt', modifier=16)
            request_delete(t, 'a.txt')
            self.assertIn('2 selected items', t.text)
            t.click_text('Delete Permanently', exact=True)
            self.assertFalse((t.work/'a.txt').exists())
            self.assertFalse((t.work/'b.txt').exists())
            self.assertEqual((t.work/'keep.txt').read_text(), 'KEEP\n')
            assert_clean_geometry(self, t)

    def test_symlink_deletion_does_not_remove_its_target(self):
        for dangling in (False, True):
            with self.subTest(dangling=dangling), tr.Terminal({'keep.txt':'KEEP\n'}, 'keep.txt') as t:
                target = t.base/'external'
                if not dangling:
                    target.mkdir(); (target/'child.txt').write_text('KEEP TARGET\n')
                link = t.work/'link'; link.symlink_to(target, target_is_directory=True)
                t.send('\x1b')
                request_delete(t, 'link'); t.click_text('Delete Permanently', exact=True)
                self.assertFalse(os.path.lexists(link))
                if not dangling: self.assertEqual((target/'child.txt').read_text(), 'KEEP TARGET\n')
                assert_clean_geometry(self, t)

    def test_file_removed_during_confirmation_is_already_done(self):
        with tr.Terminal({'victim.txt':'DELETE\n'}, 'victim.txt') as t:
            request_delete(t, 'victim.txt')
            (t.work/'victim.txt').unlink()
            t.click_text('Delete Permanently', exact=True)
            self.assertNotIn('Delete failed', t.text)
            self.assertNotIn('victim.txt', t.screen.display[0])
            assert_clean_geometry(self, t)

    def test_permission_failure_preserves_file_buffer_and_ui(self):
        with failing_directory_editor() as t:
            t.file('locked')
            t.file('victim.txt')
            request_delete(t, 'victim.txt')
            t.click_text('Delete Permanently', exact=True)
            t.wait_for(lambda: 'Delete failed:' in t.text, 'real permission error')
            self.assertEqual((t.work/'locked/victim.txt').read_text(), 'KEEP VICTIM\n')
            self.assertIn('victim.txt', t.screen.display[0])
            assert_clean_geometry(self, t)
            request_delete(t, 'victim.txt'); t.click_text('Cancel', exact=True)
            assert_clean_geometry(self, t)
            t.file('keep.txt'); t.edit('EDIT'); t.command('w')
            self.assertIn('EDIT', (t.work/'keep.txt').read_text())

    def test_multiline_status_keeps_dialog_hit_targets_aligned(self):
        with tr.Terminal({'victim.txt':'DELETE\n'}, 'victim.txt') as t:
            t.command("echo %sh{printf 'FIRST\\nSECOND\\tTHIRD\\rFOURTH'}")
            self.assertIn('EXPLORER', t.screen.display[0])
            self.assertIn('FIRST SECOND THIRD FOURTH', t.screen.display[29])
            self.assertNotIn(b'FIRST\nSECOND', bytes(t.raw))
            request_delete(t, 'victim.txt'); t.click_text('Delete Permanently', exact=True)
            self.assertFalse((t.work/'victim.txt').exists())
            assert_clean_geometry(self, t)

    def test_long_status_is_clipped_to_one_row(self):
        with tr.Terminal({'victim.txt':'KEEP\n'}, 'victim.txt') as t:
            t.command("echo %sh{printf '%%01000d' 0}")
            self.assertIn('EXPLORER', t.screen.display[0])
            self.assertIn('KEEP', t.screen.display[1])
            self.assertIn('00000000', t.screen.display[29])
            request_delete(t, 'victim.txt'); t.click_text('Cancel', exact=True)
            assert_clean_geometry(self, t)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    tr.BINARY = args.binary.resolve(); tr.RUNTIME = args.runtime.resolve()
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(DeleteTests)
    if args.filter: tests = unittest.TestSuite(t for t in tests if args.filter in t.id())
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    raise SystemExit(not result.wasSuccessful())
