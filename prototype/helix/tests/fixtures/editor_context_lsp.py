#!/usr/bin/env python3
"""Disposable formatting provider for capability, expansion and async tests."""
import json
from pathlib import Path
import sys
import time

mode, output = sys.argv[1:]
text = ''

def send(message):
    data=json.dumps(message).encode()
    sys.stdout.buffer.write(f'Content-Length: {len(data)}\r\n\r\n'.encode()+data)
    sys.stdout.buffer.flush()

while True:
    headers={}
    while True:
        line=sys.stdin.buffer.readline()
        if not line: raise SystemExit(0)
        if line in (b'\r\n',b'\n'): break
        key,value=line.decode().split(':',1);headers[key.lower()]=value.strip()
    message=json.loads(sys.stdin.buffer.read(int(headers['content-length'])))
    with Path(output).open('a') as log: log.write(json.dumps(message)+'\n')
    method=message.get('method');params=message.get('params',{})
    if method=='textDocument/didOpen': text=params['textDocument']['text']
    if method=='textDocument/didChange': text=params['contentChanges'][-1]['text']
    if method=='exit': break
    if 'id' not in message: continue
    result=None
    if method=='initialize':
        result={'capabilities':{'positionEncoding':'utf-16','textDocumentSync':1,
            'documentFormattingProvider':mode!='range-only',
            'documentRangeFormattingProvider':mode!='doc-only'}}
    elif method in ('textDocument/formatting','textDocument/rangeFormatting'):
        if mode=='failure':
            send({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32603,'message':'format rejected\nsecond line'}})
            continue
        if mode=='delayed': time.sleep(.8)
        lines=text.split('\n')
        result=[{'range':{'start':{'line':0,'character':0},
            'end':{'line':len(lines)-1,'character':len(lines[-1].encode('utf-16-le'))//2}},
            'newText':text.replace('RAW','FORMATTED')}]
    send({'jsonrpc':'2.0','id':message['id'],'result':result})
