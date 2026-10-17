#!/usr/bin/env python3
"""Generate the default shortcut catalogue from the shipped editor bindings."""
import argparse
import json
from pathlib import Path
import tomllib

HERE=Path(__file__).resolve().parent
DESCRIPTIONS={
':exit':('文件与会话','退出编辑器；有未保存内容时先确认保存'),':quit!':('文件与会话','放弃当前视图的未保存修改并关闭'),':write':('文件与会话','保存当前文件'),
'code_action':('语言与诊断','显示当前位置可用的代码操作或修复建议'),'command_palette':('导航与搜索','打开命令面板，搜索并执行编辑器命令'),
'copy_selection_on_next_line':('选择与多光标','在下一行增加一个对应的选择或光标'),'copy_selection_on_prev_line':('选择与多光标','在上一行增加一个对应的选择或光标'),
'dap_continue':('调试','继续运行已暂停的调试程序'),'dap_next':('调试','单步执行下一行，不进入函数内部'),'dap_pause':('调试','暂停正在运行的调试程序'),'dap_restart':('调试','重新启动当前调试会话'),'dap_step_in':('调试','单步进入当前函数调用'),'dap_step_out':('调试','运行到当前函数返回'),'dap_switch_stack_frame':('调试','选择调试调用栈中的栈帧'),'dap_terminate':('调试','终止当前调试会话'),'dap_toggle_breakpoint':('调试','添加或移除当前行的断点'),'dap_variables':('调试','查看当前调试栈帧中的变量'),
'delete_selection':('编辑与剪贴板','删除当前选择'),'devtui_add_all_occurrences':('选择与多光标','同时选择当前词或选区的所有匹配位置'),'devtui_add_next_occurrence':('选择与多光标','选择当前词，再次按下时增加下一个匹配位置'),'devtui_clear_selections':('选择与多光标','取消额外光标或选择，并回到普通模式'),
'devtui_copy_to_clipboard':('编辑与剪贴板','复制选区；没有显式选区时复制整行，包括换行符'),'devtui_current_replace':('导航与搜索','打开当前文件的查找与替换'),'devtui_cut_to_clipboard':('编辑与剪贴板','剪切选区；没有显式选区时剪切当前行'),'devtui_debug_menu':('调试','打开调试菜单，查看可用的调试操作'),'devtui_debug_start_or_continue':('调试','启动调试，或继续运行已暂停的调试程序'),'devtui_delete_mark':('导航与搜索','删除已命名的导航标记'),'devtui_find':('导航与搜索','在当前文件中查找文本'),'devtui_goto_line_prompt':('导航与搜索','输入行号或行列位置并跳转'),'devtui_goto_mark':('导航与搜索','选择并跳转到已命名的导航标记'),'devtui_lsp_info':('语言与诊断','查看语言服务、C/C++ 配置来源、编译器和配置警告'),'devtui_project_replace':('导航与搜索','在整个项目中查找并替换文本'),'devtui_python_venv':('语言与诊断','选择项目使用的 Python 解释器或虚拟环境'),'devtui_save_as':('文件与会话','选择新路径，将当前文件另存为'),'devtui_set_mark':('导航与搜索','为当前位置设置一个命名导航标记'),'devtui_symbol_context_menu':('语言与诊断','打开统一编辑区菜单，包含导航、剪贴板和格式化操作'),
'extend_line':('选择与多光标','选择当前整行，继续按下时扩展到下一行'),'file_explorer':('导航与搜索','将焦点切换到项目文件树'),'file_picker':('导航与搜索','按文件名快速查找并打开项目文件'),'global_search':('导航与搜索','在项目文件中搜索文本'),'goto_definition':('语言与诊断','跳转到光标处符号的定义'),'goto_next_diag':('语言与诊断','跳转到下一条诊断'),'goto_prev_diag':('语言与诊断','跳转到上一条诊断'),'goto_reference':('语言与诊断','查看光标处符号的引用'),'insert_mode':('Helix 模式','进入插入模式以输入文本'),'lsp_or_syntax_symbol_picker':('语言与诊断','按名称查找当前文件中的符号'),'normal_mode':('Helix 模式','回到普通模式'),'open_above':('编辑与剪贴板','在当前行上方插入新行'),'open_below':('编辑与剪贴板','在当前行下方插入新行'),'redo':('编辑与剪贴板','重做上一次撤销的修改'),'rename_symbol':('语言与诊断','通过语言服务重命名当前符号及其引用'),'select_all':('选择与多光标','选择当前文件的全部内容'),'switch_source_header':('语言与诊断','在 C/C++ 源文件和对应头文件之间切换'),'toggle_comments':('编辑与剪贴板','为当前行或选区添加或取消注释'),'undo':('编辑与剪贴板','撤销上一次编辑事务')}
EXTRA=[
('浮窗操作','F4','工作区','打开或关闭唯一的快捷键速查浮窗'),('浮窗操作','Esc','速查浮窗','关闭快捷键速查浮窗'),('浮窗操作','鼠标左键点击 [x]','浮窗标题右侧','关闭快捷键速查浮窗'),('浮窗操作','鼠标左键拖动标题','速查浮窗','移动窗口，保持在工作区可见范围内'),('浮窗操作','鼠标左键拖动边缘或四角','速查浮窗','调整窗口宽度和高度，内容自动换行与分栏'),('浮窗操作','鼠标滚轮 / Up / Down','速查浮窗','向上或向下滚动快捷键列表'),('浮窗操作','PageUp / PageDown','速查浮窗','按当前显示高度向前或向后翻页'),('浮窗操作','Home / End','速查浮窗','跳到快捷键列表的开头或结尾'),('浮窗操作','/','速查浮窗','输入文字搜索快捷键、功能说明或使用场景'),('浮窗操作','Ctrl+U','速查浮窗','清除搜索文字并显示全部快捷键'),
('工作区与终端','Alt+Left / Alt+Right / Alt+Up / Alt+Down','Zellij 普通模式','将焦点移动到相邻工作区面板'),('工作区与终端','Ctrl+o → d','工作区','从当前工作区会话分离，程序继续运行'),('工作区与终端','Ctrl+q','工作区','退出当前工作区会话'),('工作区与终端','Ctrl+g','Zellij','进入或退出锁定模式，让其他按键直接传给当前应用'),('工作区与终端','Alt+鼠标左键点击路径','Git 或 shell 输出','将终端中高亮的文件路径交给现有编辑器打开'),('工作区与终端','终端粘贴','编辑器','通过终端粘贴文本；默认剪贴板提供者不能读取外部剪贴板'),
('鼠标与文件树','鼠标左键拖动','编辑器','从拖动起点到终点选择文本'),('鼠标与文件树','鼠标双击 / 双击后拖动','编辑器','选择当前单词；继续拖动时按完整单词扩展选择'),('鼠标与文件树','鼠标中键拖动','编辑器','按显示列建立矩形选区和多个编辑光标'),('鼠标与文件树','鼠标右键','编辑器','打开统一菜单；格式化操作按当前语言服务能力启用'),('鼠标与文件树','鼠标单击 / 双击文件','文件树','单击预览文件；双击固定标签并聚焦编辑区'),('鼠标与文件树','Ctrl+鼠标左键 / Alt+鼠标左键','文件树','增加或取消一个文件选择'),('鼠标与文件树','Shift+鼠标左键','文件树','选择从锚点到点击位置的一段连续文件'),('鼠标与文件树','Up / Down / Home / End','文件树','移动文件树中的当前项目'),('鼠标与文件树','Left / Right','文件树','折叠、展开目录或预览文件'),('鼠标与文件树','Enter','文件树','打开当前文件并切换到编辑区'),('鼠标与文件树','F2','文件树','重命名当前文件或目录'),('鼠标与文件树','Delete','文件树','确认后永久删除选中的文件或目录'),('鼠标与文件树','Ctrl+C / Ctrl+V','文件树','复制或粘贴选中的文件与目录'),('鼠标与文件树','Shift+F10 / 鼠标右键','文件树','打开当前文件或多选文件的操作菜单'),('鼠标与文件树','Shift+H / Shift+I','文件树','切换隐藏文件或忽略文件的显示'),
('编辑与剪贴板','鼠标右键 → Paste','编辑器','替换选区或在光标处粘贴；可用内容取决于剪贴板提供者'),('语言与诊断','鼠标右键 → Format Document','编辑器','使用当前语言的格式化工具整理整个文件'),('语言与诊断','选择文本 → 鼠标右键 → Format Selection','编辑器','格式化所选语法区域；提供者可能同时整理附近代码'),('语言与诊断',':lsp-restart','编辑器命令行','重新读取项目配置并重启当前文件的语言服务'),
('Helix 模式','i / a','编辑器 · 普通模式','在光标前或后进入插入模式'),('Helix 模式','v','编辑器 · 普通模式','进入选择模式，以移动操作扩展选区'),('Helix 模式','h / j / k / l','编辑器 · 普通或选择模式','分别向左、下、上、右移动光标或选择边界'),('Helix 模式','w / b','编辑器 · 普通或选择模式','按单词向前或向后移动'),('Helix 模式','g → g / Shift+G','编辑器 · 普通或选择模式','跳转到文件开头或结尾'),('Helix 模式',':','编辑器 · 普通模式','输入编辑器命令，例如保存、退出或重启语言服务')]
EXTRA += [
('鼠标与文件树','Ctrl+A','文件树','选择当前文件树中显示的所有非根项目'),
('工作区与终端','Alt+N','Zellij 非锁定模式','在当前工作区中新增一个面板'),('工作区与终端','Alt+F','Zellij 非锁定模式','显示或隐藏普通浮动面板；置顶速查窗口继续显示'),('工作区与终端','Alt+= / Alt+-','Zellij 非锁定模式','增大或缩小当前面板'),('工作区与终端','Alt+I / Alt+O','Zellij 非锁定模式','将当前工作区标签向左或向右移动'),('工作区与终端','Alt+[ / Alt+]','Zellij 非锁定模式','切换到前一个或下一个面板布局'),('工作区与终端','Ctrl+N → Left / Right / Up / Down','Zellij 普通模式','进入调整大小模式，沿指定边缘增大当前面板'),('工作区与终端','Ctrl+N → Shift+H / Shift+J / Shift+K / Shift+L','Zellij 普通模式','进入调整大小模式，从左、下、上、右缩小当前面板'),('工作区与终端','Ctrl+T → n / x','Zellij 普通模式','新建或关闭一个工作区标签'),('工作区与终端','Ctrl+T → Left / Right','Zellij 普通模式','切换到前一个或下一个工作区标签'),('工作区与终端','Ctrl+T → 1 … 9','Zellij 普通模式','切换到指定编号的工作区标签'),('工作区与终端','Ctrl+O → Ctrl+P → f','Zellij 普通模式','进入面板模式，将当前面板全屏显示或恢复布局'),('工作区与终端','Ctrl+O → Ctrl+P → d / r','Zellij 普通模式','在当前面板下方或右侧新建面板'),('工作区与终端','Ctrl+O → Ctrl+P → x','Zellij 普通模式','关闭当前面板'),('工作区与终端','Ctrl+O → Ctrl+P → e','Zellij 普通模式','在平铺和浮动面板之间切换'),('工作区与终端','Ctrl+O → Ctrl+S','Zellij 普通模式','进入当前终端面板的历史输出滚动模式'),('工作区与终端','Esc / Enter','Zellij 调整大小、面板或标签模式','退出当前管理模式，回到普通模式'),
('选择与多光标','Left / Right / Up / Down','编辑器','移动光标；显式选区按方向收拢或移动'),('选择与多光标','Shift+Left / Shift+Right / Shift+Up / Shift+Down','编辑器','按字符或显示行扩展当前选择'),('选择与多光标','Home / End','编辑器','移动到当前行的开头或结尾'),('编辑与剪贴板','Backspace / Delete','编辑器 · 插入模式','删除光标前后的字符；存在显式选区时删除选区'),
('Helix 模式','d / c','编辑器 · 普通或选择模式','删除选择；或删除选择后进入插入模式'),('Helix 模式','y / p / Shift+P','编辑器 · 普通或选择模式','复制到内部寄存器，或在选择后方、前方粘贴内部寄存器'),('Helix 模式','= / > / <','编辑器 · 普通或选择模式','格式化选择、增加缩进或减少缩进'),('Helix 模式','m → m','编辑器 · 普通或选择模式','跳转到匹配的括号'),('Helix 模式','g → n / g → p','编辑器 · 普通或选择模式','切换到下一个或上一个已打开的文件'),('Helix 模式','Space → b','编辑器 · 普通模式','从已打开文件列表中选择文件'),('Helix 模式','Ctrl+W → s / v','编辑器 · 普通或选择模式','在编辑区中水平或垂直分割视图'),('Helix 模式','Ctrl+W → q','编辑器 · 普通或选择模式','关闭当前编辑区分割视图')]
ORDER=['浮窗操作','文件与会话','导航与搜索','编辑与剪贴板','选择与多光标','语言与诊断','调试','鼠标与文件树','工作区与终端','Helix 模式']
def display(key):
 parts=key.split('-');mods=[]
 while len(parts)>1 and parts[0] in ['C','S','A']:
  mods.append({'C':'Ctrl','S':'Shift','A':'Alt'}[parts.pop(0)])
 base='-'.join(parts);base={'ret':'Enter','esc':'Esc','space':'Space','left':'Left','right':'Right','up':'Up','down':'Down','backspace':'Backspace','tab':'Tab'}.get(base,base)
 if mods and len(base)==1 and base.isascii() and base.isalpha():base=base.upper()
 return '+'.join(mods+[base])
