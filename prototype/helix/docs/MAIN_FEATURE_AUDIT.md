# main 额外功能 → VS Code 语义 → Helix 迁移审计

Latest C/C++ configuration validation: [CPP_PROPERTIES.md](CPP_PROPERTIES.md).

Latest editor interaction validation: [EDITOR_CONTEXT_ACTIONS.md](EDITOR_CONTEXT_ACTIONS.md).

右键菜单跟随鼠标及边缘定位的后续改进见 [CONTEXT_MENU_PLACEMENT.md](CONTEXT_MENU_PLACEMENT.md)。

删除行为与弹窗绘制的后续修复见 [DELETE_BEHAVIOR.md](DELETE_BEHAVIOR.md)。

后续 Unicode 列选择复核发现并修复了原测试未覆盖的边界，见 [Unicode 列选择修复与验收](UNICODE_COLUMN_SELECTION.md)。原有验收是当时的测试结果，不代表覆盖了这些新增案例。

基线：`main@b10574bee0c85ef6ed51b620729d212760ee2520`。逐文件 SHA-256 清单见 [main-baseline.json](main-baseline.json)。
VS Code 源码参考：`e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`；文件和符号出处见 [VSCODE_REFERENCES.md](VSCODE_REFERENCES.md)。

本清单共 **160 项**，来自明确配置、定制源码与基线中声明的依赖能力。语言/DAP 的“已安装包”与“实际启用功能”分开记录，不把 lock 文件中的名字当作已实现。

## 结论与证据边界

实现对齐以文件操作结果、选择/光标状态、保存与焦点生命周期为准，不把“菜单上有这个名字”当作功能通过。主要用户链路有 PTY 回归；语言服务另有真实协议初始化，Python/C 调试另有真实程序断点、栈、变量、单步与继续测试。最终执行批次与二进制指纹见 [VALIDATION.md](VALIDATION.md)。

保留的 TUI 合同：固定工作区区域、i/Esc 模态入口、Ctrl-Q 会话退出、Alt-G、树内 Alt 多选别名、根节点相对路径点号，以及不重新加载 shell 初始化文件。这些来自用户明确约束，不描述成 VS Code 的默认设置。原生 GUI 菜单像素布局、Shada/Vim 内部数据格式、VS Code 专用富剪贴板元数据不属于跨终端承诺。

主分支保留为可审计基线；发现的旧行为差异在 Helix 迁移分支纠正，没有偷偷修改 main。未实现于 main 的拖放文件移动、标签多选批量操作、整个扩展市场不纳入“迁移完成”的分母。

## 工作区、会话与环境

基线源码：`bin/devtui`、`bin/devtui-shell-pane`、`config/zellij/config.kdl.in`、`config/zellij/layouts/dev.kdl.in`、`config/zellij/layouts/dev-wide.kdl.in`。

Helix 实现：`prototype/helix/bin/devtui-helix`、`prototype/helix/bin/devtui-helix-shell-pane`、`prototype/helix/zellij`。

