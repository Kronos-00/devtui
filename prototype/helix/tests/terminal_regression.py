#!/usr/bin/env python3
"""Isolated real-PTY regression tests; never touch the caller's workspace/config."""
from __future__ import annotations
import argparse
import base64
import codecs
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import socket
import struct
import tempfile
import termios
import time
import unittest
import fcntl
import pyte

ROOT = Path(__file__).resolve().parents[3]
BINARY: Path
RUNTIME: Path

class Screen(pyte.Screen):
    # Ignore capability probes that do not affect the rendered text surface.
    def report_device_status(self, *args, **kwargs):
        pass
    def report_device_attributes(self, *args, **kwargs):
        pass

class Terminal:
    def __init__(self, files: dict[str, str], initial: str | None = None, width: int = 120, *, config: str | None = None, languages: str | None = None, environment: dict[str, str] | None = None, directory: str | None = None):
        self.tmp = tempfile.TemporaryDirectory(prefix='devtui-regression-')
        self.base = Path(self.tmp.name)
        self.work = self.base / 'workspace'
        self.home = self.base / 'home'
        self.work.mkdir(); self.home.mkdir()
        for name, content in files.items():
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        cfg = self.home / '.config/devtui-helix/helix'
        cfg.mkdir(parents=True)
        shutil.copyfile(ROOT / 'prototype/helix/config/config.toml', cfg / 'config.toml')
        shutil.copyfile(ROOT / 'prototype/helix/config/languages.toml', cfg / 'languages.toml')
        if config is not None: (cfg / 'config.toml').write_text(config)
        if languages is not None: (cfg / 'languages.toml').write_text(languages)
        self.sock = self.base / 'editor.sock'
        self.width = width
        self.screen = Screen(width, 30)
        self.stream = pyte.ByteStream(self.screen)
        self.raw = bytearray()
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('ZELLIJ', 'DEVTUI_', 'HELIX_')):
                env.pop(key)
        env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(cfg.parent),
                   XDG_STATE_HOME=str(self.home / '.local/state'),
                   XDG_CACHE_HOME=str(self.home / '.cache'),
                   HELIX_RUNTIME=str(RUNTIME), DEVTUI_HELIX_SOCKET=str(self.sock),
                   TERM='xterm-256color', LANG='C.UTF-8')
        env.update(environment or {})
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            fcntl.ioctl(1, termios.TIOCSWINSZ, struct.pack('HHHH', 30, width, 0, 0))
            os.chdir(self.work / directory if directory else self.work)
            os.execve(str(BINARY), [str(BINARY)] + ([initial] if initial else []), env)
        self.alive = True
        try:
            self.wait_for(lambda: 'EXPLORER' in self.text, 'initial Explorer')
            self.drain(.15)
        except BaseException:
            self.close()
            raise

    @property
    def text(self) -> str:
        return '\n'.join(self.screen.display)

    def drain(self, duration: float = .08) -> bytes:
        end = time.monotonic() + duration
        data = bytearray()
        while time.monotonic() < end:
            ready, _, _ = select.select([self.fd], [], [], min(.025, max(0, end-time.monotonic())))
            if not ready: continue
            try: chunk = os.read(self.fd, 65536)
            except OSError: break
            if not chunk: break
            data.extend(chunk); self.raw.extend(chunk); self.stream.feed(chunk)
        return bytes(data)

    def send(self, data: bytes | str, delay: float = .08):
        if isinstance(data, str): data = data.encode()
        os.write(self.fd, data); self.drain(delay)

    def wait_for(self, predicate, label: str, timeout: float = 5):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.drain(.04)
            if predicate(): return
        raise AssertionError(f'timed out: {label}\n{self.text}')

    def mouse(self, code: int, x: int, y: int, release=False):
        self.send(f'\x1b[<{code};{x+1};{y+1}' + ('m' if release else 'M'), .035)

    def click(self, x: int, y: int, button: int = 0):
        self.mouse(button,x,y); self.mouse(button,x,y,True); self.drain(.08)

    def find(self, text: str, sidebar=False, exact=False):
        if exact and not sidebar:
            # A pointer-anchored menu can cover only part of a populated text
            # row. Match its label within the rendered menu rectangle instead
            # of requiring the entire terminal row to contain only that label.
            for top in range(self.screen.lines):
                for left in range(self.screen.columns):
                    if self.screen.buffer[top][left].data != '┌':
                        continue
                    right = next((x for x in range(left+1, self.screen.columns)
                                  if self.screen.buffer[top][x].data == '┐'), None)
                    if right is None:
                        continue
                    bottom = next((y for y in range(top+1, self.screen.lines)
                                   if self.screen.buffer[y][left].data == '└'
                                   and self.screen.buffer[y][right].data == '┘'), None)
                    if bottom is None:
                        continue
                    for y in range(bottom+1, self.screen.lines):
                        cells = [self.screen.buffer[y][x].data for x in range(left, right+1)]
                        if ''.join(cells).strip(' │┃') == text:
                            offset = next(i for i, value in enumerate(cells) if value and not value.isspace())
                            return left+offset, y
        for y, row in enumerate(self.screen.display):
            content = row[:32] if sidebar else row
            if exact:
                if content.strip(' │┃') == text:
                    return content.index(text), y
            elif text in content:
                return content.index(text), y
        raise AssertionError(f'cannot find {text!r}\n{self.text}')

    def click_text(self, text: str, sidebar=False, exact=False):
        x,y=self.find(text,sidebar,exact); self.click(x,y)

    def file(self, name: str, double=False, modifier=0):
        x,y=self.find(name,True); self.click(x,y,modifier)
        if double: self.click(x,y,modifier)

    def editor_focus(self):
        self.click(45,1)

    def command(self, command: str):
        self.send('\x1b',.12); self.send(':'+command+'\r',.15)

    def save_as(self, path: Path):
        self.wait_for(lambda:'Save As:' in self.text, 'Save As prompt')
        self.send('\x15'); self.send(str(path)); self.send('\r',.2)

    def edit(self, text: str):
        self.editor_focus(); self.send('i'+text+'\x1b',.12)

    def clipboard(self) -> list[str]:
        values=[]
        for encoded in re.findall(rb'\x1b\]52;[^;]*;([A-Za-z0-9+/=]*)(?:\x07|\x1b\\)',bytes(self.raw)):
            try: values.append(base64.b64decode(encoded).decode())
            except (ValueError,UnicodeError): pass
        return values

    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    def close(self):
        if self.alive:
            try: os.kill(self.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                try:
                    if os.waitpid(self.pid,os.WNOHANG)[0]: break
                except ChildProcessError: break
                self.drain(.02)
            else:
                os.kill(self.pid,signal.SIGKILL); os.waitpid(self.pid,0)
            os.close(self.fd); self.alive=False
        self.tmp.cleanup()

class MigrationTests(unittest.TestCase):
    def test_preview_pinning_and_single_click_after_insert(self):
        with Terminal({'a.txt':'AAA\n','b.txt':'BBB\n','c.txt':'CCC\n'}) as t:
            t.file('a.txt'); self.assertIn('a.txt',t.screen.display[0][32:])
            t.file('b.txt'); self.assertNotIn('a.txt',t.screen.display[0][32:])
            t.file('a.txt',double=True); t.file('b.txt')
            self.assertIn('a.txt',t.screen.display[0][32:]); self.assertIn('b.txt',t.screen.display[0][32:])
            t.editor_focus();t.send('iX');t.file('c.txt')
            self.assertIn('b.txt',t.screen.display[0][32:]);self.assertIn('c.txt',t.screen.display[0][32:])
            self.assertIn('EXPLORER',t.text)

    def test_untitled_wq_and_cancel(self):
        with Terminal({}) as t:
            t.edit('unsaved');t.command('wq')
            t.wait_for(lambda:'Save As:' in t.text,'untitled Save As')
            t.send('\x1b');self.assertFalse((t.work/'saved.txt').exists())
            t.command('wq');t.save_as(t.work/'saved.txt')
            t.wait_for(lambda:(t.work/'saved.txt').exists(),'file saved')
            self.assertEqual((t.work/'saved.txt').read_text(),'unsaved\n')
            self.assertIn('EXPLORER',t.text)

    def test_quit_command_families(self):
        with Terminal({'a.txt':'AAA\n'}) as t:
            for command in ['q!','quit!','close!']:
                t.command('open a.txt');t.edit('DISCARD');t.command(command)
                self.assertEqual((t.work/'a.txt').read_text(),'AAA\n')
                self.assertIn('EXPLORER',t.text)
            for command in ['wq','x','xit','exit']:
                t.command('open a.txt');t.edit('S');t.command(command)
                self.assertIn('S', (t.work/'a.txt').read_text())
                self.assertIn('EXPLORER',t.text)
            t.command('qa!');self.assertIn('EXPLORER',t.text)

    def test_mouse_close_dialog_cancel_and_discard(self):
        with Terminal({'a.txt':'AAA\n'},'a.txt') as t:
            t.edit('X');t.command('q')
            t.wait_for(lambda:'Save changes' in t.text,'dirty close')
            t.click_text('Cancel',exact=True)
            t.wait_for(lambda:'Save changes' not in t.text,'cancel dismissed dialog')
            self.assertIn('X',t.text);self.assertEqual((t.work/'a.txt').read_text(),'AAA\n')
            t.command('q');t.click_text("Don't Save",exact=True)
            t.wait_for(lambda:'Save changes' not in t.text,'discard dismissed dialog')
            self.assertEqual((t.work/'a.txt').read_text(),'AAA\n')

    def test_mouse_file_menu_copy_paste(self):
        with Terminal({'a.txt':'AAA\n'}) as t:
            x,y=t.find('a.txt',True);t.click(x,y,2)
            t.wait_for(lambda:'Copy Relative Path' in t.text,'context menu')
            t.click_text('Copy',exact=True)
            t.wait_for(lambda:'Copy Relative Path' not in t.text,'copy action')
            # root is the first row below the sidebar title
            t.click(4,1,2);t.click_text('Paste',exact=True)
            t.wait_for(lambda:(t.work/'a copy.txt').exists(),'file copy')
            self.assertEqual((t.work/'a copy.txt').read_text(),'AAA\n')

    def test_live_multicursor_before_escape(self):
        with Terminal({'a.txt':'aaaaaa\nbbbbbb\ncccccc\n'},'a.txt') as t:
            t.mouse(1,40,1);t.mouse(33,40,3);t.mouse(1,40,3,True)
            t.send('i');t.send('X')
            self.assertEqual(sum('X' in row[33:] for row in t.screen.display[1:4]),3,t.text)
            t.send('\x1b[C');t.send('Y')
            self.assertEqual(sum('Y' in row[33:] for row in t.screen.display[1:4]),3,t.text)
            t.command('w')
            self.assertEqual((t.work/'a.txt').read_text().count('X'),3)
            self.assertEqual((t.work/'a.txt').read_text().count('Y'),3)
            self.assertNotIn(b';?\x07',bytes(t.raw))

    def test_middle_from_insert_no_clipboard_query(self):
        with Terminal({'a.txt':'aaaa\nbbbb\ncccc\n'},'a.txt') as t:
            t.editor_focus();t.send('i')
            t.mouse(1,40,1);t.mouse(33,40,3);t.mouse(1,40,3,True)
            t.send('iZ');self.assertEqual(sum('Z' in row[33:] for row in t.screen.display[1:4]),3,t.text)
            self.assertFalse(re.search(rb'\x1b\]52;[^;]*;\?',t.raw))

    def test_external_ipc_preserves_editor_and_tree(self):
        with Terminal({'a.txt':'AAA\n'},'a.txt') as t:
            external=t.base/'outside.txt';external.write_text('111\n222\n333\n')
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                s.settimeout(2);s.connect(str(t.sock));s.sendall((json.dumps({'path':str(external),'line':2,'column':2})+'\n').encode())
            t.wait_for(lambda:'outside.txt' in t.screen.display[0], 'external document')
            t.send('iQ\x1b');t.command('w')
            self.assertEqual(external.read_text(),'111\n2Q22\n333\n')
            self.assertIn('EXPLORER',t.text)

    def test_save_as_overwrite_cancel_then_confirm(self):
        with Terminal({'existing.txt':'KEEP\n'}) as t:
            t.edit('NEW');t.command('wq');t.save_as(t.work/'existing.txt')
            t.wait_for(lambda:'Replace existing' in t.text,'overwrite confirmation')
            self.assertEqual((t.work/'existing.txt').read_text(),'KEEP\n')
            t.click_text('Cancel',exact=True)
            t.command('wq');t.save_as(t.work/'existing.txt');t.click_text('Replace',exact=True)
            t.wait_for(lambda:(t.work/'existing.txt').read_text()=='NEW\n','confirmed overwrite')
            self.assertIn('EXPLORER',t.text)

    def test_failed_save_does_not_close_on_later_manual_save(self):
        with Terminal({}) as t:
            t.edit('KEEP');t.command('wq');t.save_as(t.work/'missing'/'a.txt')
            t.wait_for(lambda:'parent directory' in t.text,'failed write')
            t.command('write fixed.txt')
            t.wait_for(lambda:(t.work/'fixed.txt').exists(),'retry save')
            self.assertIn('fixed.txt',t.screen.display[0])
            self.assertEqual((t.work/'fixed.txt').read_text(),'KEEP\n')

    def test_create_existing_does_not_truncate(self):
        with Terminal({'a.txt':'KEEP\n'}) as t:
            t.click(4,1,2);t.click_text('New File',exact=True)
            t.send('a.txt\r',.25)
            self.assertEqual((t.work/'a.txt').read_text(),'KEEP\n')
            self.assertIn('already exists',t.text)

    def test_rename_collision_does_not_overwrite(self):
        with Terminal({'a.txt':'AAA\n','b.txt':'BBB\n'}) as t:
            x,y=t.find('a.txt',True);t.click(x,y,2);t.click_text('Rename',exact=True)
            t.send('\x15b.txt\r',.2)
            self.assertEqual((t.work/'a.txt').read_text(),'AAA\n')
            self.assertEqual((t.work/'b.txt').read_text(),'BBB\n')

    def test_recursive_paste_is_rejected_before_creation(self):
        with Terminal({'folder/sub/a.txt':'KEEP\n'}) as t:
            t.file('folder')
            x,y=t.find('folder',True);t.click(x,y,2);t.click_text('Copy',exact=True)
            x,y=t.find('sub',True);t.click(x,y,2);t.click_text('Paste',exact=True)
            t.wait_for(lambda:'Cannot paste a folder' in t.text,'recursive paste rejected')
            self.assertFalse((t.work/'folder/sub/folder').exists())
            self.assertEqual((t.work/'folder/sub/a.txt').read_text(),'KEEP\n')

    def test_symlink_copy_does_not_follow_cycle(self):
        with Terminal({'folder/a.txt':'AAA\n'}) as t:
            os.symlink('.',t.work/'folder/loop')
            x,y=t.find('folder',True);t.click(x,y,2);t.click_text('Copy',exact=True)
            t.click(4,1,2);t.click_text('Paste',exact=True)
            t.wait_for(lambda:(t.work/'folder copy/loop').is_symlink(),'symlink copied')
            self.assertEqual(os.readlink(t.work/'folder copy/loop'),'.')

    def test_explorer_modifiers_and_path_copy(self):
        with Terminal({'a.txt':'A\n','b.txt':'B\n','c.txt':'C\n'}) as t:
            t.file('a.txt');t.file('b.txt',modifier=16)
            x,y=t.find('b.txt',True);t.click(x,y,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'a.txt\nb.txt')
            t.file('c.txt');x,y=t.find('c.txt',True);t.click(x,y,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'c.txt')
            t.file('a.txt');t.file('b.txt',modifier=8)
            x,y=t.find('b.txt',True);t.click(x,y,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'a.txt\nb.txt')

    def test_explorer_wheel_does_not_reset_viewport(self):
        with Terminal({f'{i:03}.txt':'A\n' for i in range(70)}) as t:
            t.mouse(65,10,8);t.mouse(65,10,8)
            t.wait_for(lambda:'000.txt' not in t.text,'Explorer wheel scroll')
            t.drain(.3);self.assertNotIn('000.txt',t.text)
            t.mouse(64,10,8);t.mouse(64,10,8)
            t.wait_for(lambda:'000.txt' in t.text,'Explorer wheel reverse')

    def test_resize_reverse_pause_and_minimum(self):
        with Terminal({'a.txt':'A\n'}) as t:
            t.mouse(0,31,10);t.mouse(32,50,10);t.drain(.7)
            self.assertEqual(t.screen.display[0].index('│'),51)
            t.mouse(32,20,10)
            self.assertEqual(t.screen.display[0].index('│'),21)
            t.mouse(32,3,10)
            self.assertEqual(t.screen.display[0].index('│'),12)
            t.mouse(32,30,10);t.mouse(0,30,10,True)
            self.assertEqual(t.screen.display[0].index('│'),31)
            state=t.home/'.local/state/devtui/explorer-width'
            self.assertEqual(state.read_text().strip(),'31')

    def test_existing_pinned_tab_does_not_pin_other_preview(self):
        with Terminal({'a.txt':'A\n','b.txt':'B\n','c.txt':'C\n'}) as t:
            t.file('a.txt',double=True);t.file('b.txt');t.file('a.txt',double=True);t.file('c.txt')
            self.assertNotIn('b.txt',t.screen.display[0][33:])
            self.assertIn('a.txt',t.screen.display[0][33:])

    def test_active_tab_visible_when_overflowing(self):
        files={f'document-{i:02}-long-name.txt':f'{i}\n' for i in range(8)}
        with Terminal(files,width=90) as t:
            t.editor_focus()
            for name in files:
                t.command('open '+name)
                self.assertIn(name,t.screen.display[0][33:])
                self.assertIn('×',t.screen.display[0][33:])

    def test_blank_tab_strip_creates_untitled(self):
        with Terminal({'a.txt':'A\n'},'a.txt') as t:
            t.click(104,0);t.click(104,0)
            self.assertIn('[No Name]',t.screen.display[0])
            t.edit('UNTITLED');t.command('wq');t.save_as(t.work/'new.txt')
            t.wait_for(lambda:(t.work/'new.txt').exists(),'new untitled saved')
            self.assertEqual((t.work/'new.txt').read_text(),'UNTITLED\n')

    def test_sparse_column_copy_and_spread_paste(self):
        with Terminal({'a.txt':'abcdef\na\nabcdef\n'},'a.txt') as t:
            t.mouse(1,42,1);t.mouse(33,45,3);t.mouse(1,45,3,True);t.send('\x03')
            values=t.clipboard()[-1].split('\n')
            self.assertEqual(len(values),2);self.assertEqual(values[0],values[1]);self.assertTrue(values[0])
            t.send('\x1b');t.mouse(1,55,1);t.mouse(33,55,3);t.mouse(1,55,3,True);t.send('i')
            t.send('\x1b[200~A\nB\nC\x1b[201~');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'abcdefA\naB\nabcdefC\n')

    def test_copy_on_self_duplicates_beside_folder(self):
        with Terminal({'folder/a.txt':'KEEP\n'}) as t:
            x,y=t.find('folder',True);t.click(x,y,2);t.click_text('Copy',exact=True)
            x,y=t.find('folder',True);t.click(x,y,2);t.click_text('Paste',exact=True)
            t.wait_for(lambda:(t.work/'folder copy/a.txt').exists(),'duplicate folder')
            self.assertFalse((t.work/'folder/folder').exists())

    def test_incomplete_ipc_request_cannot_block_following_client(self):
        with Terminal({'a.txt':'A\n','b.txt':'B\n'},'a.txt') as t:
            self.assertEqual(t.sock.stat().st_mode & 0o777,0o600)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stalled:
                stalled.connect(str(t.sock));stalled.sendall(b'{')
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                    client.settimeout(2);client.connect(str(t.sock))
                    client.sendall((json.dumps({'path':str(t.work/'b.txt'),'line':1,'column':999})+'\n').encode())
                t.wait_for(lambda:'b.txt' in t.screen.display[0],'IPC after stalled request',timeout=3)
                t.send('iQ\x1b');t.command('w')
                self.assertEqual((t.work/'b.txt').read_text(),'BQ\n')

    def test_project_replace(self):
        with Terminal({'a.txt':'foo1 alpha\nfoo2 beta\n','b.txt':'gamma foo3\n'}) as t:
            t.editor_focus();t.send('\x1bOP');t.send('devtui_project_replace\r',.2)
            t.send('\x1brfoo([0-9])\r');t.send('bar$1\r',.35)
            t.wait_for(lambda:'Replace All' in t.text,'replace preview')
            t.send('\r',.4)
            t.wait_for(lambda:'bar1' in (t.work/'a.txt').read_text(),'replace applied')
            self.assertEqual((t.work/'a.txt').read_text(),'bar1 alpha\nbar2 beta\n')
            self.assertEqual((t.work/'b.txt').read_text(),'gamma bar3\n')

    def test_markdown_source_and_symbol_menu(self):
        with Terminal({'note.md':'`inline`\n```cpp\nint a;\n```\n'},'note.md') as t:
            self.assertIn('`inline`',t.text);self.assertIn('```cpp',t.text)
            t.click(44,1,2)
            t.wait_for(lambda:'Definition' in t.text,'editor symbol menu')
            self.assertIn('Code Action',t.text)
            t.send('\x1b');self.assertIn('EXPLORER',t.text)

    def test_current_replace_preserves_unsaved_state(self):
        with Terminal({'a.txt':'foo foo\n'},'a.txt') as t:
            t.editor_focus();t.send('\x1bOP');t.send('devtui_current_replace\r',.2)
            t.wait_for(lambda:'Search:' in t.text,'current replace prompt')
            t.send('foo\r');t.send('bar\r',.25)
            t.wait_for(lambda:'Replace All in File' in t.text,'current replace preview')
            t.send('\r',.2)
            self.assertEqual((t.work/'a.txt').read_text(),'foo foo\n')
            self.assertIn('bar bar',t.text)
            t.command('w');self.assertEqual((t.work/'a.txt').read_text(),'bar bar\n')

    def test_current_replace_in_untitled(self):
        with Terminal({}) as t:
            t.edit('foo foo');t.send('\x1bOP');t.send('devtui_current_replace\r',.2)
            t.wait_for(lambda:'Search:' in t.text,'untitled current replace')
            t.send('foo\r');t.send('bar\r',.25);t.send('\r',.2)
            t.command('wq');t.save_as(t.work/'replaced.txt')
            t.wait_for(lambda:(t.work/'replaced.txt').exists(),'replaced scratch saved')
            self.assertEqual((t.work/'replaced.txt').read_text(),'bar bar\n')

    def test_palette_debug_menu_and_interpreter_prompt(self):
        with Terminal({'a.py':'print(1)\n'},'a.py') as t:
            t.editor_focus();t.send('\x1bOP');t.send('devtui_debug_menu\r',.2)
            t.wait_for(lambda:'Start / Continue' in t.text,'Run and Debug menu')
            self.assertIn('Call Stack',t.text);self.assertIn('Toggle Breakpoint',t.text)
            t.send('\x1b');t.send('\x1bOP');t.send('devtui_python_venv\r',.2)
            t.wait_for(lambda:'Python Environment:' in t.text,'interpreter prompt')
            t.send('\x1b');self.assertIn('EXPLORER',t.text)

    def test_scrollbar_drags_without_editing_document(self):
        content=''.join(f'LINE-{i:03}\n' for i in range(1,201))
        with Terminal({'long.txt':content},'long.txt') as t:
            t.mouse(0,t.width-1,2);t.mouse(32,t.width-1,24);t.mouse(0,t.width-1,24,True)
            seen=[int(v) for v in re.findall(r'LINE-(\d+)',t.text)]
            self.assertTrue(seen and max(seen)>100,t.text)
            self.assertEqual((t.work/'long.txt').read_text(),content)

    def test_normal_escape_clears_additional_carets(self):
        with Terminal({'a.txt':'aaaa\nbbbb\ncccc\n'},'a.txt') as t:
            t.mouse(1,41,1);t.mouse(33,41,3);t.mouse(1,41,3,True)
            t.send('\x1b');t.send('iQ');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text().count('Q'),1)

    def test_close_glyph_remains_clickable_when_dirty(self):
        with Terminal({'a.txt':'KEEP\n'},'a.txt') as t:
            t.edit('X');row=t.screen.display[0]
            self.assertIn('●',row);self.assertIn('×',row)
            t.click(row.index('×'),0)
            t.wait_for(lambda:'Save changes' in t.text,'close glyph confirmation')
            t.click_text('Cancel',exact=True)
            self.assertEqual((t.work/'a.txt').read_text(),'KEEP\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    BINARY=args.binary.resolve();RUNTIME=args.runtime.resolve()
    assert BINARY.is_file() and RUNTIME.is_dir()
    tests=unittest.defaultTestLoader.loadTestsFromTestCase(MigrationTests)
    if args.filter:tests=unittest.TestSuite(t for t in tests if args.filter in t.id())
    result=unittest.TextTestRunner(verbosity=2).run(tests)
    raise SystemExit(not result.wasSuccessful())
