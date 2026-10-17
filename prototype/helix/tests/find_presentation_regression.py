#!/usr/bin/env python3
"""PTY verification of balanced hit areas and composited Find scope colors."""
import argparse
import json
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import terminal_regression as tr
from find_widget_regression import paste,find,replacement,click,panel,drag,save

ROOT=Path(__file__).resolve().parents[1]
CONFIG=(ROOT/'config/config.toml').read_text()
CONFIG=re.sub(r'^cursorline\s*=\s*(true|false)\s*$', 'cursorline = false',CONFIG,flags=re.M)

def button(t,label):
    left,top,right=panel(t)
    for y in range(top+1,min(top+7,t.screen.lines)):
        for x in range(left+1,right):
            if ''.join(t.screen.buffer[y][col].data for col in range(x,min(x+len(label),t.screen.columns)))==label:
                return x,y
    raise AssertionError(f'missing button {label!r}\n{t.text}')
def cell(t,x,y):return t.screen.buffer[y][x]
def bg(t,x,y):return cell(t,x,y).bg
def body(*lines):return '\n'.join(['header']*5+list(lines))+'\n'
def left(t,y=6):return t.screen.display[y].index('left')
def scope(t,x,start,end,y=6,query='aaa'):
    drag(t,(x+start,y),(x+end,y));find(t,query);click(t,'≡')

def tint(background,light=False):
    # Defaults are read from the pinned upstream editor theme color registry.
    rgb=tuple(int(background[i:i+2],16) for i in (0,2,4))
    reference=json.loads((ROOT/'tests/find-presentation-reference.json').read_text())
    rgba=reference['light' if light else 'dark'].lstrip('#')
    color=tuple(int(rgba[i:i+2],16) for i in (0,2,4));alpha=int(rgba[6:8],16)
    return ''.join(f'{(a*alpha+b*(255-alpha)+127)//255:02x}' for a,b in zip(color,rgb))

