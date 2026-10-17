#!/usr/bin/env python3
"""Verify real language-server features through the editor, not just initialize."""
import argparse
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr

class LanguageEditor(unittest.TestCase):
    def test_clangd_definition_rename_and_overview_diagnostic(self):
        content = 'int answer = 42;\nint use() { return answer; }\n'
        content += ''.join(f'// line {i}\n' for i in range(3,145)) + 'int bad = missing;\n'
        with tr.Terminal({'main.cpp':content},'main.cpp') as t:
            t.editor_focus()
            t.wait_for(lambda: any(row[-2]=='!' for row in t.screen.display[:-2]), 'language diagnostic in overview ruler', timeout=12)
            x,y=t.find('return answer');t.click(x+7,y);t.send('\x1b[24~',.3)
            t.wait_for(lambda:t.screen.cursor.y==1,'definition response')
            t.send('\x1bOQ',.3)
            t.wait_for(lambda:'rename-to' in t.text.lower() or 'rename' in t.text.lower(), 'rename prompt')
            t.send('\x15result\r',.4)
            t.wait_for(lambda:'return result' in t.text,'rename workspace edit')
            t.command('w')
            self.assertIn('int result',(t.work/'main.cpp').read_text())
            self.assertIn('return result',(t.work/'main.cpp').read_text())

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--tools',type=Path,required=True)
    args=parser.parse_args()
    tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    os.environ['PATH']=str(args.tools.resolve())+os.pathsep+os.environ.get('PATH','')
    unittest.main(argv=[sys.argv[0]],verbosity=2)
