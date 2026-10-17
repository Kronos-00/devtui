#!/usr/bin/env python3
"""A disposable pane whose input can be audited without editing user files."""
import json,os,select,signal,sys,termios,tty
from pathlib import Path
name,log=sys.argv[1:3];dirty=True;old=termios.tcgetattr(0)
def resized(*args):
 global dirty
 dirty=True
signal.signal(signal.SIGWINCH,resized)
try:
 tty.setraw(0)
 while True:
  if dirty:
   width,height=os.get_terminal_size(1);rows=[name+'_UNDERLAY']+[name+' '+str(i)+' '+('.'*max(0,width-len(name)-8)) for i in range(1,height)]
   sys.stdout.write(('\x1b[?1000h\x1b[?1002h\x1b[?1006h' if name=='EDITOR' else '')+'\x1b[2J\x1b[H'+'\r\n'.join(row[:width] for row in rows[:height])+'\x1b[H');sys.stdout.flush();dirty=False
  if select.select([sys.stdin],[],[],.05)[0]:
   data=os.read(0,4096)
   if not data:break
   with Path(log).open('a') as output:output.write(json.dumps({'pane':name,'hex':data.hex()})+'\n')
finally:termios.tcsetattr(0,termios.TCSANOW,old)
