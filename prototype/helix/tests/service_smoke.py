#!/usr/bin/env python3
"""Bounded protocol smoke tests for real LSP/DAP executables; no user projects."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time

class Protocol:
    def __init__(self, command, env, cwd):
        self.stderr = tempfile.TemporaryFile()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, env=env, cwd=cwd)
        self.buffer = bytearray()
        self.seq = 0
    def send(self, value):
        payload = json.dumps(value).encode()
        self.process.stdin.write(f'Content-Length: {len(payload)}\r\n\r\n'.encode()+payload)
        self.process.stdin.flush()
    def read(self, deadline):
        while time.monotonic() < deadline:
            header_end=self.buffer.find(b'\r\n\r\n')
            if header_end>=0:
                headers=dict(line.split(b':',1) for line in bytes(self.buffer[:header_end]).split(b'\r\n'))
                size=int(headers[b'Content-Length'])
                if len(self.buffer)>=header_end+4+size:
                    value=json.loads(self.buffer[header_end+4:header_end+4+size])
                    del self.buffer[:header_end+4+size]
                    return value
            ready,_,_=select.select([self.process.stdout],[],[],.05)
            if ready:
                data=os.read(self.process.stdout.fileno(),65536)
                if not data:
                    self.stderr.seek(0)
                    raise RuntimeError(self.stderr.read(4000).decode(errors='replace'))
                self.buffer.extend(data)
        raise TimeoutError('protocol response timed out')
    def wait(self,predicate,timeout=12):
        deadline=time.monotonic()+timeout
        while True:
            msg=self.read(deadline)
            if predicate(msg):return msg
            # Some language servers request settings during initialization.
            if 'method' in msg and 'id' in msg:
                result=[{} for _ in msg.get('params',{}).get('items',[])] if msg['method']=='workspace/configuration' else None
                self.send({'jsonrpc':'2.0','id':msg['id'],'result':result})
    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.stderr.close()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tools',type=Path,required=True)
    args=ap.parse_args()
    env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None);env['PATH']=str(args.tools.resolve())+os.pathsep+env.get('PATH','')
    results={}
    with tempfile.TemporaryDirectory(prefix='devtui-services-') as temporary:
        work=Path(temporary);(work/'sample.cpp').write_text('#if 0\nint inactive;\n#endif\nint live;\n')
        for name,command in {
            'clangd':['clangd','--log=error'], 'pyright':['pyright-langserver','--stdio'],
            'bash':['bash-language-server','start'], 'cmake':['cmake-language-server'],
            'ruff':['ruff','server'],
        }.items():
            executable=shutil.which(command[0],path=env['PATH'])
            if not executable:results[name]={'error':'executable missing'};continue
            client=Protocol([executable,*command[1:]],env,work)
            try:
                client.send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
                    'processId':os.getpid(),'rootUri':work.as_uri(),'rootPath':str(work),
                    'capabilities':{'textDocument':{'inactiveRegionsCapabilities':{'inactiveRegions':True}}},
                    'workspaceFolders':[{'name':'test','uri':work.as_uri()}],
                }})
                response=client.wait(lambda msg:msg.get('id')==1)
                assert 'result' in response and 'capabilities' in response['result'],response
                results[name]={'initialize':'PASS'}
                client.send({'jsonrpc':'2.0','method':'initialized','params':{}})
                if name=='clangd':
                    client.send({'jsonrpc':'2.0','method':'textDocument/didOpen','params':{'textDocument':{
                        'uri':(work/'sample.cpp').as_uri(),'languageId':'cpp','version':1,
                        'text':(work/'sample.cpp').read_text(),
                    }}})
                    msg=client.wait(lambda m:m.get('method')=='textDocument/inactiveRegions')
                    assert msg.get('params'),msg
                    results[name]['inactive_regions']='PASS'
                client.send({'jsonrpc':'2.0','id':2,'method':'shutdown','params':None})
                client.wait(lambda m:m.get('id')==2,timeout=3)
                client.send({'jsonrpc':'2.0','method':'exit','params':None})
            except Exception as error:results[name]={'error':str(error)}
            finally:client.close()
        for name in ['debugpy-adapter','lldb-dap']:
            executable=shutil.which(name,path=env['PATH'])
            if not executable:results[name]={'error':'executable missing'};continue
            client=Protocol([executable],env,work)
            try:
                client.send({'seq':1,'type':'request','command':'initialize','arguments':{
                    'clientID':'devtui-regression','adapterID':name,
                    'linesStartAt1':True,'columnsStartAt1':True,'pathFormat':'path',
                    'supportsVariableType':True,'supportsRunInTerminalRequest':False,
                }})
                response=client.wait(lambda msg:msg.get('request_seq')==1)
                assert response.get('success'),response
                results[name]={'initialize':'PASS'}
                client.send({'seq':2,'type':'request','command':'disconnect','arguments':{}})
            except Exception as error:results[name]={'error':str(error)}
            finally:client.close()
        # The services, unlike the user's shell, must not load a project's
        # PYTHONPATH/PYTHONHOME into their privately locked dependencies.
        poison=work/'python-startup';poison.mkdir()
        (poison/'pygls.py').write_text('raise RuntimeError("project injection")\n')
        (poison/'debugpy.py').write_text('raise RuntimeError("project injection")\n')
        polluted=env.copy();polluted['PYTHONPATH']=str(poison);polluted['PYTHONHOME']=str(work/'missing-python-home')
        for name,command in [('cmake-isolation','cmake-language-server'),('debugpy-isolation','debugpy-adapter')]:
            executable=shutil.which(command,path=env['PATH'])
            if not executable:results[name]={'error':'executable missing'};continue
            client=Protocol([executable],polluted,work)
            try:
                if name.startswith('cmake'):
                    client.send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'processId':os.getpid(),'rootUri':work.as_uri(),'capabilities':{}}})
                    response=client.wait(lambda msg:msg.get('id')==1)
                    assert 'result' in response,response
                else:
                    client.send({'seq':1,'type':'request','command':'initialize','arguments':{'adapterID':'python','clientID':'devtui-regression'}})
                    response=client.wait(lambda msg:msg.get('request_seq')==1)
                    assert response.get('success'),response
                results[name]={'initialize':'PASS','isolated_runtime':'PASS'}
            except Exception as error:results[name]={'error':str(error)}
            finally:client.close()
    print(json.dumps(results,indent=2))
    return int(any('error' in value for value in results.values()))
if __name__=='__main__':raise SystemExit(main())
