#!/usr/bin/env python3
"""Smoke-test installed workspace components in a disposable named session."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
import pyte

class Screen(pyte.Screen):
    def report_device_status(self, *args, **kwargs): pass
    def report_device_attributes(self, *args, **kwargs): pass

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path.home())
    parser.add_argument('--zellij',default=None)
    args=parser.parse_args()
    home=args.home.resolve()
    args.zellij=args.zellij or str(home/'.local/opt/devtui/helix-prototype/bin/zellij')
    if not Path(args.zellij).is_file(): args.zellij=shutil.which('zellij')
    if not args.zellij: parser.error('Zellij is not installed')
    with tempfile.TemporaryDirectory(prefix='devtui-session-smoke-') as temporary:
        base=Path(temporary);work=base/'workspace';work.mkdir()
        (work/'sample.txt').write_text('smoke fixture\n')
        subprocess.run(['git','init','-q',str(work)],check=True)
        session='devtui-audit-'+str(os.getpid())
        env=os.environ.copy()
        for key in list(env):
            if key.startswith(('ZELLIJ','DEVTUI_')):env.pop(key)
        env.update(HOME=str(home),TERM='xterm-256color',
                   DEVTUI_HELIX_SOCKET=str(base/'editor.sock'),
                   DEVTUI_HELIX_EDITOR_PANE_FILE=str(base/'editor.pane'))
        assets=home/'.local/opt/devtui/helix-prototype/share/zellij'
        command=[args.zellij]+(['--data-dir',str(assets)] if assets.is_dir() else [])+['--session',session,'--config',str(home/'.config/devtui-helix/zellij.kdl'),
                 '--new-session-with-layout',str(home/'.config/zellij/layouts/dev-helix.kdl')]
        pid,fd=pty.fork()
        if pid==0:
            os.chdir(work)
            fcntl.ioctl(1,termios.TIOCSWINSZ,struct.pack('HHHH',40,180,0,0))
            os.execve(command[0],command,env)
        screen=Screen(180,40);stream=pyte.ByteStream(screen)
        def drain(seconds):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                ready,_,_=select.select([fd],[],[],.04)
                if ready:
                    try:data=os.read(fd,65536)
                    except OSError:return
                    stream.feed(data)
        try:
            until=time.monotonic()+12
            while time.monotonic()<until:
                drain(.15)
                if (base/'editor.sock').exists() and 'EXPLORER' in '\n'.join(screen.display):break
            drain(.4)
            text='\n'.join(screen.display)
            result={'explorer_visible':'EXPLORER' in text,
                    'editor_endpoint':(base/'editor.sock').exists(),
                    'shortcut_banner_removed':'VS Code-style terminal IDE' not in text,
                    'shortcut_hint_visible':'F4 shortcuts' in text,
                    'git_pane':'git' in text.lower(),
                    'editor_pane_recorded':(base/'editor.pane').exists()}
            assert all(result.values()),result
            pane=(base/'editor.pane').read_text().strip()
            subprocess.run([str(home/'.local/bin/devtui-helix-open'),str(work/'sample.txt'),'1','3'],env=env,check=True,timeout=5)
            drain(.5)
            dump=subprocess.run([args.zellij,'-s',session,'action','dump-screen','--pane-id',pane],
                                env=env,text=True,capture_output=True,check=True,timeout=5)
            result['external_open_in_existing_pane']='smoke fixture' in dump.stdout
            assert result['external_open_in_existing_pane'],dump.stdout
            os.write(fd,b'\x1bOS')
            until=time.monotonic()+5
            while time.monotonic()<until:
                drain(.1)
                if 'Ctrl / Shift / Alt' in '\n'.join(screen.display):break
            result['shortcut_window_visible']='Ctrl / Shift / Alt' in '\n'.join(screen.display)
            assert result['shortcut_window_visible'],'\n'.join(screen.display)
            os.write(fd,b'\x1b');drain(.35)
            result['shortcut_window_closed']='Ctrl / Shift / Alt' not in '\n'.join(screen.display)
            assert result['shortcut_window_closed'],'\n'.join(screen.display)
            os.write(fd,b'iW\x1b');drain(.2);os.write(fd,b'\x13');drain(.4)
            result['editor_save_after_help']=(work/'sample.txt').read_text()=='smWoke fixture\n'
            assert result['editor_save_after_help'],(work/'sample.txt').read_text()
            # Exercise the actual installed editor through the workspace input
            # path: Alt+L / Alt+P used to be intercepted by default bindings.
            (work/'search.txt').write_text('FOO foo\n')
            subprocess.run([str(home/'.local/bin/devtui-helix-open'),str(work/'search.txt'),'1','1'],env=env,check=True,timeout=5)
            drain(.35)
            def editor_dump():
                return subprocess.run([args.zellij,'-s',session,'action','dump-screen','--pane-id',pane],env=env,text=True,capture_output=True,check=True,timeout=5).stdout
            os.write(fd,b'\x06foo');drain(.3)
            text=editor_dump();result['find_overlay_visible']='┌─ Find' in text and '2 matches' in text
            assert result['find_overlay_visible'],text
            os.write(fd,b'\x1bl');drain(.25)
            text=editor_dump();result['find_scope_shortcut']='1 matches' in text
            assert result['find_scope_shortcut'],text
            os.write(fd,b'\x08bar');drain(.25)
            text=editor_dump();assert 'Find / Replace' in text and 'bar' in text,text
            os.write(fd,b'\x1bp');drain(.2)
            os.write(fd,b'\x1b[13;7u');drain(.3)
            text=editor_dump();assert '0 matches' in text,text
            os.write(fd,b'\x1b');drain(.2);os.write(fd,b'\x13');drain(.4)
            result['preserve_case_and_replace_all_shortcuts']=(work/'search.txt').read_text()=='BAR foo\n'
            assert result['preserve_case_and_replace_all_shortcuts'],(work/'search.txt').read_text()+editor_dump()
            print(json.dumps(result,indent=2))
        finally:
            subprocess.run([args.zellij,'kill-session',session],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            subprocess.run([args.zellij,'delete-session',session],env=env,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            drain(.2)
            until=time.monotonic()+3
            while time.monotonic()<until:
                try:
                    if os.waitpid(pid,os.WNOHANG)[0]:break
                except ChildProcessError:break
                time.sleep(.05)
            else:
                os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
            os.close(fd)

if __name__=='__main__':main()
