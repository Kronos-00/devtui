#!/usr/bin/env python3
"""Workspace C/C++ properties, exact protocol ordering and real clangd behavior."""
import argparse
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import terminal_regression as tr

HERE=Path(__file__).resolve().parent
COMPILER=shutil.which('clang++') or shutil.which('g++')
CLANGD=shutil.which('clangd')


def messages(log,direction='client',method=None):
    if not log.exists():return []
    result=[]
    for line in log.read_text().splitlines():
        try:item=json.loads(line)
        except json.JSONDecodeError:continue
        if item['direction']==direction and (method is None or item.get('method')==method):result.append(item)
    return result


def language_config(log,real=False):
    args=[str(HERE/'fixtures/cpp_properties_lsp.py'),'proxy' if real else 'fake',str(log)]
    if real:args += [CLANGD,'--background-index=false','--log=error']
    return f'''[language-server.clangd]
command = {json.dumps(sys.executable)}
args = {json.dumps(args)}
config = {{ clangdFileStatus = true }}
[[language]]
name = "cpp"
language-servers = ["clangd"]
auto-format = false
[[language]]
name = "c"
language-servers = ["clangd"]
auto-format = false
'''


def properties(**fields):
    return json.dumps({'configurations':[{'name':'Linux',**fields}],'version':4})


def opened(t,log,path='case.cpp'):
    t.wait_for(lambda:any(item['params']['textDocument']['uri'].endswith('/'+path) for item in messages(log,method='textDocument/didOpen')),'document opened with configuration')


def command_for(log,name):
    commands=[]
    for item in messages(log,method='workspace/didChangeConfiguration'):
        for file,command in item['params']['settings'].get('compilationDatabaseChanges',{}).items():
            if Path(file).name==name:commands.append(command)
    if not commands:raise AssertionError('No compile command for '+name)
    return commands[-1]


def lsp_info(t):
    t.editor_focus();t.send('\x1b');t.send(' ci');t.wait_for(lambda:'Language Servers' in t.text,'LSP info')