def build():
 cfg=tomllib.loads((HERE.parent/'config/config.toml').read_text());bindings={}
 def walk(node,mode,prefix=()):
  for key,value in node.items():
   keys=prefix+(key,)
   if isinstance(value,dict):walk(value,mode,keys);continue
   if key=='F24':continue # terminal transport alias for Ctrl+Shift+Z
   commands=[value] if isinstance(value,str) else value
   for command in commands:assert command in DESCRIPTIONS,command
   token=(' → '.join(display(k) for k in keys),tuple(commands))
   bindings.setdefault(token,[]).append(mode)
 for mode,node in cfg['keys'].items():walk(node,mode)
 labels={'normal':'普通模式','insert':'插入模式','select':'选择模式'}
 entries=[]
 for (key,commands),modes in bindings.items():
  category=DESCRIPTIONS[commands[-1]][0]
  context='编辑器' if len(modes)==3 else '编辑器 · '+' / '.join(labels[m] for m in modes)
  description='；'.join(DESCRIPTIONS[c][1] for c in commands)
  entries.append({'category':category,'keys':key,'context':context,'description':description,'commands':list(commands)})
 entries.extend({'category':category,'keys':key,'context':context,'description':description,'commands':[]} for category,key,context,description in EXTRA)
 entries.sort(key=lambda e:ORDER.index(e['category']))
 return {'schema_version':1,'title':'默认快捷键速查','entries':entries}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
 text=json.dumps(build(),ensure_ascii=False,indent=2)+'\n';target=HERE/'shortcuts.json'
 if args.check:assert target.read_text()==text,'Shortcut catalogue differs from shipped bindings'
 else:target.write_text(text)
 print('Shortcut catalogue:',len(build()['entries']),'entries')
