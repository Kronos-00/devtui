#!/usr/bin/env python3
"""Real-PTY tests of the editor-anchored, non-modal Find/Replace widget."""
import argparse
import fcntl
import json
from pathlib import Path
import signal
import struct
import sys
import termios
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import terminal_regression as tr


def paste(t,text): t.send('\x1b[200~'+text+'\x1b[201~')
def find(t,text):
    t.send('\x06'); paste(t,text)
def replacement(t,text):
    t.send('\x08'); paste(t,text)
def click(t,label):
    # Screen.display is a Unicode string, not a terminal-cell coordinate map.
    left,top,right=panel(t)
    for y in range(top+1,min(top+7,t.screen.lines)):
        for x in range(left+1,right):
            if ''.join(t.screen.buffer[y][col].data for col in range(x,min(x+len(label),t.screen.columns)))==label:
                t.click(x,y);return
    raise AssertionError(f'cannot find {label!r}\n{t.text}')
def all_matches(t): click(t,'⇉')
def save(t): t.send('\x1b');t.command('w')
def panel(t):
    for y,row in enumerate(t.screen.display):
        if '┌─ Find' in row:
            left=row.index('┌─ Find');right=row.index('┐',left)
            return left,y,right
    raise AssertionError(t.text)
def drag(t,a,b):
    t.mouse(0,*a);t.mouse(32,*b);t.mouse(0,*b,True)