class FindPresentationTests(unittest.TestCase):
    def test_option_labels_have_equal_click_padding(self):
        with tr.Terminal({'a.txt':'cat catalog CAT\n'},'a.txt') as t:
            t.editor_focus();find(t,'cat');replacement(t,'dog')
            for label in ['Aa','W','.*','AB']:
                with self.subTest(label=label):
                    x,y=button(t,label);normal=bg(t,x,y)
                    self.assertEqual(cell(t,x-1,y).data,' ');self.assertEqual(cell(t,x+len(label),y).data,' ')
                    t.click(x-1,y);active=bg(t,x,y);self.assertNotEqual(active,normal)
                    self.assertEqual(bg(t,x-1,y),active);self.assertEqual(bg(t,x+len(label),y),active)
                    t.click(x+len(label),y);self.assertEqual(bg(t,x,y),normal)

    def test_previous_and_next_accept_both_sides_of_icon(self):
        with tr.Terminal({'a.txt':'foo foo foo\n'},'a.txt') as t:
            t.click(t.screen.display[1].index('foo'),1);find(t,'foo')
            for label,counts in [('↓',(2,3)),('↑',(2,1))]:
                x,y=button(t,label)
                for delta,count in zip((-1,1),counts):
                    t.click(x+delta,y);self.assertIn(f'{count}/3 matches',t.text)

    def test_scope_and_close_accept_both_sides(self):
        with tr.Terminal({'a.txt':'foo foo foo\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');x,y=button(t,'≡')
            t.click(x-1,y);self.assertIn('1 matches',t.text)
            t.click(x+1,y);self.assertIn('3 matches',t.text)
            for delta in (-1,1):
                x,y=button(t,'×');t.click(x+delta,y);self.assertNotIn('┌─ Find',t.text)
                find(t,'foo')

    def test_replace_buttons_accept_both_sides(self):
        for label in ['↦','⇉']:
            for delta in (-1,1):
                with self.subTest(label=label,delta=delta),tr.Terminal({'a.txt':'foo foo foo\n'},'a.txt') as t:
                    t.editor_focus();find(t,'foo');replacement(t,'bar');x,y=button(t,label);t.click(x+delta,y);save(t)
                    actual=(t.work/'a.txt').read_text()
                    self.assertEqual(actual.count('bar'),1 if label=='↦' else 3)
                    self.assertEqual(actual.count('foo'),2 if label=='↦' else 0)

    def test_expand_button_accepts_both_sides(self):
        with tr.Terminal({'a.txt':'foo\n'},'a.txt') as t:
            t.editor_focus();find(t,'foo');x,y=button(t,'>');t.click(x-1,y)
            self.assertIn('Find / Replace',t.text);x,y=button(t,'v');t.click(x+1,y)
            self.assertNotIn('Find / Replace',t.text)

    def test_scope_is_distinct_from_selection_and_composes_with_it(self):
        text=body('left aaa MID aaa right','left aaa MID aaa right','left plain tail')
        with tr.Terminal({'a.txt':text},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);drag(t,(x+9,7),(x+12,7));selection_color=bg(t,x+10,7)
            drag(t,(x+5,6),(x+8,6));find(t,'aaa');normal=bg(t,x+1,6);gutter=bg(t,x-3,6)
            click(t,'≡');scope_color=bg(t,x+1,6)
            self.assertEqual(scope_color,tint(normal));self.assertNotEqual(scope_color,normal)
            self.assertNotEqual(scope_color,selection_color);self.assertIn('1 matches',t.text)
            self.assertEqual(bg(t,x-3,6),gutter);self.assertEqual(bg(t,120,6),scope_color)
            drag(t,(x+9,6),(x+12,6));composed=bg(t,x+10,6)
            self.assertEqual(composed,tint(selection_color));self.assertNotEqual(composed,scope_color)
            self.assertNotEqual(composed,selection_color);self.assertEqual(bg(t,x+1,6),scope_color)
            drag(t,(x+9,7),(x+12,7));self.assertEqual(bg(t,x+10,7),selection_color)
            self.assertEqual(bg(t,x+10,6),scope_color);self.assertIn('1 matches',t.text)
            click(t,'≡');self.assertEqual(bg(t,x+1,6),normal)
            drag(t,(x+9,6),(x+12,6));self.assertEqual(bg(t,x+10,6),selection_color)

    def test_multiline_scope_tints_empty_lines_and_excludes_column_one_end(self):
        text=body('left aaa tail','','left aaa tail','left aaa tail')
        with tr.Terminal({'a.txt':text},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);normal=bg(t,x+1,9)
            drag(t,(x+5,6),(x,9));find(t,'aaa');click(t,'≡');t.click(x,11)
            self.assertIn('2 matches',t.text)
            for y in (6,7,8):self.assertEqual(bg(t,120,y),tint(normal))
            self.assertEqual(bg(t,120,9),normal)
            t.send('\x1b')
            for y in (6,7,8):self.assertEqual(bg(t,120,y),normal)

    def test_column_scope_does_not_tint_outside_lines_or_change_limits(self):
        text=body('left aaa aaa','left aaa aaa','left aaa aaa','left aaa aaa')
        with tr.Terminal({'a.txt':text},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);normal=bg(t,120,9)
            t.mouse(1,x+5,6);t.mouse(33,x+8,8);t.mouse(1,x+8,8,True)
            find(t,'aaa');click(t,'≡');t.click(x,11);self.assertIn('3 matches',t.text)
            for y in (6,7,8):self.assertEqual(bg(t,120,y),tint(normal))
            self.assertEqual(bg(t,120,9),normal)

    def test_scope_stays_visible_when_query_has_no_results_or_is_invalid(self):
        with tr.Terminal({'a.txt':body('left aaa MID tail','left plain tail')},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);scope(t,x,5,8);color=bg(t,x+1,6)
            find(t,'missing');self.assertIn('0 matches',t.text);self.assertEqual(bg(t,x+1,6),color)
            find(t,'(');t.send('\x1br');self.assertIn('unclosed group',t.text);self.assertEqual(bg(t,x+1,6),color)
            t.send('\x1b');self.assertNotEqual(bg(t,x+1,6),color)

    def test_scope_follows_inserted_lines_and_undo(self):
        with tr.Terminal({'a.txt':body('left aaa tail','left plain tail')},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);normal=bg(t,120,7);scope(t,x,0,13)
            t.click(x+5,6);t.send('iNEW\r')
            self.assertEqual(bg(t,120,6),tint(normal));self.assertEqual(bg(t,120,7),tint(normal))
            self.assertEqual(bg(t,120,8),normal)
            t.send('\x1a');self.assertEqual(bg(t,120,6),tint(normal));self.assertEqual(bg(t,120,7),normal)
            t.send('\x1b');self.assertEqual(bg(t,120,6),normal)

    def test_light_and_dark_theme_composition_preserves_syntax_foregrounds(self):
        languages='[[language]]\nname="cpp"\nlanguage-servers=[]\n'
        for theme in ['onedark','github_light']:
            with self.subTest(theme=theme),tr.Terminal({'a.cpp':body('int variable = 42; // comment','int outside = 1;')},'a.cpp',width=160,config=CONFIG.replace('theme = "onedark"',f'theme = "{theme}"'),languages=languages) as t:
                x=t.screen.display[6].index('int variable');points=[x,x+4,x+15,x+22]
                before=[cell(t,p,6).fg for p in points];self.assertGreater(len(set(before)),1)
                drag(t,(x+4,6),(x+12,6));find(t,'variable');normal=bg(t,x,6);click(t,'≡')
                self.assertEqual(bg(t,x,6),tint(normal,theme=='github_light'))
                self.assertEqual([cell(t,p,6).fg for p in points],before)

    def test_unicode_wide_cells_and_tabs_keep_scope_background(self):
        text=body('left 中文😀\taaa tail','left plain tail')
        with tr.Terminal({'a.txt':text},'a.txt',width=160,config=CONFIG) as t:
            x=left(t);normal=bg(t,120,7);drag(t,(x+5,6),(x+18,6));find(t,'aaa');click(t,'≡');t.click(x,11)
            self.assertIn('1 matches',t.text)
            match=next(col for col in range(x,x+24) if ''.join(cell(t,col+i,6).data for i in range(3))=='aaa')
            for col in range(x,x+24):
                if not match<=col<match+3:self.assertEqual(bg(t,col,6),tint(normal),f'column {col}')
            self.assertNotEqual(bg(t,match,6),tint(normal))
            self.assertEqual(bg(t,120,7),normal)

    def test_scope_repaints_without_accumulating_and_clears_on_file_switch(self):
        files={'a.txt':body('left aaa tail','left plain tail'),'b.txt':body('left aaa tail','left plain tail')}
        with tr.Terminal(files,'a.txt',width=160,config=CONFIG) as t:
            x=left(t);normal=bg(t,120,7);scope(t,x,5,8);expected=tint(normal)
            for _ in range(4):t.send('\x1bc');self.assertEqual(bg(t,120,6),expected)
            t.file('b.txt');self.assertEqual(bg(t,120,6),normal);self.assertIn('1 matches',t.text)

    def test_wrapped_scope_tints_each_visual_line(self):
        config=CONFIG.replace('[editor]','[editor]\nsoft-wrap.enable = true',1)
        with tr.Terminal({'a.txt':body('left '+('word '*40)+'tail','left outside')},'a.txt',width=100,config=config) as t:
            x=t.screen.display[6].index('left');drag(t,(x,6),(x+9,6));find(t,'word');normal=bg(t,80,10);click(t,'≡')
            self.assertIn('1 matches',t.text)
            for row in (6,7,8):self.assertEqual(bg(t,80,row),tint(normal))
            outside=next(i for i,row in enumerate(t.screen.display) if 'left outside' in row)
            self.assertEqual(bg(t,80,outside),normal)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--filter');ap.add_argument('--json',type=Path)
    args=ap.parse_args();tr.BINARY=args.binary.resolve();tr.RUNTIME=args.runtime.resolve()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FindPresentationTests)
    if args.filter:suite=unittest.TestSuite(t for t in suite if args.filter in t.id())
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.json:args.json.write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
