#!/usr/bin/env python3
"""Record clangd protocol wiring; optionally proxy a real clangd process."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

mode, logfile = sys.argv[1:3]
lock=threading.Lock()
def record(direction,message):
    with lock,Path(logfile).open('a') as output:
        output.write(json.dumps({'direction':direction,**message})+'\n')

def read(stream):
    headers={};raw=bytearray()
    while True:
        line=stream.readline()
        if not line:return None
        raw.extend(line)
        if line in (b'\r\n',b'\n'):break
        key,value=line.decode().split(':',1);headers[key.lower()]=value.strip()
    size=int(headers['content-length']);data=stream.read(size)
    if len(data)!=size:return None
    return bytes(raw)+data,json.loads(data)

def send(message):
    data=json.dumps(message).encode()
    sys.stdout.buffer.write(f'Content-Length: {len(data)}\r\n\r\n'.encode()+data);sys.stdout.buffer.flush()

record('start',{'argv':sys.argv[3:],'cwd':str(Path.cwd())})
if mode=='proxy':
    process=subprocess.Popen(sys.argv[3:],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=sys.stderr.buffer)
    def pump(source,target,direction):
        try:
            while (item:=read(source)) is not None:
                data,message=item;record(direction,message);target.write(data);target.flush()
        except (BrokenPipeError,OSError):pass
        finally:
            try:target.close()
            except OSError:pass
    threading.Thread(target=pump,args=(sys.stdin.buffer,process.stdin,'client'),daemon=True).start()
    pump(process.stdout,sys.stdout.buffer,'server')
    raise SystemExit(process.wait())

while (item:=read(sys.stdin.buffer)) is not None:
    _,message=item;record('client',message)
    method=message.get('method')
    if method=='exit':break
    if 'id' not in message:continue
    result=None
    if method=='initialize':
        time.sleep(.1)
        result={'capabilities':{'positionEncoding':'utf-16','textDocumentSync':1,'definitionProvider':True,
            'workspace':{'workspaceFolders':{'supported':True,'changeNotifications':True}}}}
    send({'jsonrpc':'2.0','id':message['id'],'result':result})