验证入口：`deployment_regression.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 01-01 | 指定目录启动 | 工作目录由启动参数或调用者的当前目录决定 | 主分支已有；迁移保留并核对行为 |
| 01-02 | 编辑器/Git/shell/横幅布局 | 三个工作区域并列组合；布局不改变工具链 | devtui 的终端工作区约定，不是 VS Code 像素布局 |
| 01-03 | 宽屏自适应 | 宽度达到阈值选择 wide 布局；异常尺寸有回退 | 主分支已有；迁移保留并核对行为 |
| 01-04 | 完整退出 | Ctrl-Q 退出 Zellij 会话 | 有意保留 devtui 会话快捷键 |
| 01-05 | 分离/恢复会话 | Zellij detach/attach 保留进程 | 复用固定版本的终端复用器，不重写功能 |
| 01-06 | 导出的开发环境继承 | PATH、编译器、SDK、locale、代理和用户变量不被启动器改写 | 修正 Bash 启动器可能读取 BASH_ENV 的漏洞 |
| 01-07 | 不重新执行 shell 初始化 | 右下 shell 不读 rc/profile 或自动启用工具链 | Helix 启动器/终端 helper 使用隔离的 Python exec，最终 Bash --noprofile --norc -i |
| 01-08 | 编辑区域不被关掉 | 关闭文件不拆掉编辑器结构 | 用户要求；类似 closeEmptyGroups=false 的保留工作区约定 |
| 01-09 | Explorer 保持存在 | Esc/q 和打开其他文件不意外关闭目录树 | 用户明确保留的固定侧栏约定，不声称 VS Code 不能隐藏侧栏 |

## 标签、Preview 与文档生命周期

基线源码：`config/nvim/lua/config/devtui_preview.lua`、`config/nvim/lua/config/devtui_tabs.lua`、`config/nvim/lua/config/devtui_regions.lua`、`config/nvim/lua/plugins/devtui-interaction.lua`。

Helix 实现：`helix-view/src/editor.rs`、`helix-term/src/ui/editor.rs`、`helix-term/src/ui/devtui.rs`、`helix-term/src/commands/typed.rs`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 02-01 | 单击 Preview | 只复用一个未固定预览文档 | 主分支已有；迁移保留并核对行为 |
| 02-02 | 双击保持打开 | 结束 Preview 状态，保持文档；不是 sticky 置顶 | pinned 与 sticky 必须区分；同时修正双击后编辑器焦点 |
| 02-03 | 编辑自动保持打开 | 实际修改时 Preview 立即晋升，之后不再被替换 | 主分支已有；迁移保留并核对行为 |
| 02-04 | 已固定文档不被 Preview 替换 | 新 Preview 不复用固定标签 | 主分支已有；迁移保留并核对行为 |
| 02-05 | 再次打开已有文档 | 切换现有标签，不重复创建，不改变其他 Preview 状态 | 修复旧迁移实现把另一个 Preview 一并固定的问题 |
| 02-06 | Preview 样式 | 可视上区分可复用预览与保持打开的标签 | 主分支已有；迁移保留并核对行为 |
| 02-07 | 标签栏始终存在 | 新增/关闭标签不造成首行布局跳动 | 主分支已有；迁移保留并核对行为 |
| 02-08 | 单击切换标签 | 命中真实已渲染标签，切换目标文档 | 主分支已有；迁移保留并核对行为 |
| 02-09 | 关闭按钮始终可用 | dirty 圆点与关闭命中区域分开 | 主分支通过末端几何补丁模拟；Helix 直接存储渲染命中矩形 |
| 02-10 | 未保存关闭三分支 | Save 成功后关闭；Don't Save 丢弃；Cancel 不变 | 主分支已有；迁移保留并核对行为 |
| 02-11 | 保存失败保护 | 失败保留文档与修改，取消延迟关闭状态 | 修正后续一次普通保存意外关闭文档的问题 |
| 02-12 | Untitled 参与关闭确认 | 未命名修改也必须询问 | 主分支已有；迁移保留并核对行为 |
| 02-13 | Untitled 保存/另存 | Save As，路径确认一次 Enter 生效，取消不改文档 | 主分支已有；迁移保留并核对行为 |
| 02-14 | 命名文档 Save As | 切换文档身份到新路径，而不只是写一份副本 | 主分支 Ctrl-Shift-S 使用 :write path；Helix 按真正 Save As 纠正 |
| 02-15 | 覆盖确认 | 覆盖已有目标必须确认，另一个 dirty 标签不能被静默覆盖 | 补齐主分支和早期迁移缺少的安全边界 |
| 02-16 | 标签栏空白双击 | 创建新 Untitled，不误触已有标签 | 主分支已有；迁移保留并核对行为 |
| 02-17 | 关闭最后一个标签 | 保留编辑区域与空文档 | 主分支已有；迁移保留并核对行为 |
| 02-18 | 本地 q/quit/close | 当前文档关闭，dirty 时确认 | TUI 命令映射约定；避免主分支 QuitPre 异常控制流 |
| 02-19 | 强制 q!/quit!/close! | 丢弃当前文档，不删除工作区区域 | 主分支已有；迁移保留并核对行为 |
| 02-20 | wq/wq! | 保存成功才关闭；Untitled 先 Save As | 主分支已有；迁移保留并核对行为 |
| 02-21 | x/xit/exit/ZZ/ZQ | 按是否修改选择保存关闭或丢弃关闭 | 主分支已有；迁移保留并核对行为 |
| 02-22 | qa/qall/wqa 等全局关闭 | 不拆掉 devtui 编辑进程，完整退出通过 Ctrl-Q | TUI 保留约定，不宣称是 VS Code 原生命令 |
| 02-23 | 标签溢出 | 活动标签和关闭控件仍可达 | 迁移额外修正，避免宽文件名挤掉当前标签 |

## 目录树、选择与尺寸

基线源码：`config/nvim/lua/config/devtui_explorer_context.lua`、`config/nvim/lua/config/keymaps.lua`。

Helix 实现：`helix-term/src/ui/devtui.rs`、`helix-term/src/ui/editor.rs`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 03-01 | 常驻目录树 | 真实侧栏与真实编辑器并排，不是文件选择弹层 | 主分支已有；迁移保留并核对行为 |
| 03-02 | 明确根节点 | 首行是工作目录，用它执行根目录操作 | 主分支已有；迁移保留并核对行为 |
| 03-03 | 普通单选 | 单击 B 替代 A 的选择，而不是累加 | 主分支已有；迁移保留并核对行为 |
| 03-04 | Ctrl 单击多选 | 切换该项并保留其他选择 | 主分支已有；迁移保留并核对行为 |
| 03-05 | Alt 单击多选别名 | 只在树内作为 Ctrl 多选的等价入口 | 为终端兼容保留的用户约定；不冒充 VS Code 默认 Alt-click |
| 03-06 | 已选项右键 | 保留当前多选，菜单动作作用于整组 | 主分支已有；迁移保留并核对行为 |
| 03-07 | 未选项右键 | 该项成为上下文目标，不误操作旧选择 | 主分支已有；迁移保留并核对行为 |
| 03-08 | 跨区域首次点击 | Insert 模式或其他区域有焦点时，第一次点树即打开 | 主分支已有；迁移保留并核对行为 |
| 03-09 | 单击保留树焦点 | Preview 后可继续导航树 | 主分支已有；迁移保留并核对行为 |
| 03-10 | 双击移动编辑焦点 | 文件保持打开且立即可按 i 编辑 | 严格审计补齐早期迁移只固定但不转移焦点的问题 |
| 03-11 | 展开与折叠目录 | 目录操作不创建文件标签 | 主分支已有；迁移保留并核对行为 |
| 03-12 | 隐藏/忽略文件默认显示 | 保持 devtui 既有设置 | 配置选择，不是 VS Code 全局默认值 |
| 03-13 | 隐藏/忽略切换 | 只改变树的可见性过滤 | 主分支已有；迁移保留并核对行为 |
| 03-14 | Explorer 聚焦快捷键 | 存在则聚焦，不是 toggle-close | 主分支已有；迁移保留并核对行为 |
| 03-15 | 树轮滚动 | 移动视口，不能被旧选择强行拉回 | 主分支已有；迁移保留并核对行为 |
| 03-16 | 右侧宽度拖动 | 同一次按住允许停顿、往返拖动 | 主分支已有；迁移保留并核对行为 |
| 03-17 | 三字符热区 | 便于终端命中边缘 | 终端尺寸适配，不是 VS Code 像素值 |
| 03-18 | 最小树宽度 | 最小 12 列，同时保留编辑器空间 | 主分支已有；迁移保留并核对行为 |
| 03-19 | 宽度记忆 | 重启后恢复侧栏宽度 | 主分支已有；迁移保留并核对行为 |
| 03-20 | 根目录替代空白右键 | 不重新加入用户已撤销的空白区右键逻辑 | 保留明确要求的交互范围 |
| 03-21 | 键盘树导航 | 上下移动选择；左右折叠/父项/展开/子项；Enter 打开文件 | 迁移中补齐键盘上下文，原版来自 Snacks 原生树导航 |

## 文件操作与路径剪贴板

基线源码：`config/nvim/lua/config/devtui_explorer_context.lua`。

Helix 实现：`helix-term/src/ui/devtui.rs`、`helix-view/src/editor.rs`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 04-01 | 根/目录新建文件 | 在目标目录创建，打开并保持新文件 | 主分支已有；迁移保留并核对行为 |
| 04-02 | 根/目录新建文件夹 | 创建目录并展开/选中结果 | 主分支已有；迁移保留并核对行为 |
| 04-03 | 嵌套相对路径新建 | 创建父目录，禁止越出所选目录 | 主分支已有；迁移保留并核对行为 |
| 04-04 | 已有名称保护 | 新建不能清空原文件，Rename 不能静默覆盖 | 主分支已有；迁移保留并核对行为 |
| 04-05 | 文件/文件夹复制 | 存储独立的文件剪贴板，不混入文本剪贴板 | 主分支已有；迁移保留并核对行为 |
| 04-06 | 目录粘贴 | 有文件剪贴板才可用，禁用项不能执行 | 主分支已有；迁移保留并核对行为 |
| 04-07 | 同目录重复命名 | name copy、name copy 2，扩展名保留 | 补齐 copy 0、无空格/多空格字面后缀与大整数退路；避免饱和计数卡死并逐候选检查冲突 |
| 04-08 | 复制项自身粘贴 | 在父目录生成副本，不嵌套复制自身 | 按 VS Code 源码纠正原来一律拒绝自身目标的区别 |
| 04-09 | 子孙目录粘贴保护 | 执行前拒绝源目录的子孙目标，防止递归 | 主分支已有；迁移保留并核对行为 |
| 04-10 | 符号链接复制 | 复制链接而非无限跟随循环 | 主分支已有；迁移保留并核对行为 |
| 04-11 | 单个粘贴文件打开 | 结果固定并揭示，保留树焦点 | 主分支已有；迁移保留并核对行为 |
| 04-12 | 复制绝对路径 | 写到系统剪贴板，不读取终端剪贴板 | 主分支已有；迁移保留并核对行为 |
| 04-13 | 复制相对路径 | 相对工作目录；根节点使用点号 | 根节点点号沿用用户合同 |
| 04-14 | 多选路径复制 | 按文档/列表次序换行分隔 | 主分支已有；迁移保留并核对行为 |
| 04-15 | 多选复制/删除 | 对整组操作，父子重复目标去重 | 主分支已有；迁移保留并核对行为 |
| 04-16 | 删除确认 | 确认后操作，dirty 文件有数据丢失警告 | 主分支已有；迁移保留并核对行为 |
| 04-17 | 按提供者能力删除 | 回收站要求配置启用且提供者声明 Trash 能力；当前终端提供者直接确认永久删除 | 已纠正无条件调用 gio 的实现，见删除修复报告 |
| 04-18 | 删除打开文件 | 移除对应文档，保留编辑区，避免稍后保存又复活 | 主分支已有；迁移保留并核对行为 |
| 04-19 | Rename | 修改路径，更新已打开文件/子文件身份 | 主分支自定义右键菜单未列 Rename；属原生树入口与迁移补全 |

## 鼠标文本选择与多光标

基线源码：`config/nvim/lua/plugins/multicursor.lua`、`config/nvim/lua/config/keymaps.lua`。

Helix 实现：`helix-term/src/ui/editor.rs`、`helix-term/src/commands.rs`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 05-01 | 左键定位与拖选 | 字符区定位，选区采用半开边界 | 主分支已有；迁移保留并核对行为 |
| 05-02 | 普通复制保留选区 | Copy 不取消高亮 | 主分支已有；迁移保留并核对行为 |
| 05-03 | 中键垂直光标 | 每个经过行产生原生 caret | 主分支已有；迁移保留并核对行为 |
| 05-04 | 中键矩形选择 | 左右/上下任意拖动方向一致 | 主分支已有；迁移保留并核对行为 |
| 05-05 | 短行夹取 | 零宽拖选夹取到 EOL | 主分支已有；迁移保留并核对行为 |
| 05-06 | 稀疏矩形 | 真正到不了左边界的行跳过；等于边界保留 EOL caret | 主分支已有；迁移保留并核对行为 |
| 05-07 | 全短行后备 | 所有行均到不了矩形时，每行 EOL 产生 caret | 主分支已有；迁移保留并核对行为 |
| 05-08 | Insert 中中键 | 不进入原生中键贴上路径，不请求 OSC52 读取 | 主分支已有；迁移保留并核对行为 |
| 05-09 | 实时多光标输入 | 每个按键当下更新全部 caret | 主分支插件在离开 Insert 后回放；Helix 原生事务消除这一差异 |
| 05-10 | Insert 方向移动 | 所有 caret 同步移动，不越界弹异常 | 主分支已有；迁移保留并核对行为 |
| 05-11 | 选择上的方向键 | 左右先收起到对应边界，不额外多走一格 | 主分支折叠再移动的近似实现不是精确 VS Code 规则；迁移修正 |
| 05-12 | 多选右键 Copy/Cut/Delete | 按选区动作，不误开符号菜单 | 主分支已有；迁移保留并核对行为 |
| 05-13 | 框选复制保留 | Copy 不改变原选区 | 主分支已有；迁移保留并核对行为 |
| 05-14 | 稀疏复制 | 不为真正跳过的行制造空白剪贴板行 | 主分支已有；迁移保留并核对行为 |
| 05-15 | 按行分配粘贴 | 行数等于 caret 数则逐行分配，否则各接收完整文本 | 主分支已有；迁移保留并核对行为 |
| 05-16 | 粘贴替换选区 | 一次 undo 事务替换，不在选区前插入 | 本轮严格测试发现并修复 |
| 05-17 | 剪切后粘贴锚点 | 剪切后是 caret，不误删下一个字符 | 主分支已有；迁移保留并核对行为 |
| 05-18 | 上下添加光标 | 保留其他 caret | 主分支已有；迁移保留并核对行为 |
| 05-19 | 匹配词增选 | 第一次选词，下次增选后续匹配；全部匹配入口 | 主分支第一次可能立即增选；迁移按 VS Code 纠正 |
| 05-20 | Esc 收起额外光标 | Normal Esc 清除额外 caret，Insert Esc 先退出输入 | 保留原 TUI 模态约定 |

## VS Code 风格快捷键与文本命令

基线源码：`config/nvim/lua/config/keymaps.lua`。

Helix 实现：`prototype/helix/config/config.toml`、`helix-term/src/commands.rs`、`helix-term/src/ui/editor.rs`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 06-01 | Ctrl-S 保存 | 命名文档保存，Untitled 弹出路径输入 | 主分支已有；迁移保留并核对行为 |
| 06-02 | Ctrl-Shift-S 另存 | Save As 真实切换文档路径 | 主分支已有；迁移保留并核对行为 |
| 06-03 | Ctrl-Z 撤销 | 作用于合理事务，不破坏多光标 | 主分支已有；迁移保留并核对行为 |
| 06-04 | Ctrl-Y/Ctrl-Shift-Z 重做 | 重做与引用导航不能冲突 | 修复旧转发序列实际对应 Shift-F12，以及 CSI-u Shift 规范化 |
| 06-05 | Ctrl-C 复制 | 有明确选择复制选择，否则复制当前行 | 主分支已有；迁移保留并核对行为 |
| 06-06 | Ctrl-X 剪切 | 选择或整行剪切，之后 caret 可直接粘贴 | 主分支已有；迁移保留并核对行为 |
| 06-07 | Ctrl-A 全选 | 选择整个内容；输入替换，取消不修改 | 主分支已有；迁移保留并核对行为 |
| 06-08 | Ctrl-L 选择当前行 | 行选择可以继续扩展 | 主分支已有；迁移保留并核对行为 |
| 06-09 | Ctrl-/ 注释 | 根据语言对选择行切换行注释 | 主分支已有；迁移保留并核对行为 |
| 06-10 | Ctrl-Enter 插入下行 | 进入新行输入 | 主分支已有；迁移保留并核对行为 |
| 06-11 | Ctrl-Shift-Enter 插入上行 | 进入新行输入 | 主分支已有；迁移保留并核对行为 |
| 06-12 | Ctrl-Shift-K 删除行 | 删除当前/选中行，维护编辑状态 | 主分支已有；迁移保留并核对行为 |
| 06-13 | 快捷键多模式支持 | 适用动作在 Normal/Insert/Select 都可触发 | 不只配置 Normal 模式 |
| 06-14 | Esc/命令前缀兼容 | 保留 Helix 模态操作，不伪造无模式编辑器 | 主分支已有；迁移保留并核对行为 |

## 查找、替换与导航

基线源码：`config/nvim/lua/config/keymaps.lua`、`config/nvim/lua/plugins/devtui-interaction.lua`。

Helix 实现：`helix-term/src/commands.rs`、`helix-term/src/ui/devtui.rs`、`helix-term/src/ui/mod.rs`、`prototype/helix/config/config.toml`。

验证入口：`terminal_regression.py`、`strict_parity.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 07-01 | Ctrl-F 查找 | 默认字面量、不区分大小写；可切换大小写/全词/正则 | 主分支映射 Vim /，默认语义不同；已纠正 |
| 07-02 | Find 正则错误 | 不修改文档，显示错误可继续编辑 | 主分支已有；迁移保留并核对行为 |
| 07-03 | Ctrl-H 当前文件替换 | 可预览并逐项/全部应用，结果仍 dirty | 主分支已有；迁移保留并核对行为 |
| 07-04 | 未命名文档替换 | 不需要先保存 | 主分支已有；迁移保留并核对行为 |
| 07-05 | Ctrl-Shift-F 项目搜索 | 以打开工作目录为范围 | 主分支已有；迁移保留并核对行为 |
| 07-06 | Ctrl-Shift-H 项目替换 | 预览并按匹配/文件/全部应用；显式保存目标 | 按 VS Code replaceService 修正早期迁移对于已打开文件的错误假设 |
| 07-07 | 字面量替换文本 | 非正则模式中美元符号不当作捕获组 | 主分支已有；迁移保留并核对行为 |
| 07-08 | 正则捕获替换 | 显式正则模式支持捕获引用 | 主分支已有；迁移保留并核对行为 |
| 07-09 | Ctrl-P Quick Open | 限制打开工作目录，确认后真实编辑器获得焦点 | 修复向上发现无关父 Git 仓库和保留旧树焦点的问题 |
| 07-10 | Ctrl-Shift-P/F1 命令面板 | 执行命令的后续 UI 回调不能丢失 | 主分支已有；迁移保留并核对行为 |
| 07-11 | Alt-G 行号跳转 | 正整数校验，越界夹取 | Ctrl-G 被终端复用器使用，保留 Alt-G 适配 |
| 07-12 | Ctrl-Shift-O 文件符号 | 使用 LSP/语法树可用的符号 | 主分支已有；迁移保留并核对行为 |
| 07-13 | F2 Rename、F12 定义、Shift-F12 引用 | 有语言服务能力才执行相应动作 | 主分支已有；迁移保留并核对行为 |
| 07-14 | Ctrl-. Code Action | 调用当前上下文的语言服务操作 | 主分支已有；迁移保留并核对行为 |
| 07-15 | F8/Shift-F8 诊断导航 | 前后跳转诊断位置 | 主分支已有；迁移保留并核对行为 |
| 07-16 | 编辑器符号右键菜单 | 定义/声明/引用/实现/类型/Hover/Rename/Code Action 及键盘入口 | 主分支已有；迁移保留并核对行为 |

