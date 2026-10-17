#!/usr/bin/env python3
"""Unified editor actions, source-derived double click and real C++ formatting."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from wcwidth import wcswidth
sys.path.insert(0,str(Path(__file__).resolve().parent))
import terminal_regression as tr

HERE=Path(__file__).resolve().parent
CONFIG=(tr.ROOT/'prototype/helix/config/config.toml').read_text()
LANGUAGES=(tr.ROOT/'prototype/helix/config/languages.toml').read_text().replace('auto-format = true','auto-format = false')
WORDS=json.loads((HERE/'editor-word-cases.json').read_text())
STYLE='BasedOnStyle: LLVM\nIndentWidth: 2\nColumnLimit: 80\nAllowShortFunctionsOnASingleLine: None\n'
CPP='namespace demo{\nint first( int x ){return x+1;}\nint second( int y ){return y+2;}\n}\n'


def buffer(t):
    t.send('\x01');t.send('\x03')
    return t.clipboard()[-1]


def select(t,left,right,row=1):
    t.mouse(0,left,row);t.mouse(32,right,row);t.mouse(0,right,row,True)


def context(t,label,x=45,y=1):
    t.click(x,y,2);t.click_text(label,exact=True)


def clipboard_config(clip):
    writer="from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.stdin.read())"
    provider='{ custom = { yank = { command = "cat", args = ['+json.dumps(str(clip))+'] }, paste = { command = '+json.dumps(sys.executable)+', args = '+json.dumps(['-c',writer,str(clip)])+' } } }'
    return CONFIG.replace('clipboard-provider = "termcode"','clipboard-provider = '+provider)


def fixture_languages(mode,log):
    return f'''[language-server.editor-fixture]
command = {json.dumps(sys.executable)}
args = {json.dumps([str(HERE/'fixtures/editor_context_lsp.py'),mode,str(log)])}
[[language]]
name = "cpp"
language-servers = ["editor-fixture"]
formatter = {{ command = "devtui-unavailable-formatter" }}
auto-format = false
'''


def ready(t,log):
    t.wait_for(lambda:log.exists() and '"method": "initialized"' in log.read_text(),'fixture initialized')


def requests(log,method):
    return [item for item in map(json.loads,log.read_text().splitlines()) if item.get('method')==method]


class EditorContextTests(unittest.TestCase):
    def test_double_click_matches_upstream_word_cases(self):
        for item in WORDS:
            with self.subTest(case=item['name']),tr.Terminal({'case.txt':item['text']+'\n'},'case.txt') as t:
                x=40+wcswidth(item['text'][:item['click_char']].expandtabs(4))
                t.click(x,1);t.click(x,1);t.send('\x03')
                self.assertEqual(t.clipboard()[-1],item['expected'])
                self.assertEqual((t.work/'case.txt').read_text(),item['text']+'\n')

    def test_word_drag_expands_in_both_directions(self):
        for reverse in (False,True):
            with self.subTest(reverse=reverse),tr.Terminal({'case.txt':'first_word middle last_word\n'},'case.txt') as t:
                x=65 if reverse else 44;end=44 if reverse else 65
                t.click(x,1);t.mouse(0,x,1);t.mouse(32,end,1);t.mouse(0,end,1,True);t.send('\x03')
                self.assertEqual(t.clipboard()[-1],'first_word middle last_word')

    def test_separated_or_slow_clicks_remain_carets(self):
        for kind in ('slow','different','keyboard'):
            with self.subTest(kind=kind),tr.Terminal({'case.txt':'alpha_beta value\n'},'case.txt') as t:
                t.click(44,1)
                if kind=='slow': t.drain(.45)
                if kind=='keyboard': t.send('l')
                t.click(45 if kind=='different' else 44,1);t.send('\x03')
                self.assertEqual(t.clipboard()[-1],'alpha_beta value\n')

    def test_caret_and_selection_share_navigation_and_clipboard_actions(self):
        with tr.Terminal({'case.txt':'alpha_beta other\n'},'case.txt') as t:
            for selected in (False,True):
                if selected: select(t,40,50)
                t.click(44,1,2)
                for label in ('Go to Definition','Go to References','Copy','Cut','Paste','Delete','Format Document'):
                    self.assertIn(label,t.text)
                self.assertEqual('Format Selection' in t.text,selected)
                t.click_text('Copy',exact=True)
                self.assertEqual(t.clipboard()[-1],'alpha_beta' if selected else 'alpha_beta other\n')
            # An outside right click resets deliberate-selection metadata.
            t.click(53,1,2);t.click_text('Copy',exact=True)
            self.assertEqual(t.clipboard()[-1],'alpha_beta other\n')

    def test_empty_selection_copy_includes_line_ending_and_preserves_caret(self):
        for content,expected in [('first\nsecond\n','first\n'),('last_line','last_line\n'),('','\n'),('first\r\nsecond','first\r\n')]:
            with self.subTest(content=content),tr.Terminal({'case.txt':content},'case.txt') as t:
                context(t,'Copy',44,1)
                self.assertEqual(t.clipboard()[-1],expected)
                self.assertTrue(t.screen.display[28].rstrip().endswith('1:5' if content else '1:1'),t.screen.display[28])
                self.assertEqual((t.work/'case.txt').read_bytes(),content.encode())
        with tr.Terminal({'case.txt':'a word\n'},'case.txt') as t:
            select(t,40,41);context(t,'Copy',40,1)
            self.assertEqual(t.clipboard()[-1],'a')

    def test_cached_line_copy_paste_preserves_column_and_undo(self):
        with tr.Terminal({'case.txt':'first line\nsecond line\n'},'case.txt') as t:
            context(t,'Copy',44,1)
            context(t,'Paste',45,2)
            self.assertTrue(t.screen.display[28].rstrip().endswith('3:6'),t.screen.display[28])
            self.assertEqual(buffer(t),'first line\nfirst line\nsecond line\n')
            t.send('\x1a');self.assertEqual(buffer(t),'first line\nsecond line\n')

    def test_external_clipboard_paste_replaces_selection_and_is_one_undo(self):
        with tempfile.TemporaryDirectory(prefix='editor-clipboard-') as tmp:
            clip=Path(tmp)/'clipboard';clip.write_text('新内容\nnext')
            cfg=clipboard_config(clip)
            with tr.Terminal({'case.txt':'before selected after\n'},'case.txt',config=cfg) as t:
                select(t,47,55);context(t,'Paste',50,1);t.command('write --no-format')
                self.assertEqual((t.work/'case.txt').read_text(),'before 新内容\nnext after\n')
                t.send('\x1a');t.command('write --no-format')
                self.assertEqual((t.work/'case.txt').read_text(),'before selected after\n')

    def test_external_clipboard_prefix_change_is_not_replaced_by_cached_copy(self):
        with tempfile.TemporaryDirectory(prefix='editor-clipboard-') as tmp:
            clip=Path(tmp)/'clipboard';clip.write_text('')
            with tr.Terminal({'case.txt':'alpha rest\ntarget\n'},'case.txt',config=clipboard_config(clip)) as t:
                select(t,40,45);context(t,'Copy',42,1)
                self.assertEqual(clip.read_text(),'alpha')
                clip.write_text('alphabet')
                context(t,'Paste',40,2);t.command('write --no-format')
                self.assertEqual((t.work/'case.txt').read_text(),'alpha rest\nalphabettarget\n')

    def test_menu_paste_spreads_rows_over_column_selection(self):
        with tempfile.TemporaryDirectory(prefix='editor-clipboard-') as tmp:
            clip=Path(tmp)/'clipboard';clip.write_text('A\nB\nC')
            cfg=clipboard_config(clip)
            with tr.Terminal({'case.txt':'012345\n012345\n012345\n'},'case.txt',config=cfg) as t:
                t.mouse(1,42,1);t.mouse(33,44,3);t.mouse(1,44,3,True)
                context(t,'Paste',43,2);t.command('write --no-format')
                self.assertEqual((t.work/'case.txt').read_text(),'01A45\n01B45\n01C45\n')

    def test_unavailable_clipboard_paste_is_visible_and_keeps_text(self):
        with tr.Terminal({'case.txt':'KEEP\n'},'case.txt') as t:
            context(t,'Paste',43,1)
            self.assertIn('Clipboard is empty or unavailable',t.text)
            self.assertNotIn('┌',t.text)
            self.assertEqual((t.work/'case.txt').read_text(),'KEEP\n')

    def test_document_format_uses_project_style_and_separate_undo(self):
        with tr.Terminal({'case.cpp':CPP,'.clang-format':STYLE},'case.cpp',languages=LANGUAGES) as t:
            t.click(40,1);t.send('\x1b[200~// unsaved\n\x1b[201~')
            original='// unsaved\n'+CPP
            expected=subprocess.check_output(['clang-format','--assume-filename='+str(t.work/'case.cpp')],input=original,text=True)
            context(t,'Format Document',45,2)
            t.wait_for(lambda:'int first(int x)' in t.text,'document formatting')
            self.assertEqual(buffer(t),expected)
            self.assertEqual((t.work/'case.cpp').read_text(),CPP)
            t.send('\x1a');self.assertEqual(buffer(t),original)
            t.send('\x1a');self.assertEqual(buffer(t),CPP)

    def test_clangd_selection_format_expands_beyond_selected_characters(self):
        with tr.Terminal({'case.cpp':CPP,'.clang-format':STYLE},'case.cpp',languages=LANGUAGES) as t:
            t.drain(.8)
            start=CPP.index('return x');length=6
            expected=subprocess.check_output(['clang-format','--assume-filename='+str(t.work/'case.cpp'),'-offset='+str(start),'-length='+str(length)],input=CPP,text=True)
            self.assertNotEqual(expected[:start],CPP[:start])
            select(t,58,64,2);context(t,'Format Selection',60,2)
            t.wait_for(lambda:'int first(int x)' in t.text,'selection formatting')
            self.assertEqual(buffer(t),expected)
            self.assertIn('int second( int y ){return y+2;}',expected)
            t.send('\x1a');self.assertEqual(buffer(t),CPP)

    def test_range_only_provider_and_utf16_request(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl';content='// 中文\n// 😀 RAW;\n'
            with tr.Terminal({'case.cpp':content},'case.cpp',languages=fixture_languages('range-only',log)) as t:
                ready(t,log);select(t,46,49,2);context(t,'Format Selection',47,2)
                t.wait_for(lambda:'FORMATTED' in t.text,'range-only formatting')
                self.assertEqual(buffer(t),content.replace('RAW','FORMATTED'))
                request=requests(log,'textDocument/rangeFormatting')[0]['params']['range']
                self.assertEqual(request,{'start':{'line':1,'character':6},'end':{'line':1,'character':9}})
                self.assertEqual(requests(log,'textDocument/formatting'),[])

    def test_expanded_overlapping_multi_ranges_are_recomputed_as_union(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl';content='int RAW = 0;\nint RAW = 1;\n'
            with tr.Terminal({'case.cpp':content},'case.cpp',languages=fixture_languages('overlap',log)) as t:
                ready(t,log)
                t.mouse(1,44,1);t.mouse(33,47,2);t.mouse(1,47,2,True)
                context(t,'Format Selection',45,1)
                t.wait_for(lambda:'FORMATTED' in t.text,'merged range formatting')
                self.assertEqual(buffer(t),content.replace('RAW','FORMATTED'))
                calls=requests(log,'textDocument/rangeFormatting')
                self.assertEqual(len(calls),3)
                self.assertEqual(calls[-1]['params']['range'],{'start':{'line':0,'character':4},'end':{'line':1,'character':7}})
                t.send('\x1a');self.assertEqual(buffer(t),content)

    def test_format_failure_preserves_document_and_terminal_geometry(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl'
            with tr.Terminal({'case.cpp':'int RAW;\n'},'case.cpp',languages=fixture_languages('failure',log)) as t:
                ready(t,log);before=t.screen.display[:28]
                context(t,'Format Document',45,1)
                t.wait_for(lambda:'format rejected' in t.text,'format error')
                self.assertIn('EXPLORER',t.screen.display[0]);self.assertNotIn('┌',t.text)
                self.assertEqual(t.screen.display[:28],before)
                self.assertEqual(buffer(t),'int RAW;\n')

    def test_delayed_format_does_not_overwrite_new_edits(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl'
            with tr.Terminal({'case.cpp':'int RAW;\n'},'case.cpp',languages=fixture_languages('delayed',log)) as t:
                ready(t,log);context(t,'Format Document',45,1)
                t.wait_for(lambda:bool(requests(log,'textDocument/formatting')),'format request')
                t.send('iNEW\x1b');t.drain(1)
                self.assertEqual(buffer(t),'int RNEWAW;\n')

    def test_delayed_format_is_cancelled_when_view_switches_document(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl'
            with tr.Terminal({'case.cpp':'int RAW;\n','other.txt':'KEEP\n'},'case.cpp',languages=fixture_languages('delayed',log)) as t:
                ready(t,log);context(t,'Format Document',45,1)
                t.wait_for(lambda:bool(requests(log,'textDocument/formatting')),'format request')
                t.command('edit other.txt');t.drain(1)
                self.assertEqual(buffer(t),'KEEP\n')
                t.command('buffer-next');self.assertEqual(buffer(t),'int RAW;\n')

    def test_document_only_provider_cannot_activate_selection_format(self):
        with tempfile.TemporaryDirectory(prefix='editor-format-') as tmp:
            log=Path(tmp)/'requests.jsonl'
            with tr.Terminal({'case.cpp':'int RAW;\n'},'case.cpp',languages=fixture_languages('doc-only',log)) as t:
                ready(t,log);select(t,44,47);context(t,'Format Selection',45,1)
                self.assertIn('Editor',t.text);self.assertEqual(requests(log,'textDocument/rangeFormatting'),[])
                t.send('\x1b');self.assertEqual(buffer(t),'int RAW;\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True,type=Path);parser.add_argument('--runtime',required=True,type=Path);parser.add_argument('--filter',default='')
    args=parser.parse_args();tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    tests=unittest.defaultTestLoader.loadTestsFromTestCase(EditorContextTests)
    if args.filter: tests=unittest.TestSuite(test for test in tests if args.filter in test.id())
    result=unittest.TextTestRunner(verbosity=2).run(tests);raise SystemExit(not result.wasSuccessful())
