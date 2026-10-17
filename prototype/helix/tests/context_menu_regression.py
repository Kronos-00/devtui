#!/usr/bin/env python3
"""Pointer-anchored context menus, using upstream VS Code geometry fixtures."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import struct
import sys
import termios
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terminal_regression as tr

CASES=json.loads(Path(__file__).with_name('context-menu-cases.json').read_text())
CONTENT=('0123456789'*12+'\n')*40


def frame(t):
    for y in range(t.screen.lines):
        for x in range(t.screen.columns):
            if t.screen.buffer[y][x].data == '┌':
                right=next(i for i in range(x+1,t.screen.columns) if t.screen.buffer[y][i].data == '┐')
                return x,y,right-x+1
    raise AssertionError('No context menu frame\n'+t.text)


def assert_frame(test,t,case):
    x,y,width=frame(t)
    test.assertEqual([x,y],case['expected'],t.text)
    test.assertEqual(width,case['menu'][0],t.text)
    test.assertLessEqual(x+width,t.screen.columns)
    test.assertLessEqual(y+case['menu'][1],t.screen.lines)


def resize(t,width,height):
    t.screen.resize(lines=height,columns=width)
    t.width=width
    fcntl.ioctl(t.fd,termios.TIOCSWINSZ,struct.pack('HHHH',height,width,0,0))
    os.kill(t.pid,signal.SIGWINCH)
    t.drain(.2)


class ContextMenuTests(unittest.TestCase):
    def test_explorer_menu_follows_mouse_and_actions_hit_correct_file(self):
        for case in (c for c in CASES if c['kind']=='explorer'):
            with self.subTest(case=case['name']), tr.Terminal({f'target{i:02}.txt':'KEEP\n' for i in range(27)}) as t:
                x,y=case['anchor']; name=f'target{y-2:02}.txt'
                t.click(x,y,2)
                assert_frame(self,t,case)
                t.click_text('Copy Relative Path',exact=True)
                self.assertEqual(t.clipboard()[-1],name)
                self.assertTrue((t.work/name).exists())
                self.assertNotIn('┌',t.text)

    def test_editor_menu_follows_mouse_including_all_window_edges(self):
        for case in (c for c in CASES if c['kind']=='editor'):
            with self.subTest(case=case['name']), tr.Terminal({'case.txt':CONTENT},'case.txt') as t:
                before=t.screen.display[:28]
                t.click(*case['anchor'],2)
                assert_frame(self,t,case)
                self.assertIn('Go to Definition',t.text)
                t.send('\x1b')
                self.assertEqual(t.screen.display[:28],before)
                self.assertEqual((t.work/'case.txt').read_text(),CONTENT)

    def test_selection_menu_keeps_multiselection_and_mouse_copy(self):
        for case in (c for c in CASES if c['kind']=='selection'):
            with self.subTest(case=case['name']), tr.Terminal({'case.txt':CONTENT},'case.txt') as t:
                t.command('set-option scrolloff 0')
                x,y=case['anchor']; left=x-3; right=x+3
                t.mouse(1,left,y-1); t.mouse(33,right,y+1); t.mouse(1,right,y+1,True)
                t.click(x,y,2)
                assert_frame(self,t,case)
                self.assertIn('Editor',t.text)
                t.click_text('Copy',exact=True)
                expected='0123456789'*12
                self.assertEqual(t.clipboard()[-1],'\n'.join([expected[left-40:right-40]]*3))
                self.assertIn('3/3 sels',t.text)
                self.assertEqual((t.work/'case.txt').read_text(),CONTENT)

    def test_outside_right_click_reopens_menu_at_new_target(self):
        case=next(c for c in CASES if c['kind']=='reopen_explorer')
        with self.subTest(origin='explorer'), tr.Terminal({f'target{i:02}.txt':'KEEP\n' for i in range(27)}) as t:
            t.click(5,3,2)
            before=frame(t)
            t.click(8,7,2) # Right-clicking inside the existing menu does not execute Copy.
            self.assertEqual(frame(t),before)
            t.click(*case['anchor'],2)
            assert_frame(self,t,case)
            t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'target18.txt')
            self.assertEqual(len(list(t.work.iterdir())),27)
        case=next(c for c in CASES if c['kind']=='reopen_tree')
        with self.subTest(origin='editor'), tr.Terminal({'a.txt':'KEEP\n','case.txt':CONTENT},'case.txt') as t:
            t.click(90,12,2)
            self.assertIn('Go to Definition',t.text)
            t.click(*case['anchor'],2)
            assert_frame(self,t,case)
            t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'a.txt')
            self.assertEqual((t.work/'case.txt').read_text(),CONTENT)

    def test_keyboard_context_does_not_reuse_previous_mouse_anchor(self):
        with tr.Terminal({f'target{i:02}.txt':'KEEP\n' for i in range(27)}) as t:
            t.click(29,25,2); t.send('\x1b')
            t.send('\x1b[21;2~')
            self.assertEqual(frame(t),(50,11,20),t.text)
            t.click_text('Copy Relative Path',exact=True)
            self.assertEqual(t.clipboard()[-1],'target23.txt')

    def test_delete_confirmation_is_centered_after_anchored_menu(self):
        with tr.Terminal({f'target{i:02}.txt':'KEEP\n' for i in range(27)}) as t:
            t.click(29,25,2); t.click_text('Delete',exact=True)
            self.assertIn('Permanently delete',t.text)
            x,y,width=frame(t)
            self.assertEqual(x,(120-width)//2)
            self.assertEqual(y,12)
            t.click_text('Cancel',exact=True)
            self.assertTrue((t.work/'target23.txt').exists())
            self.assertNotIn('┌',t.text)

    def test_resize_reflows_open_menu_inside_new_viewport(self):
        case=next(c for c in CASES if c['kind']=='resize')
        with tr.Terminal({'case.txt':CONTENT},'case.txt') as t:
            t.click(*case['anchor'],2)
            resize(t,*case['viewport'])
            assert_frame(self,t,case)
            t.click(0,t.screen.lines-1)
            self.assertNotIn('┌',t.text)
            self.assertIn('EXPLORER',t.screen.display[0])
            self.assertEqual((t.work/'case.txt').read_text(),CONTENT)

    def test_short_viewport_scrolls_to_last_action_without_corrupting_screen(self):
        case=next(c for c in CASES if c['kind']=='short')
        with tr.Terminal({'case.txt':CONTENT},'case.txt',width=60) as t:
            resize(t,*case['viewport'])
            t.click(*case['anchor'],2)
            assert_frame(self,t,case)
            t.send('\x1b[B'*12)
            t.wait_for(lambda:'Delete' in t.screen.display[-1],'last context action visible')
            t.send('\x1b')
            self.assertIn('EXPLORER',t.screen.display[0])
            self.assertNotIn('┌',t.text)
            self.assertEqual((t.work/'case.txt').read_text(),CONTENT)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    tr.BINARY=args.binary.resolve(); tr.RUNTIME=args.runtime.resolve()
    tests=unittest.defaultTestLoader.loadTestsFromTestCase(ContextMenuTests)
    if args.filter: tests=unittest.TestSuite(t for t in tests if args.filter in t.id())
    result=unittest.TextTestRunner(verbosity=2).run(tests)
    raise SystemExit(not result.wasSuccessful())