## 外部文件、Git 与剪贴板传输

基线源码：`bin/tui-nvim-open`、`patches/zellij-link-devtui.patch`、`patches/zellij-0.45.1-mouse-passthrough.patch`、`config/lazygit/config.yml.in`、`config/nvim/lua/config/options.lua`、`config/nvim/lua/plugins/tui-dev.lua`。

Helix 实现：`prototype/helix/bin/devtui-helix-open`、`helix-term/src/application.rs`、`prototype/helix/zellij/link-paths.patch`、`prototype/helix/config/lazygit.yml`。

验证入口：`terminal_regression.py`、`strict_parity.py`、`Zellij link native tests`、`deployment_regression.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 08-01 | 终端文件点击 | 终端 Alt-click 文件位置发给当前编辑器，不新开独立实例 | 主分支已有；迁移保留并核对行为 |
| 08-02 | 行号和列号 | path:line:column 与 path(line,column)，一基计数 | 主分支已有；迁移保留并核对行为 |
| 08-03 | Unicode 列位置 | 外部列按 UTF-16 单位转换并在字符/EOL 边界夹取 | 新增 Unicode 回归 |
| 08-04 | 相对和绝对路径 | 支持常规相对、./、绝对、环境变量与用户目录形式 | 主分支已有；迁移保留并核对行为 |
| 08-05 | 带空格/Unicode 路径 | 引号和定位后缀分离，不把引号算入文件名 | 本轮补齐 link 高亮与解析测试 |
| 08-06 | 工作区外文件 | 在现有编辑区打开，不替换根目录树 | 主分支已有；迁移保留并核对行为 |
| 08-07 | 编辑器聚焦 | 外部导航聚焦已有 Zellij 编辑 pane | 主分支已有；迁移保留并核对行为 |
| 08-08 | Lazygit 编辑入口 | e/open-at-line 复用运行实例 | 主分支已有；迁移保留并核对行为 |
| 08-09 | Git 暂存/差异/提交/分支/stash | 保留固定 Lazygit 版本与专用 pane | 第三方复用，不重新实现 Git；不在用户仓库做破坏性验收 |
| 08-10 | 编辑器内 Git 差异提示 | 保留原生 Git gutter，当前行 blame 不默认弹出 | 主分支显式关闭自动 blame |
| 08-11 | OSC52 写剪贴板 | Copy/Copy Path 只写，不读取终端剪贴板 | 主分支已有；迁移保留并核对行为 |
| 08-12 | 终端粘贴入口 | 使用 bracketed paste，从宿主获得纯文本 | 终端协议不保证传递 VS Code 私有 HTML/列剪贴板元数据 |
| 08-13 | 鼠标修饰键转发 | 树内 Ctrl/Alt 与 shell 文件跳转分域处理 | 主分支已有；迁移保留并核对行为 |
| 08-14 | IPC 边界保护 | 私有端点权限、读取超时、限制长度、校验目标，滞留客户端不堵塞后续 | 主分支已有；迁移保留并核对行为 |

## 视觉、编辑器附加与语言集成

基线源码：`config/nvim/lua/config/autocmds.lua`、`config/nvim/lua/plugins/scrollbar.lua`、`config/nvim/lua/plugins/clangd-inactive.lua`、`config/nvim/lua/config/lazy.lua`、`scripts/install-mason-tools.sh`、`config/nvim/lazy-lock.json`。

Helix 实现：`helix-term/src/ui/editor.rs`、`helix-view/src/document.rs`、`helix-term/src/application.rs`、`helix-lsp`、`prototype/helix/config/languages.toml`、`prototype/helix/scripts/install-tools.sh`。

验证入口：`strict_parity.py`、`terminal_regression.py`、`service_smoke.py`、`debugger_regression.py`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 09-01 | Markdown 原始标点 | 源码视图不隐藏反引号与围栏 | 主分支已有；迁移保留并核对行为 |
| 09-02 | 交互滚动条 | 拖动 thumb 移动视口，不编辑内容 | 主分支已有；迁移保留并核对行为 |
| 09-03 | 滚动条显隐 | 命令可临时切换 | 主分支已有；迁移保留并核对行为 |
| 09-04 | 滚动条搜索/诊断提示 | 按文档位置显示概览标记 | 严格读取 main 的 signs_on_startup 发现漏项后补齐 |
| 09-05 | 滚动条命名标记 | 保留文档标记显示及设置/跳转/删除入口 | Vim 标记无 VS Code 核心等价；以命名导航标记保留用途，不导入 Shada |
| 09-06 | 非活动条件编译区域 | 接受语言服务通知并淡化范围 | 主分支已有；迁移保留并核对行为 |
| 09-07 | 文件图标与字体 | 树/标签使用 Nerd Font 图标；字体不随仓库分发 | 主分支已有；迁移保留并核对行为 |
| 09-08 | C/C++/CUDA 语言服务 | clangd 与项目编译数据库，不注入主机 SDK | main 有安装声明与能力菜单，完整语言 extras 未显式导入；Helix 补齐通用配置 |
| 09-09 | Source/Header 切换 | 通过 clangd 对应请求执行 | 主分支环境文档声明，Helix 增加通用入口 |
| 09-10 | CMake 语言/格式化 | 独立语言服务及格式化工具 | 修正传递依赖升级导致服务无法启动，锁定兼容版本 |
| 09-11 | Bash 语言/检查/格式化 | 语言服务、ShellCheck、shfmt | main 主要依赖环境安装；Helix 明确配置和部署 |
| 09-12 | Python 语言/检查/格式化 | Pyright/Ruff，选定解释器用于语言服务 | main 安装声明不等于完整启用；Helix 提供可部署配置 |
| 09-13 | Python 环境选择 | 记忆工作区解释器，不修改右下 shell | 通用迁移补全，editor 专用环境与 shell 分开 |
| 09-14 | 调试常用动作 | 断点/启动/继续/暂停/单步/重启/停止/变量/栈 | main 的公共 extras 配置不完整；Helix 提供 DAP 集成并做真实进程测试 |
| 09-15 | LSP/工具健康查看 | 可检查实际加载与可执行程序 | 依赖可用性和真实服务初始化分别验收 |

## 部署、复现与发布

基线源码：`install.sh`、`uninstall.sh`、`versions.env`、`scripts/build-zellij.sh`、`scripts/install-system-deps-ubuntu.sh`、`scripts/install-mason-tools.sh`、`README.md`、`DEPLOYMENT.md`。

Helix 实现：`prototype/helix/install-prototype.sh`、`prototype/helix/scripts`、`prototype/helix/config/node-tools`、`prototype/helix/config/python-tools.lock.txt`。

验证入口：`deployment_regression.py`、`clean patch tree verification`、`release build`、`public tree scan`。

| ID | 额外功能 | 目标行为 | main 审计与迁移处理 |
|---|---|---|---|
| 10-01 | 固定依赖版本 | 固定编辑器源码 revision、插件/工具版本与原生工具基线 | 主分支已有；迁移保留并核对行为 |
| 10-02 | 补丁可复现 | 增量顺序明确，干净基线可完整应用并核对源码树 | 修复原累计 patch 与分步 patch 重复叠加导致安装失败 |
| 10-03 | 独立安装 | Helix 不覆盖 Neovim 的配置/启动器 | 主分支已有；迁移保留并核对行为 |
| 10-04 | 配置备份 | 替换前备份旧 Helix 设置 | 主分支已有；迁移保留并核对行为 |
| 10-05 | home 路径渲染 | 模板在目标用户安装时展开，不写入当前机器地址 | 主分支已有；迁移保留并核对行为 |
| 10-06 | 依赖隔离 | 编辑器工具安装在私有前缀，不修改 shell 初始化文件 | 主分支已有；迁移保留并核对行为 |
| 10-07 | 发布校验 | 提交文件、文件名、提交信息不泄露本机环境 | 主分支已有；迁移保留并核对行为 |
| 10-08 | 源码与运行版本一致 | 原子替换二进制与构建指纹，验收安装后的程序 | 恢复时已安装程序落后源码；本轮发布必须修正 |
| 10-09 | 回归可重跑 | 终端交互、协议、真实调试、部署测试进入版本库 | main 未提供这一套可重跑测试；这是本轮新增的迁移验收保障 |

## 严格审计纠正的典型误判

1. Ctrl-Shift-S 不能只写副本，Save As 必须更新文档身份。
2. 非空选区上的左右方向键不是收起后再多走一步。
3. 在矩形左边界恰好到达 EOL 的行并不是“被跳过的短行”。
4. 项目 Replace Service 显式保存目标；当前文档 Replace 不擅自保存。
5. Shift-F12 不能兼作 redo 转发，扩展键须按协议规范化。
6. Quick Open 的搜索根必须与打开目录一致，不能误扫描外层 Git 仓库。
7. Shell wrapper 本身也不能重新执行 BASH_ENV；仅最终 shell 加 --norc 不够。
8. 编译过的源码和实际安装运行的源码必须核对同一构建指纹。
9. 原生菜单吞掉鼠标、异步命令丢回调、复制递归或覆盖失败，均不能标成“功能已迁移”。
10. 回归通过只说明列出的场景；真实 Windows Terminal 鼠标/剪贴板权限与项目专用编译/硬件调试仍依赖宿主设置。

## 最后一轮编辑器调试验收

适配器单独可运行并不等于编辑器 F5 链路可用。最后补测发现默认解释器名称和子进程终端会话两个问题，已修正：优先使用工作区选定的有效解释器，否则发现 `python3`/`python`；适配器使用独立会话，避免被调试进程抢占编辑器终端控制权。失败时显示适配器提供的具体信息，不再只有 `None`。新增 `editor_debugger_regression.py` 验证断点、F5、变量、单步、调用栈、继续执行及所选环境实际生效。

## 恢复后独立复核：副本命名边界

新增三个 PTY 回归入口，验证数字零、没有分隔空格的名称、多空格字面后缀、空前缀、大整数、已有副本、点文件和多重扩展名。旧版在 `a copy 4294967295.txt` 自身重复粘贴时可能因计数饱和而陷入循环；新实现按 VS Code `incrementFileName` 与 `MAX_SAFE_SMALL_INTEGER` 规则生成下一个名称，不重复检查同一个候选。
