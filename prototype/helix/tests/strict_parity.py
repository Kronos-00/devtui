#!/usr/bin/env python3
"""VS Code semantic edge cases, exercised via terminal input and disk/OSC52 checks."""
import argparse
from pathlib import Path
import re
import time
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr

class StrictParity(unittest.TestCase):
    def test_new_file_opens_pinned_and_nested_parent_is_revealed(self):
        with tr.Terminal({'old.txt':'OLD\n'}) as t:
            t.click(4,1,2);t.click_text('New File',exact=True);t.send('sub/new.txt\r',.3)
            t.wait_for(lambda:'new.txt' in t.screen.display[0],'created document open')
            self.assertIn('new.txt',t.text);t.send('iNEW\x1b');t.command('w')
            self.assertEqual((t.work/'sub/new.txt').read_text(),'NEW\n')
            t.file('old.txt');self.assertIn('new.txt',t.screen.display[0])

    def test_new_file_rejects_parent_escape(self):
        with tr.Terminal({}) as t:
            t.click(4,1,2);t.click_text('New File',exact=True);t.send('../escape.txt\r',.2)
            self.assertFalse((t.base/'escape.txt').exists())
            self.assertIn('relative',t.text.lower())

    def test_empty_file_clipboard_cannot_activate_paste(self):
        with tr.Terminal({}) as t:
            t.click(4,1,2);t.click_text('Paste',exact=True)
            self.assertIn('New File',t.text);self.assertIn('Paste',t.text)

    def test_delete_dirty_document_warns_and_does_not_resurrect_file(self):
        with tr.Terminal({'a.txt':'ORIGINAL\n'},'a.txt') as t:
            t.edit('DIRTY');x,y=t.find('a.txt',True);t.click(x,y,2);t.click_text('Delete',exact=True)
            self.assertIn('unsaved',t.text.lower())
            t.click_text('Cancel',exact=True);self.assertTrue((t.work/'a.txt').exists())
            x,y=t.find('a.txt',True);t.click(x,y,2);t.click_text('Delete',exact=True)
            for label in ['Move to Trash','Delete Permanently','Delete']:
                try: t.click_text(label,exact=True);break
                except AssertionError: pass
            t.wait_for(lambda:not (t.work/'a.txt').exists(),'confirmed deletion')
            self.assertNotIn('a.txt',t.screen.display[0]);self.assertIn('EXPLORER',t.text)

    def test_copy_name_zero_and_literal_suffix_match_vscode(self):
        cases = [
            ('a copy 0.txt', 'a copy.txt'),
            ('a copy0.txt', 'a copy0 copy.txt'),
            ('a copy  2.txt', 'a copy  2 copy.txt'),
            (' copy.txt', ' copy copy.txt'),
        ]
        for source, expected in cases:
            with self.subTest(source=source), tr.Terminal({source: 'KEEP\n'}) as t:
                x, y = t.find(source, True)
                t.click(x, y, 2); t.click_text('Copy', exact=True)
                t.click(4, 1, 2); t.click_text('Paste', exact=True)
                t.wait_for(lambda: (t.work / expected).exists(), 'VS Code duplicate name')
                self.assertEqual((t.work / expected).read_text(), 'KEEP\n')
                self.assertEqual((t.work / source).read_text(), 'KEEP\n')

    def test_copy_name_large_counter_never_stalls(self):
        for number in (1073741824, 4294967295):
            source = f'a copy {number}.txt'
            expected = f'a copy {number} copy.txt'
            with self.subTest(number=number), tr.Terminal({source: 'KEEP\n'}) as t:
                x, y = t.find(source, True)
                t.click(x, y, 2); t.click_text('Copy', exact=True)
                t.click(4, 1, 2); t.click_text('Paste', exact=True)
                t.wait_for(lambda: (t.work / expected).exists(), 'bounded duplicate counter')
                self.assertEqual((t.work / expected).read_text(), 'KEEP\n')
                t.editor_focus(); t.command('new')
                self.assertIn('[No Name]', t.screen.display[0])

    def test_duplicate_names_keep_extensions_and_advance_existing_copies(self):
        cases = [
            ('a copy.txt', 'a copy 2.txt', 'a copy 3.txt'),
            ('a copy 2.txt', 'a copy 3.txt', 'a copy 4.txt'),
            ('.env', '.env copy', '.env copy 2'),
            ('archive.tar.gz', 'archive.tar copy.gz', 'archive.tar copy 2.gz'),
        ]
        for source, occupied, expected in cases:
            with self.subTest(source=source), tr.Terminal({source: 'KEEP\n', occupied: 'EXISTING\n'}) as t:
                x, y = t.find(source, True)
                t.click(x, y, 2); t.click_text('Copy', exact=True)
                t.click(4, 1, 2); t.click_text('Paste', exact=True)
                t.wait_for(lambda: (t.work / expected).exists(), 'next free duplicate name')
                self.assertEqual((t.work / expected).read_text(), 'KEEP\n')
                self.assertEqual((t.work / occupied).read_text(), 'EXISTING\n')

    def test_ctrl_d_first_selects_word_second_adds_occurrence(self):
        with tr.Terminal({'a.txt':'apple apple apple\n'},'a.txt') as t:
            t.click(41,1);t.send('\x04')
            self.assertIn('1 sel',t.text);t.send('\x03')
            self.assertEqual(t.clipboard()[-1],'apple')
            t.send('\x04');self.assertIn('2 sel',t.text)
            t.send('\x03');self.assertEqual(t.clipboard()[-1],'apple\napple')

    def test_ctrl_d_in_insert_selects_current_word(self):
        with tr.Terminal({'a.txt':'apple apple\n'},'a.txt') as t:
            t.click(41,1);t.send('i\x04\x03')
            self.assertEqual(t.clipboard()[-1],'apple');self.assertIn('1 sel',t.text)

    def test_copy_after_keyboard_motion_copies_line_not_block_cursor(self):
        with tr.Terminal({'a.txt':'abcdef\n'},'a.txt') as t:
            t.click(41,1);t.send('l\x03')
            self.assertEqual(t.clipboard()[-1],'abcdef\n')

    def test_plain_drag_is_half_open_and_copy_preserves_selection(self):
        with tr.Terminal({'a.txt':'abcdef\n'},'a.txt') as t:
            x=t.screen.display[1].index('abcdef')
            t.mouse(0,x+1,1);t.mouse(32,x+3,1);t.mouse(0,x+3,1,True);t.send('\x03')
            self.assertEqual(t.clipboard()[-1],'bc')
            t.send('\x03');self.assertEqual(t.clipboard()[-1],'bc')

    def test_rectangle_typing_replaces_instead_of_inserting_before(self):
        with tr.Terminal({'a.txt':'abcdef\nabcdef\n'},'a.txt') as t:
            x=t.screen.display[1].index('abcdef')
            t.mouse(1,x+1,1);t.mouse(33,x+3,2);t.mouse(1,x+3,2,True);t.send('iX')
            self.assertEqual(sum('aXdef' in row for row in t.screen.display[1:3]),2,t.text)
            t.command('w');self.assertEqual((t.work/'a.txt').read_text(),'aXdef\naXdef\n')

    def test_rectangle_left_and_right_collapse_exactly_to_boundary(self):
        for arrow,index in [('D',1),('C',3)]:
            with self.subTest(arrow=arrow),tr.Terminal({'a.txt':'abcdef\nabcdef\n'},'a.txt') as t:
                x=t.screen.display[1].index('abcdef')
                t.mouse(1,x+1,1);t.mouse(33,x+3,2);t.mouse(1,x+3,2,True)
                t.send('\x1b['+arrow);t.send('iX');t.command('w')
                expected='abcdef'[:index]+'X'+'abcdef'[index:]+'\n'
                self.assertEqual((t.work/'a.txt').read_text(),expected*2)

    def test_ctrl_z_undoes_pending_insert_transaction(self):
        with tr.Terminal({'a.txt':'aaa\n'},'a.txt') as t:
            x=t.screen.display[1].index('aaa');t.click(x,1);t.send('iXYZ');t.send('\x1a')
            self.assertNotIn('XYZ',t.screen.display[1]);t.send('\x19')
            self.assertIn('XYZ',t.screen.display[1])

    def test_ZZ_ZQ_and_full_quit_aliases(self):
        with tr.Terminal({'a.txt':'AAA\n'},'a.txt') as t:
            t.edit('S');t.send('ZZ',.3);self.assertIn('S',(t.work/'a.txt').read_text())
            self.assertNotIn('a.txt',t.screen.display[0]);t.command('open a.txt');t.edit('DISCARD');t.send('ZQ',.3)
            self.assertNotIn('DISCARD',(t.work/'a.txt').read_text());self.assertNotIn('a.txt',t.screen.display[0])
            for cmd in ['qall','qall!','wqall','wqall!','xall','xall!']:
                t.command(cmd);self.assertNotIn('no such command',t.text.lower());self.assertIn('EXPLORER',t.text)

    def test_find_defaults_literal_case_insensitive_and_mouse_toggle(self):
        with tr.Terminal({'a.txt':'a.b A.B axb abé\n'},'a.txt') as t:
            t.editor_focus();t.send('\x06');t.send('a.b')
            self.assertIn('2 matches',t.text);self.assertIn('┌─ Find',t.text)
            t.send('\r');self.assertIn('┌─ Find',t.text)
            t.click_text('Aa');self.assertIn('1 matches',t.text)
            t.send('\x1b');t.send('\x03');self.assertEqual(t.clipboard()[-1],'a.b')

    def test_in_file_replace_literal_dollar_and_regex_opt_in(self):
        with tr.Terminal({'a.txt':'foo.bar FOO.BAR fooXbar\n'},'a.txt') as t:
            t.editor_focus();t.send('\x06');t.send('foo.bar');t.send('\x08');t.send('$1');t.click_text('⇉');t.send('\x1b')
            self.assertEqual((t.work/'a.txt').read_text(),'foo.bar FOO.BAR fooXbar\n')
            self.assertIn('$1 $1 fooXbar',t.text)
            t.command('w');self.assertEqual((t.work/'a.txt').read_text(),'$1 $1 fooXbar\n')

    def test_project_replace_saves_explicitly_even_open_documents(self):
        with tr.Terminal({'a.txt':'foo\n','b.txt':'foo\n'},'a.txt') as t:
            t.edit('DIRTY-');t.send('\x1bOP');t.send('devtui_project_replace\r',.2)
            t.send('foo\r');t.send('bar\r');t.send('\r',.4)
            t.wait_for(lambda:'bar' in (t.work/'a.txt').read_text(),'open target saved')
            self.assertIn('DIRTY-',(t.work/'a.txt').read_text());self.assertEqual((t.work/'b.txt').read_text(),'bar\n')

    def test_pasted_single_file_opens_pinned_without_losing_tree(self):
        with tr.Terminal({'a.txt':'A\n','b.txt':'B\n'}) as t:
            x,y=t.find('a.txt',True);t.click(x,y,2);t.click_text('Copy',exact=True)
            t.click(4,1,2);t.click_text('Paste',exact=True)
            t.wait_for(lambda:'a copy.txt' in t.screen.display[0],'pasted file open')
            t.file('b.txt');self.assertIn('a copy.txt',t.screen.display[0]);self.assertIn('EXPLORER',t.text)

    def test_external_utf16_column(self):
        import socket,json
        with tr.Terminal({'a.txt':'OLD\n'},'a.txt') as t:
            target=t.base/'unicode.txt';target.write_text('a😀b\n')
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.connect(str(t.sock));client.sendall((json.dumps({'path':str(target),'line':1,'column':4})+'\n').encode())
            t.wait_for(lambda:'unicode.txt' in t.screen.display[0],'unicode document')
            t.send('iX');t.command('w');self.assertEqual(target.read_text(),'a😀Xb\n')

    def test_redo_terminal_bridge_is_not_reference_key(self):
        import re
        template=(Path(__file__).resolve().parents[3]/'prototype/helix/zellij/zellij.kdl.in').read_text()
        sequence=bytes(map(int,re.search(r'bind "Ctrl Shift z".*?Write ([0-9 ]+);',template).group(1).split()))
        self.assertNotEqual(sequence,b'\x1b[24;2~')
        with tr.Terminal({'a.txt':'aaa\n'},'a.txt') as t:
            t.edit('XYZ');t.send('\x1a');self.assertNotIn('XYZ',t.screen.display[1])
            t.send(sequence);self.assertIn('XYZ',t.screen.display[1])

    def test_clangd_definition_navigation_in_editor(self):
        with tr.Terminal({'main.cpp':'int target = 1;\nint read_value() {\n  return target;\n}\n'},'main.cpp') as t:
            t.click(t.screen.display[3].index('target'),3)
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                t.send('\x1b[24~',.25)
                if t.screen.cursor.y==1: break
            self.assertEqual(t.screen.cursor.y,1,t.text)
            self.assertIn('EXPLORER',t.text)

    def test_quick_open_from_tree_focus_accepts_immediate_edit(self):
        with tr.Terminal({'a.txt':'AAA\n','b.txt':'BBB\n'}) as t:
            t.file('a.txt');t.send('\x10');t.send('b.txt\r',.35)
            t.send('iX');t.command('w')
            self.assertEqual((t.work/'b.txt').read_text(),'XBBB\n')
            self.assertIn('EXPLORER',t.text)

    def test_find_whole_word_option(self):
        with tr.Terminal({'a.txt':'cat catalog CAT\n'},'a.txt') as t:
            t.editor_focus();t.send('\x06');t.send('cat');self.assertIn('3 matches',t.text)
            t.send('\x1bw');self.assertIn('2 matches',t.text)
            t.send('\x1bc');self.assertIn('1 matches',t.text)


    def test_mouse_dirty_save_and_named_save_as(self):
        with tr.Terminal({'a.txt':'AAA\n'},'a.txt') as t:
            t.edit('X');t.command('q');t.click_text('Save',exact=True)
            t.wait_for(lambda:'a.txt' not in t.screen.display[0],'saved tab closed')
            self.assertIn('X',(t.work/'a.txt').read_text())
            t.command('open a.txt');t.editor_focus();t.send('\x1bOP');t.send('devtui_save_as\r',.2)
            t.save_as(t.work/'renamed.txt');t.wait_for(lambda:'renamed.txt' in t.screen.display[0],'new document name')
            t.edit('Y');t.command('w')
            self.assertIn('Y',(t.work/'renamed.txt').read_text());self.assertNotIn('Y',(t.work/'a.txt').read_text())

    def test_reverse_rectangle_and_mismatch_paste(self):
        with tr.Terminal({'a.txt':'abcdef\na\nabcdef\n'},'a.txt') as t:
            x=t.screen.display[1].index('abcdef')
            t.mouse(1,x+4,3);t.mouse(33,x+2,1);t.mouse(1,x+2,1,True);t.send('\x03')
            self.assertEqual(t.clipboard()[-1],'cd\ncd')
            t.send('i');t.send('\x1b[200~Q\x1b[201~');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'abQef\na\nabQef\n')

    def test_all_short_rows_fallback_and_boundary_navigation(self):
        with tr.Terminal({'a.txt':'aa\nb\n'},'a.txt') as t:
            t.mouse(1,60,1);t.mouse(33,65,2);t.mouse(1,65,2,True);t.send('iX')
            self.assertIn('aaX',t.text);self.assertIn('bX',t.text)
            t.send('\x1b[A'*5+'\x1b[D'*10+'\x1b[C'*10+'\x1b[B'*5)
            self.assertNotIn('error',t.text.lower());self.assertNotIn(b']52;c;?',t.raw)
            t.send('Z');t.command('w');self.assertIn('Z',(t.work/'a.txt').read_text())

    def test_cut_selection_then_terminal_paste(self):
        with tr.Terminal({'a.txt':'abcdef\nabcdef\n'},'a.txt') as t:
            x=t.screen.display[1].index('abcdef')
            t.mouse(1,x+1,1);t.mouse(33,x+3,2);t.mouse(1,x+3,2,True);t.send('\x18')
            self.assertEqual(t.clipboard()[-1],'bc\nbc')
            t.send('\x1b[200~XY\nZW\x1b[201~');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'aXYdef\naZWdef\n')

    def test_new_folder_and_hidden_toggle(self):
        with tr.Terminal({'.hidden.txt':'H\n','visible.txt':'V\n'}) as t:
            self.assertIn('.hidden.txt',t.text);t.send('H');self.assertNotIn('.hidden.txt',t.text)
            t.send('H');self.assertIn('.hidden.txt',t.text)
            t.click(4,1,2);t.click_text('New Folder',exact=True);t.send('new/sub\r',.2)
            self.assertTrue((t.work/'new/sub').is_dir());self.assertIn('sub',t.text)

    def test_shift_selection_and_context_preserve_group(self):
        with tr.Terminal({'a.txt':'A\n','b.txt':'B\n','c.txt':'C\n'}) as t:
            t.file('a.txt');t.file('c.txt',modifier=4)
            x,y=t.find('b.txt',True);t.click(x,y,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(set(t.clipboard()[-1].splitlines()),{'a.txt','b.txt','c.txt'})
            t.file('a.txt');t.file('b.txt',modifier=8)
            x,y=t.find('a.txt',True);t.click(x,y,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(set(t.clipboard()[-1].splitlines()),{'a.txt','b.txt'})
            t.file('c.txt');t.send('\x03');self.assertIn('c.txt',t.text)

    def test_invalid_regex_does_not_modify_document(self):
        with tr.Terminal({'a.txt':'abc\n'},'a.txt') as t:
            t.editor_focus();t.send('\x06');t.send('\x1br[')
            self.assertIn('abc',t.text);t.send('\x1b');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'abc\n')

    def test_root_path_clipboard(self):
        with tr.Terminal({}) as t:
            t.click(4,1,2);t.click_text('Copy Path',exact=True)
            self.assertEqual(t.clipboard()[-1],str(t.work))
            t.click(4,1,2);t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'.')


    def test_paste_replacement_undo_is_single_transaction(self):
        with tr.Terminal({'a.txt':'abcdef\nabcdef\n'},'a.txt') as t:
            x=t.screen.display[1].index('abcdef')
            t.mouse(1,x+1,1);t.mouse(33,x+3,2);t.mouse(1,x+3,2,True);t.send('i')
            t.send('\x1b[200~XY\nZW\x1b[201~')
            self.assertIn('aXYdef',t.text);self.assertIn('aZWdef',t.text)
            t.send('\x1a');self.assertIn('abcdef',t.screen.display[1]);self.assertIn('abcdef',t.screen.display[2])
            t.send('\x19');self.assertIn('aXYdef',t.text);self.assertIn('aZWdef',t.text)

    def test_overview_search_and_named_mark_navigation(self):
        data=''.join(f'LINE-{i:03d}\n' for i in range(1,161))
        with tr.Terminal({'long.txt':data},'long.txt') as t:
            t.editor_focus();t.send('\x06');t.send('LINE-130\r')
            self.assertTrue(any(line[-2]=='s' for line in t.screen.display[:-2]), t.text)
            t.send('\x1b');self.assertFalse(any(line[-2]=='s' for line in t.screen.display[:-2]),t.text)
            t.send(' msa');t.send('gg');t.send(' mga')
            self.assertIn('LINE-130',t.text)
            t.send('\x06');t.send('\x15');t.send('\x1b')
            self.assertTrue(any(line[-2]=='a' for line in t.screen.display[:-2]), t.text)
            t.send(' mda');self.assertFalse(any(line[-2]=='a' for line in t.screen.display[:-2]))


    def test_double_click_and_keyboard_open_focus_editor(self):
        with tr.Terminal({'a.txt':'AAA\n','b.txt':'BBB\n'}) as t:
            t.file('a.txt',double=True);t.send('iX\x1b');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'XAAA\n')
            t.file('b.txt');t.send('\r');t.send('iY\x1b');t.command('w')
            self.assertEqual((t.work/'b.txt').read_text(),'YBBB\n')

    def test_tree_left_right_preserve_keyboard_context(self):
        with tr.Terminal({'folder/a.txt':'A\n'}) as t:
            t.file('folder');t.send('\x1b[C')
            t.send('\x03');t.send('\x1b[D')
            t.send('\x1b[21;2~');t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'folder')

    def test_symbol_actions_without_provider_are_disabled(self):
        with tr.Terminal({'a.txt':'text\n'},'a.txt') as t:
            t.click(44,1,2);t.click_text('Go to Definition',exact=True)
            self.assertIn('Go to Definition',t.text);self.assertNotIn('error',t.text.lower())
            t.send('\x1b');self.assertIn('text',t.text)

    def test_external_open_dismisses_transient_picker(self):
        with tr.Terminal({'a.txt':'A\n','b.txt':'B\n'},'a.txt') as t:
            t.editor_focus();t.send('\x10');t.drain(.2)
            import socket, json
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.connect(str(t.sock));client.sendall((json.dumps({'path':str(t.work/'b.txt'),'line':1,'column':1})+'\n').encode())
            t.wait_for(lambda:'b.txt' in t.screen.display[0],'external editor opened')
            t.send('iQ\x1b');t.command('w');self.assertEqual((t.work/'b.txt').read_text(),'QB\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--filter',default='')
    args=ap.parse_args();tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StrictParity)
    if args.filter: suite=unittest.TestSuite(t for t in suite if args.filter in t.id())
    result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())
