#!/usr/bin/env python3
"""Exercise real F9/F5/debug-menu flows in the terminal editor itself."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr

PROGRAM = ('value = 1\nvalue += 2\nimport sys\n'
           'open("result.txt", "w").write(str(value) + "|" + sys.prefix)\n')

class EditorDebugger(unittest.TestCase):
    def palette(self, terminal, name):
        terminal.send('\x1bOP', .15)
        terminal.send(name, .15)
        terminal.send('\r', .25)

    def variables(self, terminal, expected):
        self.palette(terminal, 'devtui_debug_menu')
        terminal.wait_for(lambda:'Run and Debug' in terminal.text, 'debug menu')
        terminal.click_text('Variables')
        terminal.wait_for(lambda:f'value: int = {expected}' in terminal.text, 'real debug variables')
        terminal.send('\x1b', .15)

    def launch(self, terminal):
        terminal.click(42, 2)
        terminal.send('\x1b[20~')  # F9: breakpoint at the second source line.
        terminal.send('\x1b[15~', .2)  # F5: start debug.
        terminal.wait_for(lambda:'launch file' in terminal.text, 'debug template')
        terminal.send('\r', .2)
        terminal.wait_for(lambda:'program:' in terminal.text.lower(), 'program prompt')
        terminal.send('\x15sample.py', .25)
        terminal.send('\r', .3)
        terminal.wait_for(lambda:'▶' in terminal.screen.display[2], 'breakpoint stop', timeout=15)
        self.assertEqual(os.tcgetpgrp(terminal.fd), terminal.pid,
                         'debuggee stole the editor controlling terminal')

    def test_f5_python_fallback_variables_step_and_continue(self):
        with tr.Terminal({'sample.py':PROGRAM}, 'sample.py') as t:
            self.launch(t)
            self.variables(t, 1)
            t.send('\x1b[21~', .2)  # F10: step over value += 2.
            t.wait_for(lambda:'▶' in t.screen.display[3], 'step over', timeout=10)
            self.variables(t, 3)
            self.palette(t, 'devtui_debug_menu')
            t.wait_for(lambda:'Call Stack' in t.text, 'stack action')
            t.click_text('Call Stack')
            t.wait_for(lambda:'<module>' in t.text, 'real call stack')
            t.send('\x1b', .1)
            t.send('\x1b[15~', .2)
            t.wait_for(lambda:(t.work/'result.txt').exists(), 'continued program completed', timeout=10)
            self.assertTrue((t.work/'result.txt').read_text().startswith('3|'))
            self.assertIn('EXPLORER', t.text)
            self.assertNotIn('panicked', bytes(t.raw).decode(errors='replace'))

    def test_selected_environment_is_used_by_debuggee(self):
        with tr.Terminal({'sample.py':PROGRAM}, 'sample.py') as t:
            python = shutil.which('python3')
            self.assertIsNotNone(python)
            venv=t.work/'.venv'
            subprocess.run([python,'-m','venv','--without-pip',str(venv)],check=True,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            t.editor_focus()
            self.palette(t,'devtui_python_venv')
            t.wait_for(lambda:'Python Environment:' in t.text,'interpreter prompt')
            t.send('\x15.venv', .15);t.send('\r', .3)
            t.wait_for(lambda:'Python Environment:' not in t.text,'interpreter accepted')
            self.launch(t)
            t.send('\x1b[15~', .2)
            t.wait_for(lambda:(t.work/'result.txt').exists(),'selected interpreter completed',timeout=10)
            self.assertEqual((t.work/'result.txt').read_text(),'3|'+str(venv))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--tools',type=Path,required=True)
    args=parser.parse_args()
    tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    os.environ['PATH']=str(args.tools.resolve())+os.pathsep+os.environ.get('PATH','')
    # The fallback scenario must not borrow a virtualenv from the test runner.
    os.environ.pop('VIRTUAL_ENV',None)
    unittest.main(argv=[sys.argv[0]],verbosity=2)
