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
    parser.add_argument('--zellij',default=shutil.which('zellij'))
    args=parser.parse_args()
    if not args.zellij: parser.error('Zellij is not installed')
    home=args.home.resolve()
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
        command=[args.zellij,'--session',session,'--config',str(home/'.config/devtui-helix/zellij.kdl'),
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
                    'shortcut_banner_visible':'devtui-helix' in text,
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
