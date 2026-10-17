#!/usr/bin/env python3
"""Configuration-only deployment and shell-environment checks in temporary homes."""
from pathlib import Path
import ast
import json
import os
import pty
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]

class DeploymentTests(unittest.TestCase):
    def test_install_isolated_and_backed_up(self):
        with tempfile.TemporaryDirectory(prefix='devtui-install-') as directory:
            home=Path(directory)/'home with spaces';home.mkdir()
            files={'.config/nvim/init.lua':'-- user configuration\n',
                   '.local/bin/devtui':'existing launcher\n',
                   '.local/bin/devtui-shell-pane':'existing shell helper\n',
                   '.bashrc':'export DO_NOT_CHANGE=1\n'}
            for name,text in files.items():
                p=home/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            env=os.environ.copy();env['HOME']=str(home)
            legacy=home/'.local/bin/devtui-helix-banner';legacy.write_text('legacy banner\n')
            command=[str(ROOT/'prototype/helix/install-prototype.sh'),'--config-only']
            subprocess.run(command,env=env,check=True,stdout=subprocess.PIPE)
            for name,text in files.items():self.assertEqual((home/name).read_text(),text)
            self.assertFalse(legacy.exists())
            self.assertTrue(any(p.read_text()=='legacy banner\n' for p in (home/'.local/state/devtui').glob('helix-backup-*/.local/bin/devtui-helix-banner')))
            cfg=home/'.config/devtui-helix/helix/config.toml'
            self.assertTrue(cfg.exists());cfg.write_text('# prior Helix settings\n')
            subprocess.run(command,env=env,check=True,stdout=subprocess.PIPE)
            backups=list((home/'.local/state/devtui').glob('helix-backup-*/.config/devtui-helix/helix/config.toml'))
            self.assertTrue(any(p.read_text()=='# prior Helix settings\n' for p in backups))
            for p in (home/'.config/devtui-helix').rglob('*'):
                if p.is_file():self.assertNotIn('__HOME__',p.read_text())

    def test_shell_keeps_exported_development_environment(self):
        with tempfile.TemporaryDirectory(prefix='devtui-env-') as directory:
            home=Path(directory)
            (home/'.bashrc').write_text('export SHOULD_NOT_LOAD=YES\nexport CC=wrong\n')
            (home/'.profile').write_text('export SHOULD_NOT_LOAD=YES\n')
            env=os.environ.copy();env.update(HOME=str(home), CC='custom-cc', CXX='custom-cxx',
                SDKROOT='/example/sdk', PATH='/usr/local/bin:/usr/bin:/bin',
                TEST_EXPORTED_VALUE='inherited', DEVTUI_HELIX_SOCKET='private',
                DEVTUI_HELIX_EDITOR_PANE_FILE='private', TERM='xterm-256color')
            startup=home/'noninteractive-startup';startup.write_text('export SHOULD_NOT_LOAD=YES\nexport CC=wrong\n')
            env['BASH_ENV']=str(startup)
            env['BASH_FUNC_devtui_probe%%']='() { echo inherited-function; }'
            result=subprocess.run([str(ROOT/'prototype/helix/bin/devtui-helix-shell-pane')],
                env=env,input="printf '%s\\n' CHECK_BEGIN \"$CC\" \"$CXX\" \"$SDKROOT\" \"$PATH\" \"$TEST_EXPORTED_VALUE\" \"${SHOULD_NOT_LOAD-unset}\" \"${DEVTUI_HELIX_SOCKET-unset}\" \"${DEVTUI_HELIX_EDITOR_PANE_FILE-unset}\" CHECK_END\nexit\n",
                text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=True,start_new_session=True)
            actual=result.stdout.split('CHECK_BEGIN\n',1)[1].split('CHECK_END',1)[0].splitlines()
            self.assertEqual(actual,['custom-cc','custom-cxx','/example/sdk',env['PATH'],'inherited','unset','unset','unset'])

    def test_shell_scripts_parse(self):
        scripts=[ROOT/'prototype/helix/install-prototype.sh']
        scripts+=list((ROOT/'prototype/helix/scripts').glob('*.sh'))
        scripts+=list((ROOT/'prototype/helix/bin').glob('*'))
        for script in scripts:
            if 'python' in script.read_text().splitlines()[0]:
                ast.parse(script.read_text(),filename=str(script))
            else:
                subprocess.run(['bash','-n',str(script)],check=True)

    def test_launcher_scope_and_environment(self):
        with tempfile.TemporaryDirectory(prefix='devtui-launch-') as directory:
            base=Path(directory);home=base/'home';home.mkdir();project=base/'project';project.mkdir()
            tools=base/'bin';tools.mkdir();output=base/'args.json'
            fake=tools/'zellij'
            fake.write_text('#!/usr/bin/env -S python3 -I -S\nimport os,sys,json\nopen(os.environ["OUTPUT"],"w").write(json.dumps({"args":sys.argv,"cwd":os.getcwd(),"cc":os.environ.get("CC"),"sentinel":os.environ.get("STARTUP_RAN"),"function":os.environ.get("BASH_FUNC_devtui_probe%%")}))\n')
            fake.chmod(0o755)
            startup=base/'startup';startup.write_text('export STARTUP_RAN=yes\nexport CC=wrong\n')
            env=os.environ.copy();env.update(HOME=str(home),PATH=str(tools)+':/usr/local/bin:/usr/bin:/bin',BASH_ENV=str(startup),CC='custom-cc',OUTPUT=str(output))
            env['BASH_FUNC_devtui_probe%%']='() { echo inherited-function; }'
            for columns,layout in [('120','dev-helix.kdl'),('240','dev-helix-wide.kdl')]:
                env['DEVTUI_COLUMNS']=columns
                subprocess.run([str(ROOT/'prototype/helix/bin/devtui-helix'),str(project)],env=env,check=True)
                result=json.loads(output.read_text())
                self.assertTrue(result['args'][-1].endswith(layout));self.assertEqual(result['cwd'],str(project))
                self.assertEqual(result['cc'],'custom-cc');self.assertIsNone(result['sentinel'])
                self.assertEqual(result['function'],env['BASH_FUNC_devtui_probe%%'])
            native=home/'.local/opt/devtui/helix-prototype/bin/zellij';native.parent.mkdir(parents=True);native.write_text(fake.read_text());native.chmod(0o755)
            assets=native.parent.parent/'share/zellij';assets.mkdir(parents=True)
            subprocess.run([str(ROOT/'prototype/helix/bin/devtui-helix'),str(project)],env=env,check=True)
            result=json.loads(output.read_text());self.assertEqual(result['args'][0],str(native));self.assertIn('--data-dir',result['args']);self.assertIn(str(assets),result['args'])

    def test_navigation_client_ignores_project_python_startup(self):
        import socket
        with tempfile.TemporaryDirectory(prefix='devtui-open-client-') as directory:
            base=Path(directory);endpoint=base/'editor.sock';target=base/'file with spaces.txt'
            target.write_text('unchanged\n');marker=base/'should-not-run'
            (base/'json.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\nraise RuntimeError("project module imported")\n')
            (base/'sitecustomize.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
            env=os.environ.copy();env.update(DEVTUI_HELIX_SOCKET=str(endpoint),PYTHONPATH=str(base))
            env.pop('BASH_ENV',None);env.pop('PYTHONHOME',None)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(str(endpoint));server.listen(1);server.settimeout(3)
                subprocess.run([str(ROOT/'prototype/helix/bin/devtui-helix-open'),str(target),'2','3'],env=env,cwd=base,check=True,timeout=5)
                conn,_=server.accept()
                with conn:payload=json.loads(conn.recv(4096))
            self.assertEqual(payload,{'path':str(target),'line':2,'column':3})
            self.assertFalse(marker.exists())
            self.assertEqual(target.read_text(),'unchanged\n')

    def test_workspace_has_no_banner_and_global_f4_help(self):
        for name in ['dev-helix.kdl.in','dev-helix-wide.kdl.in']:
            text=(ROOT/'prototype/helix/zellij'/name).read_text()
            self.assertNotIn('devtui-helix-banner',text)
            self.assertNotIn('name="shortcuts"',text)
            self.assertIn('F4 shortcuts',text)
        config=(ROOT/'prototype/helix/zellij/zellij.kdl.in').read_text()
        self.assertIn('bind "F4"',config)
        self.assertIn('MessagePlugin',config)
        self.assertIn('floating true',config)
        self.assertFalse((ROOT/'prototype/helix/bin/devtui-helix-banner').exists())

if __name__=='__main__':unittest.main(verbosity=2)