class FindWidgetTests(unittest.TestCase):
    def test_top_right_bounds_singleton_and_close(self):
        with tr.Terminal({'a.txt':'foo foo\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');left,top,right=panel(t)
            self.assertEqual(top,1);self.assertGreater(left,32);self.assertEqual(right,119)
            self.assertIn('2 matches',t.text)
            t.send('\x06'*3);self.assertEqual(t.text.count('┌─ Find'),1)
            replacement(t,'bar');self.assertEqual(t.text.count('┌─ Find'),1)
            self.assertIn('Find / Replace',t.text);click(t,'×')
            self.assertNotIn('┌─ Find',t.text);self.assertIn('foo foo',t.text)
            t.send('\x06\x1b');self.assertNotIn('┌─ Find',t.text)

    def test_left_sash_drag_and_width_retention(self):
        with tr.Terminal({'a.txt':'foo\n'},'a.txt',width=160) as t:
            t.editor_focus();find(t,'foo');left,y,right=panel(t)
            drag(t,(left,y+1),(left-25,y+1));new=panel(t)
            self.assertEqual(new[0],left-25);self.assertEqual(new[2],right)
            drag(t,(new[0],y+1),(right-10,y+1));small=panel(t)
            self.assertLess(small[2]-small[0],new[2]-new[0]);self.assertGreaterEqual(small[0],32)
            t.send('\x1b\x06');self.assertEqual(panel(t),small)

    def test_double_click_sash_maximizes_and_restores(self):
        with tr.Terminal({'a.txt':'foo\n'},'a.txt',width=160) as t:
            t.editor_focus();find(t,'foo');left,y,right=panel(t)
            t.click(left,y+1);t.click(left,y+1);maximized=panel(t)
            self.assertLess(maximized[0],left);self.assertEqual(maximized[2],right)
            t.click(maximized[0],y+1);t.click(maximized[0],y+1)
            self.assertEqual(panel(t),(left,y,right))

    def test_terminal_resize_reanchors_within_editor(self):
        with tr.Terminal({'a.txt':'foo\n'},'a.txt',width=160) as t:
            t.editor_focus();find(t,'foo');self.assertEqual(panel(t)[2],159)
            fcntl.ioctl(t.fd,termios.TIOCSWINSZ,struct.pack('HHHH',30,78,0,0));t.screen.resize(30,78)
            import os
            os.kill(t.pid,signal.SIGWINCH);t.drain(.3)
            left,y,right=panel(t);self.assertGreaterEqual(left,0);self.assertLess(right,78)
            click(t,'×');self.assertNotIn('┌─ Find',t.text)

    def test_find_flags_mouse_and_keyboard_and_previous_next(self):
        with tr.Terminal({'a.txt':'a.b A.B axb a.bc\n'},'a.txt') as t:
            t.editor_focus();find(t,'a.b');self.assertIn('3 matches',t.text)
            click(t,'Aa');self.assertIn('2 matches',t.text)
            click(t,'W ');self.assertIn('1 matches',t.text)
            click(t,'.*');self.assertIn('2 matches',t.text)
            t.send('\x1bc');self.assertIn('3 matches',t.text)
            click(t,'↓');self.assertIn('2/3 matches',t.text)
            click(t,'↑');self.assertIn('1/3 matches',t.text)
            t.send('\x1b[13;2u');self.assertIn('3/3 matches',t.text)

    def test_selection_seed_ctrl_h_focus_and_tab_fields(self):
        with tr.Terminal({'a.txt':'foo foo\n'},'a.txt') as t:
            x=t.screen.display[1].index('foo');drag(t,(x,1),(x+3,1))
            t.send('\x08');self.assertIn('2 matches',t.text)
            paste(t,'bar');all_matches(t)
            self.assertEqual((t.work/'a.txt').read_text(),'foo foo\n')
            save(t);self.assertEqual((t.work/'a.txt').read_text(),'bar bar\n')

    def test_literal_dollars_and_dirty_until_save(self):
        with tr.Terminal({'a.txt':'foo.bar FOO.BAR fooXbar\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo.bar');replacement(t,'$1\\n$$');all_matches(t)
            self.assertEqual((t.work/'a.txt').read_text(),'foo.bar FOO.BAR fooXbar\n')
            save(t);self.assertEqual((t.work/'a.txt').read_text(),'$1\\n$$ $1\\n$$ fooXbar\n')

    def test_regex_groups_dollars_and_case_operations(self):
        with tr.Terminal({'a.txt':'AbCd-42 xyz-19\n'},'a.txt') as t:
            t.editor_focus();find(t,r'([a-z]+)-(\d+)');t.send('\x1br')
            replacement(t,r'$2:\l\U$1:$$:$&');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'42:aBCD:$:AbCd-42 19:xYZ:$:xyz-19\n')

    def test_preserve_case_static_and_segmented(self):
        with tr.Terminal({'a.txt':'FOO foo Foo fOo foo-BAR Foo_bar\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');replacement(t,'new');click(t,'AB');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'NEW new New new new-BAR New_bar\n')
            t.editor_focus();find(t,'new-bar');replacement(t,'next-word');all_matches(t);save(t)
            self.assertIn('next-WORD',(t.work/'a.txt').read_text())

    def test_replace_one_advances_and_replace_all_is_one_undo(self):
        with tr.Terminal({'a.txt':'foo foo foo\n'},'a.txt') as t:
            t.click(t.screen.display[1].index('foo'),1);find(t,'foo');replacement(t,'bar');click(t,'↦')
            self.assertIn('2 matches',t.text);all_matches(t);t.send('\x1b');t.send('\x1a');t.command('w')
            self.assertEqual((t.work/'a.txt').read_text(),'bar foo foo\n')
            t.send('\x1a');t.command('w');self.assertEqual((t.work/'a.txt').read_text(),'foo foo foo\n')
            t.send('\x19');t.command('w');self.assertEqual((t.work/'a.txt').read_text(),'bar foo foo\n')

    def test_replace_current_when_selection_no_longer_matches_first_selects(self):
        with tr.Terminal({'a.txt':'foo foo\nplain\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');replacement(t,'bar');t.click(42,8)
            click(t,'↦');self.assertNotIn('bar foo',t.text)
            click(t,'↦');save(t);self.assertEqual((t.work/'a.txt').read_text(),'bar foo\nplain\n')

    def test_find_in_selection_and_scopes_follow_replacement_edits(self):
        with tr.Terminal({'a.txt':'foo foo\nfoo foo\n'},'a.txt') as t:
            x=t.screen.display[1].index('foo');drag(t,(x,1),(x+7,1))
            find(t,'foo');click(t,'≡');self.assertIn('2 matches',t.text)
            replacement(t,'longer');click(t,'↦');self.assertIn('1 matches',t.text)
            all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'longer longer\nfoo foo\n')

    def test_multiline_selection_end_at_column_one_and_toggle_off(self):
        with tr.Terminal({'a.txt':'foo foo\nfoo foo\nfoo foo\n'},'a.txt') as t:
            x=t.screen.display[1].index('foo');drag(t,(x,1),(x,3))
            find(t,'foo');t.send('\x1bl');self.assertIn('4 matches',t.text)
            t.send('\x1bl');self.assertIn('6 matches',t.text)

    def test_multicursor_selection_scope(self):
        with tr.Terminal({'a.txt':'foo x foo\nfoo y foo\nfoo z foo\n'},'a.txt') as t:
            x=t.screen.display[1].index('foo');t.mouse(1,x,1);t.mouse(33,x+3,3);t.mouse(1,x+3,3,True)
            find(t,'foo');click(t,'≡');self.assertIn('3 matches',t.text)
            replacement(t,'bar');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'bar x foo\nbar y foo\nbar z foo\n')

    def test_invalid_regex_is_inline_and_recovers(self):
        with tr.Terminal({'a.txt':'foo foo\n'},'a.txt') as t:
            t.editor_focus();find(t,'(');t.send('\x1br');self.assertIn('unclosed group',t.text)
            self.assertNotIn('delete failed',t.text);replacement(t,'bar');all_matches(t)
            t.send('\x06');paste(t,'foo');self.assertIn('2 matches',t.text)
            all_matches(t);save(t);self.assertEqual((t.work/'a.txt').read_text(),'bar bar\n')

    def test_zero_width_regex_all_and_single_make_progress(self):
        with tr.Terminal({'a.txt':'ab\ncd\n'},'a.txt') as t:
            t.editor_focus();find(t,'^');t.send('\x1br');replacement(t,'>');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'>ab\n>cd\n>\n')

    def test_multiline_paste_find_and_replace(self):
        with tr.Terminal({'a.txt':'a\nb\na\nb\n'},'a.txt') as t:
            t.editor_focus();find(t,'a\nb');self.assertIn('2 matches',t.text)
            replacement(t,'x\ny\nz');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_text(),'x\ny\nz\nx\ny\nz\n')

    def test_unicode_input_grapheme_motion_and_backspace(self):
        with tr.Terminal({'a.txt':'中文😀 é\n中文😀 é\n'},'a.txt') as t:
            t.editor_focus();find(t,'中文😀');self.assertIn('2 matches',t.text)
            replacement(t,'新😀é');t.send('\x7f');t.send('\x1b[D');paste(t,'界')
            all_matches(t);save(t);self.assertEqual((t.work/'a.txt').read_text(),'新界😀 é\n新界😀 é\n')

    def test_editing_outside_widget_keeps_it_visible_and_updates_count(self):
        with tr.Terminal({'a.txt':'foo\n\n\n\n\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');t.click(41,6);t.send('ifoo')
            self.assertIn('┌─ Find',t.text);self.assertIn('2 matches',t.text)
            t.send('\x1b');self.assertNotIn('┌─ Find',t.text)
            t.command('w');self.assertEqual((t.work/'a.txt').read_text().count('foo'),2)

    def test_tab_switch_keeps_query_and_clears_old_scope(self):
        with tr.Terminal({'a.txt':'foo foo\n','b.txt':'foo\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');t.file('b.txt');self.assertIn('1 matches',t.text)
            self.assertIn('┌─ Find',t.text);t.send('\x06');replacement(t,'bar');all_matches(t);save(t)
            self.assertEqual((t.work/'b.txt').read_text(),'bar\n');self.assertEqual((t.work/'a.txt').read_text(),'foo foo\n')

    def test_crlf_replacement_preserves_line_endings(self):
        with tr.Terminal({'a.txt':'foo\r\nfoo\r\n'},'a.txt') as t:
            t.editor_focus();find(t,r'^(foo)$');t.send('\x1br');replacement(t,r'$1\nbar');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_bytes(),b'foo\r\nbar\r\nfoo\r\nbar\r\n')

    def test_multiline_find_normalizes_crlf_and_captures(self):
        with tr.Terminal({'a.txt':'中\r\nfoo\r\n中\r\nfoo\r\n'},'a.txt') as t:
            t.editor_focus();find(t,'中\nfoo');self.assertIn('2 matches',t.text)
            replacement(t,'new\nline');all_matches(t);save(t)
            self.assertEqual((t.work/'a.txt').read_bytes(),b'new\r\nline\r\nnew\r\nline\r\n')

    def test_narrow_editor_all_actions_remain_clickable(self):
        with tr.Terminal({'a.txt':'foo\n'},'a.txt',width=68) as t:
            t.editor_focus();find(t,'foo');left,y,right=panel(t);self.assertGreaterEqual(left,32)
            for icon in ['↑','↓','≡','×']:self.assertIn(icon,t.screen.display[y+1][left:right+1])
            replacement(t,'bar');all_matches(t);save(t);self.assertEqual((t.work/'a.txt').read_text(),'bar\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--filter');ap.add_argument('--json',type=Path)
    args=ap.parse_args();tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FindWidgetTests)
    if args.filter:suite=unittest.TestSuite(t for t in suite if args.filter in t.id())
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.json:args.json.write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
