#!/usr/bin/env python3
"""Real workspace tests for the single movable, resizable shortcut window."""
import argparse,fcntl,json,os,pty,select,shutil,signal,struct,subprocess,sys,tempfile,termios,time,unittest
from pathlib import Path
import pyte
ROOT=Path(__file__).resolve().parents[3]
ZELLIJ:Path
PLUGIN:Path
ASSETS:Path|None=None
class Screen(pyte.Screen):
 def report_device_status(self,*args,**kwargs):pass
 def report_device_attributes(self,*args,**kwargs):pass
class Workspace:
 def __init__(self,width=180,height=44):
  self.tmp=tempfile.TemporaryDirectory(prefix='devtui-shortcuts-test-');self.base=Path(self.tmp.name);self.home=self.base/'home';self.home.mkdir();(self.home/'.config/zellij/layouts').mkdir(parents=True)
  self.session='shortcuts-test-'+str(os.getpid())+'-'+self.base.name.rsplit('-',1)[1]
  self.env=os.environ.copy()
  for key in list(self.env):
   if key.startswith(('ZELLIJ','DEVTUI_','HELIX_')):self.env.pop(key)
  self.env.update(HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'.config'),XDG_CACHE_HOME=str(self.home/'.cache'),XDG_DATA_HOME=str(self.home/'.local/share'),TERM='xterm-256color',LANG='C.UTF-8')
  self.log=self.base/'input.jsonl';self.width=width;self.height=height
  plugin=self.home/'.local/share/devtui/devtui-shortcuts.wasm';plugin.parent.mkdir(parents=True);shutil.copyfile(PLUGIN,plugin)
  config=(ROOT/'prototype/helix/zellij/zellij.kdl.in').read_text().replace('__HOME__',str(self.home))
  import re
  config=re.sub(r'load_plugins\s*\{[^}]*\}','load_plugins {}',config)
  self.config=self.base/'config.kdl';self.config.write_text(config+'\nshow_startup_tips false\nshow_release_notes false\n')
  fixture=str(Path(__file__).parent/'fixtures/shortcuts_surface.py')
  def pane(name,extra=''):
   return 'pane name='+json.dumps(name)+' command='+json.dumps(sys.executable)+' '+extra+' { args "-I" "-S" '+json.dumps(fixture)+' '+json.dumps(name)+' '+json.dumps(str(self.log))+'; }'
  self.layout=self.base/'layout.kdl';self.layout.write_text('layout { tab { pane split_direction="vertical" { '+pane('EDITOR','focus=true size="62%"')+'; pane split_direction="horizontal" { '+pane('GIT')+'; '+pane('SHELL')+'; }; }; }; }')
  command=[str(ZELLIJ)]+(['--data-dir',str(ASSETS)] if ASSETS else [])+['--session',self.session,'--config',str(self.config),'--new-session-with-layout',str(self.layout)]
  self.pid,self.fd=pty.fork()
  if self.pid==0:
   os.chdir(self.base);fcntl.ioctl(1,termios.TIOCSWINSZ,struct.pack('HHHH',height,width,0,0));os.execve(str(ZELLIJ),command,self.env)
  self.screen=Screen(width,height);self.stream=pyte.ByteStream(self.screen)
  try:self.wait(lambda:'EDITOR_UNDERLAY' in self.text,'workspace start',15)
  except BaseException:self.close();raise
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
 @property
 def text(self):return '\n'.join(self.screen.display)
 def drain(self,seconds=.1):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   if select.select([self.fd],[],[],min(.03,max(0,end-time.monotonic())))[0]:
    try:data=os.read(self.fd,65536)
    except OSError:return
    if not data:return
    self.stream.feed(data)
 def send(self,data,delay=.15):os.write(self.fd,data.encode() if isinstance(data,str) else data);self.drain(delay)
 def wait(self,predicate,label,timeout=7):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   self.drain(.07)
   if predicate():return
  raise AssertionError('Timed out: '+label+'\n'+self.text)
 def action(self,*args):
  return subprocess.check_output([str(ZELLIJ),'-s',self.session,'action',*map(str,args)],env=self.env,text=True,stderr=subprocess.PIPE,timeout=5)
 def panes(self):
  value=json.loads(self.action('list-panes','--json','--all'))
  panes=value.get('panes',value) if isinstance(value,dict) else value
  return [pane for pane in panes if not pane.get('is_suppressed',False)]
 def sheets(self):return [p for p in self.panes() if p.get('name',p.get('title',''))=='devtui Keyboard Shortcuts (F4)']
 def open(self):
  self.send('\x1bOS');self.wait(lambda:len(self.sheets())==1 and 'Ctrl / Shift / Alt' in self.text,'shortcut window')
  return self.sheets()[0]
 def mouse(self,code,x,y,release=False):self.send(f'\x1b[<{code};{x+1};{y+1}'+('m' if release else 'M'),.08)
 def drag(self,x,y,dx,dy):
  self.mouse(0,x,y)
  # Several intermediate events exercise native drag capture across pane bounds.
  for step in range(1,5):self.mouse(32,x+round(dx*step/4),y+round(dy*step/4))
  self.mouse(0,x+dx,y+dy,True);self.drain(.15)
 def resize(self,width,height):
  self.width=width;self.height=height;self.screen.resize(height,width)
  fcntl.ioctl(self.fd,termios.TIOCSWINSZ,struct.pack('HHHH',height,width,0,0));os.kill(self.pid,signal.SIGWINCH);self.drain(.4)
 def close(self):
  for command in [('kill-session',self.session),('delete-session',self.session)]:
   subprocess.run([str(ZELLIJ),*command],env=self.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
  end=time.monotonic()+3
  while time.monotonic()<end:
   try:
    if os.waitpid(self.pid,os.WNOHANG)[0]:break
   except ChildProcessError:break
   self.drain(.05)
  else:
   os.kill(self.pid,signal.SIGKILL);os.waitpid(self.pid,0)
  os.close(self.fd);self.tmp.cleanup()

def geometry(pane):return tuple(pane[key] for key in ['pane_x','pane_y','pane_columns','pane_rows'])
def pane_id(pane):return ('plugin_' if pane['is_plugin'] else 'terminal_')+str(pane['id'])
def cyan_columns(w,pane):
 x,y,width,height=geometry(pane);result=set()
 for row in range(y+1,y+height-1):
  previous=False
  for col in range(x+1,x+width-1):
   cell=w.screen.buffer[row][col];active=cell.fg=='cyan' and cell.bold
   if active and not previous and cell.data.strip():result.add(col)
   previous=active
 return result

class ShortcutTests(unittest.TestCase):
 def test_toggle_esc_and_unique_window(self):
  with Workspace() as w:
   self.assertEqual(len(w.panes()),3);self.assertEqual(w.sheets(),[])
   first=w.open();self.assertTrue(first['is_floating'])
   w.send('\x1bOS');w.wait(lambda:not w.sheets(),'F4 close')
   w.open();w.send('\x1b');w.wait(lambda:not w.sheets(),'Escape close')
   self.assertEqual(len(w.panes()),3)
 def test_search_uses_full_names_and_real_descriptions(self):
  with Workspace() as w:
   w.open();w.send('/Ctrl+Shift+S\r');w.wait(lambda:'Ctrl+Shift+S' in w.text and '另存为' in w.text,'full key description')
   self.assertNotIn('Ctrl+Shift+F',w.text)
   w.send('\x15');w.wait(lambda:'Ctrl / Shift / Alt' in w.text,'clear filter')
   w.send('/Ctrl+Shift+');w.send('\x1b[115;2u');w.send('\r');w.wait(lambda:'另存为' in w.text,'extended-protocol shifted search character')
   w.send('\x15');w.send('/不存在的快捷键\r');w.wait(lambda:'没有匹配' in w.text,'empty search result')
 def test_close_button_restores_underlay_and_focus(self):
  with Workspace() as w:
   w.open();before=w.text
   x,y=next((row.index('[x]')+1,y) for y,row in enumerate(w.screen.display) if '[x]' in row)
   w.mouse(0,x,y);w.mouse(0,x,y,True);w.wait(lambda:not w.sheets(),'close button')
   self.assertNotIn('Ctrl / Shift / Alt',w.text)
   self.assertNotIn('[x]',w.text)
   w.send('SAFE');w.wait(lambda:w.log.exists() and 'SAFE' in ''.join(bytes.fromhex(json.loads(line)['hex']).decode(errors='replace') for line in w.log.read_text().splitlines()),'restored editor input')
 def test_title_drag_moves_without_resizing(self):
  with Workspace() as w:
   pane=w.open();x,y,width,height=geometry(pane)
   w.drag(x+12,y,5,3)
   w.wait(lambda:geometry(w.sheets()[0])==(x+5,y+3,width,height),'title movement')
   self.assertIn('Ctrl / Shift / Alt',w.text)
 def test_all_four_edges_and_four_corners_resize(self):
  for edge in ['left','right','top','bottom','top-left','top-right','bottom-left','bottom-right']:
   with self.subTest(edge=edge),Workspace() as w:
    pane=w.open();x,y,width,height=geometry(pane)
    dx=-8 if 'left' in edge else 8 if 'right' in edge else 0
    dy=-3 if 'top' in edge else 3 if 'bottom' in edge else 0
    px=x if 'left' in edge else x+width-1 if 'right' in edge else x+width-9
    py=y if 'top' in edge else y+height-1 if 'bottom' in edge else y+height//2
    expected=(x+min(dx,0),y+min(dy,0),width+abs(dx),height+abs(dy))
    w.drag(px,py,dx,dy);w.wait(lambda:geometry(w.sheets()[0])==expected,'resize '+edge)
 def test_resizing_reflows_between_one_two_and_three_columns(self):
  with Workspace(width=300,height=60) as w:
   pane=w.open();self.assertEqual(len(cyan_columns(w,pane)),2)
   x,y,width,height=geometry(pane);w.drag(x+width-1,y+height//2,70,0)
   w.wait(lambda:len(cyan_columns(w,w.sheets()[0]))==3,'three-column layout')
   x,y,width,height=geometry(w.sheets()[0]);w.drag(x+width-1,y+height//2,-145,0)
   w.wait(lambda:len(cyan_columns(w,w.sheets()[0]))==1,'one-column layout')
   w.send('/Ctrl+Shift+S\r');w.wait(lambda:'Ctrl+Shift+S' in w.text and '另存为' in w.text,'narrow readable content')
 def test_scroll_keys_wheel_and_page_navigation(self):
  with Workspace() as w:
   w.open();initial=w.text;w.send('\x1b[6~');w.wait(lambda:w.text!=initial,'PageDown')
   self.assertIn('F4 / Esc',w.text)
   w.send('\x1b[H');w.wait(lambda:w.text==initial,'Home')
   pane=w.sheets()[0];x,y,width,height=geometry(pane);w.mouse(65,x+width//2,y+height//2)
   w.wait(lambda:w.text!=initial,'mouse wheel')
   w.send('\x1b[F');end=w.text;self.assertNotEqual(end,initial)
   w.send('\x1b[5~');w.wait(lambda:w.text!=end,'PageUp')
 def test_f4_works_from_every_pane_and_locked_mode(self):
  with Workspace() as w:
   panes=list(w.panes())
   for pane in panes:
    w.action('focus-pane-id',pane_id(pane));w.open();w.send('\x1bOS');w.wait(lambda:not w.sheets(),'close from '+pane['title'])
   for mode in ['locked','pane','tab','resize','session','scroll','search']:
    w.action('switch-mode',mode);w.open();w.send('\x1b');w.wait(lambda:not w.sheets(),'Esc close from '+mode+' mode')
 def test_always_on_top_when_other_panes_gain_focus(self):
  with Workspace() as w:
   editor=next(pane for pane in w.panes() if pane['title']=='EDITOR');sheet=w.open()
   w.action('focus-pane-id',pane_id(editor));w.drain(.2);self.assertIn('Ctrl / Shift / Alt',w.text)
   x,y,width,height=geometry(sheet)
   w.action('new-pane','--floating','--pinned','true','--name','OTHER','--x',x,'--y',y,'--width',width,'--height',height,'--',sys.executable,'-I','-S',str(Path(__file__).parent/'fixtures/shortcuts_surface.py'),'OTHER',str(w.log))
   w.drain(.4);self.assertIn('Ctrl / Shift / Alt',w.text);self.assertNotIn('OTHER_UNDERLAY',w.text)
   self.assertEqual(len(w.sheets()),1)
   w.send('\x1bOS');w.wait(lambda:not w.sheets(),'global close while another pane focused')
   self.assertIn('OTHER_UNDERLAY',w.text)
 def test_terminal_resize_keeps_window_inside_screen_and_closable(self):
  with Workspace() as w:
   w.open();w.resize(80,20)
   x,y,width,height=geometry(w.sheets()[0]);self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0);self.assertLessEqual(x+width,80);self.assertLessEqual(y+height,20)
   self.assertIn('[x]',w.text);w.send('\x1b');w.wait(lambda:not w.sheets(),'close after terminal resize')
   w.resize(180,44);w.open()
 def test_repeated_toggles_never_duplicate_window(self):
  with Workspace() as w:
   w.open()
   for _ in range(12):
    w.send('\x1bOS',.06);self.assertLessEqual(len(w.sheets()),1)
   w.drain(.3);self.assertLessEqual(len(w.sheets()),1)
   if w.sheets():w.send('\x1bOS');w.wait(lambda:not w.sheets(),'close before new tab')
   w.open();w.action('new-tab','--layout',str(w.layout),'--name','SECOND');w.drain(.3)
   self.assertEqual(len(w.sheets()),1)
   w.send('\x1bOS');w.wait(lambda:not w.sheets(),'close unique instance from another tab')
   w.open();self.assertEqual(len(w.sheets()),1)
 def test_help_input_is_not_forwarded_to_background(self):
  with Workspace() as w:
   w.open();baseline=w.log.read_text() if w.log.exists() else '';w.send('DO_NOT_EDIT');w.send('/Ctrl+Shift+F\r');w.send('\x1b[6~');w.send('\x1b')
   w.wait(lambda:not w.sheets(),'help closed')
   self.assertEqual(w.log.read_text() if w.log.exists() else '',baseline)
 def test_geometry_limits_keep_title_and_close_button_reachable(self):
  with Workspace() as w:
   w.open();x,y,width,height=geometry(w.sheets()[0]);w.drag(x+12,y,-x-5,-y-5)
   x,y,width,height=geometry(w.sheets()[0]);self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
   self.assertLessEqual(x+width,w.width);self.assertLessEqual(y+height,w.height);self.assertIn('[x]',w.text)

 def test_existing_control_and_mouse_input_reaches_editor(self):
  with Workspace() as w:
   w.send('\x13\x10\x08')
   w.mouse(16,8,5);w.mouse(16,8,5,True)
   w.mouse(8,8,6);w.mouse(8,8,6,True)
   w.mouse(1,8,7);w.mouse(33,10,8);w.mouse(1,10,8,True)
   def data():return b''.join(bytes.fromhex(json.loads(line)['hex']) for line in w.log.read_text().splitlines()) if w.log.exists() else b''
   w.wait(lambda:b'\x13' in data() and b'\x10' in data() and b'\x08' in data() and b'[<33;' in data(),'control and middle drag passthrough')
   self.assertIn(b'[<16;',data());self.assertIn(b'[<8;',data())
 def test_ordinary_float_keeps_native_title_and_border_drag(self):
  with Workspace() as w:
   w.action('new-pane','--floating','--name','ORDINARY','--',sys.executable,'-I','-S',str(Path(__file__).parent/'fixtures/shortcuts_surface.py'),'ORDINARY',str(w.log))
   w.wait(lambda:any(pane['title']=='ORDINARY' for pane in w.panes()),'ordinary float')
   pane=next(pane for pane in w.panes() if pane['title']=='ORDINARY');x,y,width,height=geometry(pane)
   w.drag(x+width-1,y+height//2,4,2)
   pane=next(pane for pane in w.panes() if pane['title']=='ORDINARY');self.assertEqual(geometry(pane),(x+4,y+2,width,height))
 def test_very_small_window_keeps_close_button(self):
  with Workspace() as w:
   w.open();x,y,width,height=geometry(w.sheets()[0]);w.drag(x+width-1,y+height//2,-85,0)
   x,y,width,height=geometry(w.sheets()[0]);w.drag(x+width//2,y+height-1,0,-14)
   self.assertIn('[x]',w.text)
   x,y=next((row.index('[x]')+1,y) for y,row in enumerate(w.screen.display) if '[x]' in row)
   w.mouse(0,x,y);w.mouse(0,x,y,True);w.wait(lambda:not w.sheets(),'tiny close button')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--zellij',required=True,type=Path);parser.add_argument('--plugin',required=True,type=Path);parser.add_argument('--assets',type=Path);parser.add_argument('--filter',default='');args=parser.parse_args();ZELLIJ=args.zellij.resolve();PLUGIN=args.plugin.resolve();ASSETS=args.assets.resolve() if args.assets else None
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ShortcutTests)
 if args.filter:suite=unittest.TestSuite(test for test in suite if args.filter in test.id())
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())