class CppPropertiesTests(unittest.TestCase):
    def test_first_open_receives_jsonc_variables_and_compiler_before_parse(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            config='''{
              // JSONC is accepted by VS Code.
              "env": {"roots":["${workspaceFolder}/z include","${workspaceFolder}/a include"],"flag":"FEATURE"},
              "configurations":[{"name":"Linux","compilerPath":"${env:TEST_CPP_COMPILER}",
                "compilerArgs":["-DARG_VALUE=7"],"defines":["${flag}=1"],
                "includePath":["${roots}"],"forcedInclude":["${workspaceFolder}/prelude.h"],
                "cppStandard":"c++20","intelliSenseMode":"linux-clang-x64",}],"version":4,}
            '''
            files={'.vscode/c_cpp_properties.json':config,'case.cpp':'int value;\n','prelude.h':'#define PRELUDE 1\n','z include/z.h':'','a include/a.h':''}
            with tr.Terminal(files,'case.cpp',languages=language_config(log),environment={'TEST_CPP_COMPILER':COMPILER}) as t:
                opened(t,log)
                command=command_for(log,'case.cpp');args=command['compilationCommand']
                self.assertEqual(args[0],COMPILER);self.assertIn('-DFEATURE=1',args);self.assertIn('-DARG_VALUE=7',args)
                self.assertIn('-std=c++20',args);self.assertIn('-m64',args)
                self.assertLess(args.index('-I'+str(t.work/'z include')),args.index('-I'+str(t.work/'a include')))
                self.assertEqual(command['workingDirectory'],str(t.work))
                wire=messages(log);opened_index=next(i for i,item in enumerate(wire) if item.get('method')=='textDocument/didOpen')
                self.assertEqual(wire[opened_index-1]['method'],'workspace/didChangeConfiguration')
                init=messages(log,method='initialize')[0]['params'];self.assertTrue(init['initializationOptions']['clangdFileStatus'])
                argv=messages(log,'start')[0]['argv'];self.assertIn('--query-driver='+COMPILER,argv)
                lsp_info(t);self.assertIn('C/C++ configuration',t.text);self.assertIn('manual configuration',t.text)

    def test_database_entry_wins_and_unmatched_file_uses_manual_configuration(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            with tr.Terminal({'case.cpp':'int value;\n','other.cpp':'int other;\n'},languages=language_config(log)) as t:
                (t.work/'.vscode').mkdir();(t.work/'.vscode/c_cpp_properties.json').write_text(properties(compileCommands='${workspaceFolder}/build/compile_commands.json',defines=['MANUAL=1'],cppStandard='c++20'))
                (t.work/'build').mkdir();args=[COMPILER,'-DDATABASE=1','-std=c++17','case.cpp']
                (t.work/'build/compile_commands.json').write_text(json.dumps([{'directory':str(t.work),'file':'case.cpp','arguments':args}]))
                t.command('edit case.cpp');opened(t,log)
                self.assertEqual(command_for(log,'case.cpp')['compilationCommand'],args)
                init=messages(log,method='initialize')[0]['params'];self.assertEqual(init['initializationOptions']['compilationDatabasePath'],str(t.work/'build'))
                t.command('edit other.cpp');opened(t,log,'other.cpp')
                fallback=command_for(log,'other.cpp')['compilationCommand'];self.assertIn('-DMANUAL=1',fallback);self.assertNotIn('-DDATABASE=1',fallback)

    def test_selected_configuration_environment_and_default_platform(self):
        for selected,expected in [(None,'PLATFORM'),('Custom','CUSTOM')]:
            with self.subTest(selected=selected),tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
                log=Path(tmp)/'wire.jsonl'
                config=json.dumps({'configurations':[{'name':'Custom','defines':['CUSTOM']},{'name':'Linux','defines':['PLATFORM']} ]})
                env={'DEVTUI_CPP_CONFIGURATION':selected} if selected else {}
                with tr.Terminal({'.vscode/c_cpp_properties.json':config,'case.cpp':'int value;\n'},'case.cpp',languages=language_config(log),environment=env) as t:
                    opened(t,log);self.assertIn('-D'+expected,command_for(log,'case.cpp')['compilationCommand'])

    def test_launch_below_configuration_finds_parent_workspace(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';files={'.vscode/c_cpp_properties.json':properties(defines=['PARENT']),'nested/src/case.cpp':'int value;\n'}
            with tr.Terminal(files,'src/case.cpp',languages=language_config(log),directory='nested') as t:
                opened(t,log);self.assertEqual(messages(log,'start')[0]['cwd'],str(t.work))
                self.assertIn('-DPARENT',command_for(log,'case.cpp')['compilationCommand'])

    def test_opened_workspace_configuration_governs_nested_directories(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';files={'.vscode/c_cpp_properties.json':properties(defines=['OUTER']),'case.cpp':'int value;\n',
                'nested/.vscode/c_cpp_properties.json':properties(defines=['INNER']),'nested/inside.cpp':'int inside;\n'}
            with tr.Terminal(files,'case.cpp',languages=language_config(log)) as t:
                opened(t,log);t.command('edit nested/inside.cpp');opened(t,log,'inside.cpp')
                self.assertEqual(len(messages(log,'start')),1)
                self.assertIn('-DOUTER',command_for(log,'case.cpp')['compilationCommand'])
                self.assertIn('-DOUTER',command_for(log,'inside.cpp')['compilationCommand'])
                self.assertNotIn('-DINNER',command_for(log,'inside.cpp')['compilationCommand'])

    def test_external_projects_do_not_share_a_clangd_configuration(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';outside=Path(tmp)/'other-project';(outside/'.vscode').mkdir(parents=True)
            (outside/'.vscode/c_cpp_properties.json').write_text(properties(defines=['EXTERNAL']))
            (outside/'outside.cpp').write_text('int outside;\n')
            files={'.vscode/c_cpp_properties.json':properties(defines=['CURRENT']),'case.cpp':'int value;\n'}
            with tr.Terminal(files,'case.cpp',languages=language_config(log)) as t:
                opened(t,log)
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                    client.settimeout(2);client.connect(str(t.sock));client.sendall((json.dumps({'path':str(outside/'outside.cpp'),'line':1,'column':1})+'\n').encode())
                opened(t,log,'outside.cpp')
                self.assertEqual(len(messages(log,'start')),2)
                self.assertIn('-DCURRENT',command_for(log,'case.cpp')['compilationCommand'])
                self.assertIn('-DEXTERNAL',command_for(log,'outside.cpp')['compilationCommand'])
                self.assertNotIn('-DCURRENT',command_for(log,'outside.cpp')['compilationCommand'])

    def test_c_and_cpp_receive_their_own_standard_in_one_project(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';files={'.vscode/c_cpp_properties.json':properties(cStandard='c11',cppStandard='c++20'),'case.c':'int value;\n','other.cpp':'int other;\n'}
            with tr.Terminal(files,'case.c',languages=language_config(log)) as t:
                opened(t,log,'case.c');t.command('edit other.cpp');opened(t,log,'other.cpp')
                self.assertIn('-std=c11',command_for(log,'case.c')['compilationCommand'])
                self.assertIn('-std=c++20',command_for(log,'other.cpp')['compilationCommand'])
                self.assertEqual(len(messages(log,'start')),1)

    def test_invalid_configuration_is_reported_without_blocking_language_server(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            with tr.Terminal({'.vscode/c_cpp_properties.json':'{broken','case.cpp':'int value;\n'},'case.cpp',languages=language_config(log)) as t:
                opened(t,log);self.assertFalse(any('compilationDatabaseChanges' in item['params']['settings'] for item in messages(log,method='workspace/didChangeConfiguration')))
                lsp_info(t);self.assertIn('Configuration warning',t.text);self.assertIn('C/C++ configuration',t.text)

    def test_missing_database_falls_back_with_warning(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            with tr.Terminal({'.vscode/c_cpp_properties.json':properties(compileCommands='missing.json',defines=['FALLBACK']),'case.cpp':'int value;\n'},'case.cpp',languages=language_config(log)) as t:
                opened(t,log);self.assertIn('-DFALLBACK',command_for(log,'case.cpp')['compilationCommand'])
                lsp_info(t);self.assertIn('Configuration warning',t.text)

    def test_no_properties_file_preserves_existing_clangd_configuration(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            with tr.Terminal({'case.cpp':'int value;\n'},'case.cpp',languages=language_config(log)) as t:
                opened(t,log);self.assertFalse(any('compilationDatabaseChanges' in item['params']['settings'] for item in messages(log,method='workspace/didChangeConfiguration')))
                self.assertEqual(messages(log,method='initialize')[0]['params']['initializationOptions'],{'clangdFileStatus':True})
                self.assertEqual(messages(log,'start')[0]['argv'],[])

    def test_configuration_provider_is_explicitly_reported_as_unsupported(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl'
            with tr.Terminal({'.vscode/c_cpp_properties.json':properties(configurationProvider='example.provider',defines=['BASE']),'case.cpp':'int value;\n'},'case.cpp',languages=language_config(log)) as t:
                opened(t,log);self.assertIn('-DBASE',command_for(log,'case.cpp')['compilationCommand'])
                lsp_info(t);self.assertIn('Configuration warning',t.text)

    def test_real_clangd_macros_includes_and_database_precedence_change_definition(self):
        for mode in ['manual-blue','manual-red','database-red','unmatched-blue']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
                log=Path(tmp)/'wire.jsonl'
                manual=mode!='database-red';blue=mode!='manual-red';std=202002 if manual else 201703;arg=7 if manual else 17
                checks=f'#if __cplusplus != {std}L || ARG_VALUE != {arg}\n#error incorrect compile configuration\n#endif\n'
                checks+='#ifndef FORCED\n#error missing forced include\n#endif\n' if manual else '#ifdef FORCED\n#error manual configuration leaked into database command\n#endif\n'
                source=checks+'#include "choice.hpp"\nint main(){return chosen_value;}\n'
                config=properties(compilerPath=COMPILER,compilerArgs=['-DARG_VALUE=7'],defines=['USE_BLUE'] if blue else [],includePath=['${workspaceFolder}/include'],forcedInclude=['${workspaceFolder}/prelude.h'],cppStandard='c++20')
                files={'.vscode/c_cpp_properties.json':config,'case.cpp':source,'prelude.h':'#define FORCED 1\n',
                    'include/choice.hpp':'#ifdef USE_BLUE\n#include "blue.hpp"\n#else\n#include "red.hpp"\n#endif\n',
                    'include/blue.hpp':'inline int chosen_value = 7;\n','include/red.hpp':'inline int chosen_value = 17;\n'}
                with tr.Terminal(files,languages=language_config(log,True)) as t:
                    if mode in ('database-red','unmatched-blue'):
                        props=json.loads(config);props['configurations'][0]['compileCommands']='${workspaceFolder}/build/compile_commands.json'
                        (t.work/'.vscode/c_cpp_properties.json').write_text(json.dumps(props));(t.work/'build').mkdir()
                        target='case.cpp' if mode=='database-red' else 'other.cpp'
                        (t.work/'build/compile_commands.json').write_text(json.dumps([{'directory':str(t.work),'file':target,'arguments':[COMPILER,'-I'+str(t.work/'include'),'-DARG_VALUE=17','-std=c++17',target]}]))
                    t.command('edit case.cpp');opened(t,log)
                    uri=(t.work/'case.cpp').as_uri()
                    t.wait_for(lambda:any(item['params']['uri']==uri for item in messages(log,'server','textDocument/publishDiagnostics')),'real diagnostics',timeout=12)
                    diagnostics=[item['params']['diagnostics'] for item in messages(log,'server','textDocument/publishDiagnostics') if item['params']['uri']==uri][-1]
                    self.assertEqual(diagnostics,[])
                    row=len(source.splitlines());t.click(61,row,2);t.click_text('Go to Definition',exact=True)
                    expected='blue.hpp' if blue and manual else 'red.hpp'
                    t.wait_for(lambda:expected in t.screen.display[0],'configured definition target',timeout=8)

    def test_real_c_language_uses_c_standard_and_forced_include(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';source='#if __STDC_VERSION__ != 201112L || VALUE != 9\n#error incorrect C configuration\n#endif\nint main(void){return VALUE;}\n'
            files={'.vscode/c_cpp_properties.json':properties(compilerPath=COMPILER,cStandard='c11',cppStandard='c++20',forcedInclude=['${workspaceFolder}/prelude.h']),'case.c':source,'prelude.h':'#define VALUE 9\n'}
            with tr.Terminal(files,'case.c',languages=language_config(log,True)) as t:
                opened(t,log,'case.c');uri=(t.work/'case.c').as_uri()
                t.wait_for(lambda:any(item['params']['uri']==uri for item in messages(log,'server','textDocument/publishDiagnostics')),'C diagnostics',timeout=12)
                self.assertEqual([item['params']['diagnostics'] for item in messages(log,'server','textDocument/publishDiagnostics') if item['params']['uri']==uri][-1],[])

    def test_lsp_restart_reloads_modified_configuration(self):
        with tempfile.TemporaryDirectory(prefix='cpp-properties-') as tmp:
            log=Path(tmp)/'wire.jsonl';files={'.vscode/c_cpp_properties.json':properties(defines=['BEFORE']),'case.cpp':'int value;\n'}
            with tr.Terminal(files,'case.cpp',languages=language_config(log)) as t:
                opened(t,log);self.assertIn('-DBEFORE',command_for(log,'case.cpp')['compilationCommand'])
                (t.work/'.vscode/c_cpp_properties.json').write_text(properties(defines=['AFTER']))
                t.command('lsp-restart')
                t.wait_for(lambda:len(messages(log,'start'))==2 and '-DAFTER' in command_for(log,'case.cpp')['compilationCommand'],'reloaded configuration')
                self.assertNotIn('-DBEFORE',command_for(log,'case.cpp')['compilationCommand'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True,type=Path);parser.add_argument('--runtime',required=True,type=Path);parser.add_argument('--filter',default='')
    args=parser.parse_args();tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CppPropertiesTests)
    if args.filter:suite=unittest.TestSuite(test for test in suite if args.filter in test.id())
    result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())
