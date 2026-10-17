#!/usr/bin/env python3
"""Real disposable Python/C debug sessions, beyond DAP initialize smoke tests."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_smoke import Protocol

class DebugSession(Protocol):
    def __init__(self, command, env, cwd):
        super().__init__(command,env,cwd);self.sequence=0;self.backlog=[]
    def request(self, command, arguments):
        self.sequence+=1;self.send({'seq':self.sequence,'type':'request','command':command,'arguments':arguments});return self.sequence
    def take(self, predicate, timeout=15):
        for i,item in enumerate(self.backlog):
            if predicate(item):return self.backlog.pop(i)
        deadline=time.monotonic()+timeout
        while True:
            try: item=self.read(deadline)
            except TimeoutError as error: raise TimeoutError(str(error)+'; pending='+json.dumps(self.backlog[-4:])) from error
            if item.get('type')=='response' and not item.get('success',True): raise AssertionError(item)
            if predicate(item):return item
            self.backlog.append(item)
    def response(self, sequence):
        result=self.take(lambda m:m.get('request_seq')==sequence)
        assert result.get('success'),result
        return result.get('body',{})
    def event(self, name):return self.take(lambda m:m.get('event')==name)

def run_session(adapter,env,work,language):
    if language=='python':
        program=work/'sample.py';program.write_text('value = 1\nvalue += 2\nprint(value)\n')
        line=2;args={'program':str(program),'python':[sys.executable],'console':'internalConsole','justMyCode':True}
    else:
        source=work/'sample.c';source.write_text('int main(void) {\n  int value = 1;\n  value += 2;\n  return value;\n}\n')
        program=work/'sample';subprocess.run(['/usr/bin/cc','-g','-O0',str(source),'-o',str(program)],check=True)
        program_source=source;line=3
        args={'program':str(program),'cwd':str(work),'disableASLR':False,'initCommands':['settings set target.disable-aslr false']}
    source=program if language=='python' else program_source
    client=DebugSession([adapter],env,work);result={}
    try:
        client.response(client.request('initialize',{'clientID':'devtui-test','adapterID':language,'linesStartAt1':True,'columnsStartAt1':True,'pathFormat':'path','supportsRunInTerminalRequest':False,'supportsVariableType':True}))
        launch=client.request('launch',args);client.event('initialized')
        bps=client.response(client.request('setBreakpoints',{'source':{'path':str(source)},'breakpoints':[{'line':line}]}))
        assert bps.get('breakpoints') and all(b.get('verified') for b in bps['breakpoints']),bps
        result['breakpoint']='PASS'
        client.response(client.request('configurationDone',{}));client.response(launch)
        stop=client.event('stopped');thread=stop['body']['threadId'];result['launch_and_stop']='PASS'
        stack=client.response(client.request('stackTrace',{'threadId':thread}));frame=stack['stackFrames'][0]
        assert frame.get('line')==line,frame;result['call_stack']='PASS'
        scopes=client.response(client.request('scopes',{'frameId':frame['id']}))['scopes']
        all_variables=[]
        for scope in scopes:
            all_variables+=client.response(client.request('variables',{'variablesReference':scope['variablesReference']})).get('variables',[])
        assert any(v['name']=='value' for v in all_variables),all_variables;result['variables']='PASS'
        client.response(client.request('next',{'threadId':thread}));client.event('stopped');result['step_over']='PASS'
        client.response(client.request('continue',{'threadId':thread}));client.event('terminated');result['continue_and_terminate']='PASS'
        client.request('disconnect',{'terminateDebuggee':True})
    finally:client.close()
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tools',type=Path,required=True);args=ap.parse_args()
    env=os.environ.copy();env.pop('DEBUGINFOD_URLS',None);env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None);env['PATH']=str(args.tools.resolve())+os.pathsep+env.get('PATH','')
    results={}
    with tempfile.TemporaryDirectory(prefix='devtui-dap-') as path:
        for name,lang in [('debugpy-adapter','python'),('lldb-dap','c')]:
            work=Path(path)/lang;work.mkdir()
            adapter=shutil.which(name,path=env['PATH'])
            try:
                if not adapter:raise RuntimeError('adapter missing')
                results[name]=run_session(adapter,env,work,lang)
            except Exception as error:results[name]={'error':str(error)}
    print(json.dumps(results,indent=2));return int(any('error' in r for r in results.values()))
if __name__=='__main__':raise SystemExit(main())
