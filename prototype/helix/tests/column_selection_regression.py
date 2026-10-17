#!/usr/bin/env python3
"""Unicode rectangular selections compared with pinned VS Code source output."""
import argparse
import json
from pathlib import Path
import re
import socket
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr

CASES = json.loads(Path(__file__).with_name('column-selection-cases.json').read_text())

def char_index(text, utf16_column):
    return len(text.encode('utf-16-le')[:2 * (utf16_column - 1)].decode('utf-16-le'))

def expected_edit(case, replacement):
    lines = list(case['lines'])
    for selected in case['selection']:
        row = selected['row'] - 1
        a = char_index(lines[row], min(selected['anchor'], selected['head']))
        b = char_index(lines[row], max(selected['anchor'], selected['head']))
        lines[row] = lines[row][:a] + replacement + lines[row][b:]
    return '\n'.join(lines) + '\n'

def origin(t):
    # Read terminal cells, not Python string offsets: wide glyphs have a
    # continuation cell, and combining/ZWJ sequences contain several scalars.
    # The isolated fixture has a 32-cell Explorer, one divider and 7 gutter cells.
    return 40

def drag(t, case, reverse_x=False, reverse_y=False):
    left, right = case['from'], case['to']
    first, last = 1, len(case['lines'])
    if reverse_x: left, right = right, left
    if reverse_y: first, last = last, first
    x = origin(t)
    t.mouse(1, x + left, first)
    t.mouse(33, x + right, last)
    t.mouse(1, x + right, last, True)

class ColumnSelectionTests(unittest.TestCase):
    def test_oracle_copy_and_typing_all_drag_directions(self):
        for case in CASES:
            for reverse_x, reverse_y in ((False,False),(True,False),(False,True),(True,True)):
                with self.subTest(case=case['name'], reverse_x=reverse_x, reverse_y=reverse_y):
                    original = '\n'.join(case['lines']) + '\n'
                    with tr.Terminal({'case.txt': original}, 'case.txt', width=180) as t:
                        drag(t, case, reverse_x, reverse_y)
                        count = re.search(r'(\d+)/(\d+) sels', t.text)
                        self.assertIsNotNone(count, t.text)
                        self.assertEqual(int(count[2]), len(case['selection']), t.text)
                        t.send('\x03')
                        self.assertEqual(t.clipboard()[-1], case['clipboard'])
                        t.send('\x03')
                        self.assertEqual(t.clipboard()[-1], case['clipboard'])
                        t.send('iX')
                        t.command('w')
                        self.assertEqual((t.work/'case.txt').read_text(), expected_edit(case, 'X'))

    def test_sparse_and_empty_caret_cut(self):
        for name in ('sparse_and_eol', 'all_eol', 'zero_width', 'cjk_short_eol', 'emoji_sequences', 'rounded_caret_inside_cjk'):
            case = next(c for c in CASES if c['name'] == name)
            with self.subTest(case=name):
                original = '\n'.join(case['lines']) + '\n'
                with tr.Terminal({'case.txt': original}, 'case.txt', width=180) as t:
                    drag(t, case)
                    t.send('\x18')
                    self.assertEqual(t.clipboard()[-1], case['clipboard'])
                    t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), case['cut'])
                    t.send('\x1a'); t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), original)

    def test_arrows_collapse_ranges_but_move_empty_unicode_carets(self):
        case = next(c for c in CASES if c['name'] == 'rounded_caret_inside_cjk')
        for arrow, direction in (('D',-1), ('C',1)):
            with self.subTest(arrow=arrow):
                original = '\n'.join(case['lines'])+'\n'
                expected = list(case['lines'])
                for selected in case['selection']:
                    row = selected['row'] - 1
                    a = char_index(expected[row], min(selected['anchor'],selected['head']))
                    b = char_index(expected[row], max(selected['anchor'],selected['head']))
                    point = a+direction if a == b else (a if direction < 0 else b)
                    expected[row] = expected[row][:point]+'X'+expected[row][point:]
                with tr.Terminal({'case.txt':original}, 'case.txt', width=180) as t:
                    drag(t, case)
                    t.send('\x1b['+arrow); t.send('iX'); t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), '\n'.join(expected)+'\n')

    def test_paste_keeps_empty_carets_and_replaces_nonempty_ranges(self):
        for name in ('rounded_caret_inside_cjk', 'emoji_sequences', 'sparse_and_eol'):
            case = next(c for c in CASES if c['name'] == name)
            with self.subTest(case=name):
                original = '\n'.join(case['lines'])+'\n'
                with tr.Terminal({'case.txt':original}, 'case.txt', width=180) as t:
                    drag(t, case)
                    t.send('\x1b[200~文字\x1b[201~')
                    t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), expected_edit(case, '文字'))
                    t.send('\x1a'); t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), original)

    def test_right_edge_scrolloff_does_not_move_drag_anchor(self):
        line = '0123456789' * 20
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                with tr.Terminal({'case.txt': (line+'\n')*3}, 'case.txt') as t:
                    drag(t, {'from':3, 'to':76, 'lines':[line]*3}, reverse, reverse)
                    t.send('\x03')
                    self.assertEqual(t.clipboard()[-1], '\n'.join([line[3:76]]*3))

    def test_horizontal_viewport_offset_uses_visual_columns(self):
        line = ''.join(chr(i) for i in range(33, 127))
        wide = '中文' * 40
        for left, right in ((3,18), (2,17)):
            with self.subTest(left=left):
                with tr.Terminal({'case.txt':line+'\n'+wide+'\n'+line+'\n'}, 'case.txt') as t:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                        client.connect(str(t.sock))
                        client.sendall((json.dumps({'path':str(t.work/'case.txt'),'line':1,'column':90})+'\n').encode())
                    t.drain(.2)
                    offset = line.index(t.screen.buffer[1][40].data)
                    self.assertGreater(offset, 0)
                    drag(t, {'from':left, 'to':right, 'lines':[line,wide,line]})
                    t.send('\x03')
                    expected_ascii = line[offset+left:offset+right]
                    expected_wide = wide[(offset+left)//2:(offset+right)//2]
                    self.assertEqual(t.clipboard()[-1], '\n'.join([expected_ascii,expected_wide,expected_ascii]))

    def test_softwrapped_wide_graphemes_select_both_visual_rows(self):
        with tr.Terminal({'case.txt':'中文'*60+'\n'}, 'case.txt') as t:
            t.command('set-option soft-wrap.enable true')
            t.mouse(1,43,1); t.mouse(33,52,2); t.mouse(1,52,2,True)
            t.send('\x03')
            self.assertEqual(t.clipboard()[-1], '文中文中文\n中文中文中')

    def test_unicode_replacement_undo_redo(self):
        for name in ('cjk_short_eol', 'accented_and_combining', 'emoji_sequences', 'tab_left_nearest'):
            case = next(c for c in CASES if c['name'] == name)
            with self.subTest(case=name):
                original = '\n'.join(case['lines']) + '\n'
                with tr.Terminal({'case.txt': original}, 'case.txt', width=180) as t:
                    drag(t, case)
                    t.send('i文字')
                    t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), expected_edit(case, '文字'))
                    t.send('\x1a'); t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), original)
                    t.send('\x19'); t.command('w')
                    self.assertEqual((t.work/'case.txt').read_text(), expected_edit(case, '文字'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    tr.BINARY = args.binary.resolve(); tr.RUNTIME = args.runtime.resolve()
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(ColumnSelectionTests)
    if args.filter:
        tests = unittest.TestSuite(t for t in tests if args.filter in t.id())
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    raise SystemExit(not result.wasSuccessful())
