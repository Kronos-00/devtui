# 编辑区查找与替换

Ctrl+F 打开当前编辑视图右上角的查找面板；Ctrl+H 展开替换行。面板不改变正文区域的高度，只有一个实例；点击正文后可以继续编辑，匹配结果随编辑更新。Esc 或 × 关闭面板，关闭后清除搜索高亮和概览标记，保留当前文本选择。

拖动左侧边缘调整宽度，右侧保持贴齐正文区域；双击左边缘在最大宽度和默认宽度之间切换。宽度在本次编辑器会话内保留；切换文件和终端尺寸改变后重新限制在当前视图内。窄视图使用更紧凑的按钮字符。

| 位置 | 字符 | 功能 |
| --- | --- | --- |
| 左侧 | > / v | 展开或收起替换行 |
| 查找框内 | Aa / W / .* | 区分大小写 / 全字匹配 / 正则表达式 |
| 查找框外 | ↑ / ↓ / ≡ / × | 上一个 / 下一个 / 在选定内容中查找 / 关闭 |
| 替换框内 | AB | 保留大小写 |
| 替换框外 | ↦ / ⇉ | 替换当前匹配并前进 / 全部替换 |

底边显示当前匹配序号、总数、操作说明或正则错误。开启的选项使用选中样式。查找默认是字面量、不区分大小写、不限制为完整词。全字匹配采用 VS Code 默认单词分隔符，并考虑匹配内容自身的边界字符；下划线和非英文标识符字符不是默认分隔符。

## 输入与操作

- Enter / Shift+Enter：查找框中跳到下一个 / 上一个匹配，循环经过首尾。
- Alt+C / Alt+W / Alt+R：切换大小写 / 全词 / 正则。
- Alt+L / Alt+P：切换选区搜索 / 保留大小写。
- 替换框中 Enter：若当前选择就是一个匹配则替换，然后选择下一个；否则先定位匹配。
- Ctrl+Alt+Enter：一次替换全部匹配，一个撤销步骤。
- Tab / Shift+Tab：在输入框和按钮之间移动；Enter / Space 激活按钮。
- Ctrl+A、Ctrl+C/X/V、左右方向键、Home/End、Backspace/Delete：编辑框内的文本操作。外部剪贴板也可用终端粘贴。
- Ctrl+Enter 或终端粘贴：输入真正的多行文本；输入框最多显示三行，其余内容随光标滚动。

Ctrl+F 会用单行选择或光标处单词填入查找内容并选中输入框文字。Ctrl+H 的焦点按 VS Code 源码处理：从查找框触发或有可用单行选择时聚焦替换框，否则聚焦查找框。修改仍保留在编辑器缓冲区，Ctrl+S 保存；未命名文档也可直接替换。

选区搜索支持普通选择和多个列选择范围；启用前保留原选择，排除以后一行第 1 列结尾时多带入的行尾。范围随着插入、删除和替换移动。切换文件会清除旧文件范围。CRLF 文件按 LF 模型查找，再映射回原文件偏移；替换保留原有行尾类型。

## 替换字符串

只有启用正则表达式后才解释以下语法。普通模式下 `$1`、`$$`、`\n` 都是原文。

| 替换输入 | 正则模式结果 |
| --- | --- |
| `$1` … `$99` | 第 1 … 99 个捕获组 |
| `$0` / `$&` | 完整匹配 |
| `$$` | 一个字面量 `$` |
| `\n` / `\t` / `\\` | 换行 / 制表符 / 反斜线 |
| `\u$1` / `\l$1` | 捕获内容首个 UTF-16 单元转大写 / 小写 |
| `\U$1` / `\L$1` | 捕获内容其余字符转大写 / 小写 |
| `\u\u\u$1` / `\l\U$1` | 连用单字符转换 / 首字符小写且其余大写 |

例如查找 `([A-Za-z]+)-(\d+)`，替换 `$2:\U$1`，会把 `item-42` 变成 `42:ITEM`。

VS Code 当前文件替换的边界规则也已保留：未参与匹配的可选组变成空字符串；超出组数的两位引用向一位引用回退，例如只有一个组时 `$12` 是第 1 组加 `2`；若没有可回退的组则保留 `$12` 原文。`${1}` 和 `$<name>` 在此语法中保持原文。不要把其他工具的替换语法直接套入当前文件替换。

“保留大小写”对静态替换处理全大写、全小写、首字母和对应的连字符/下划线分段，例如 `FOO/foo/Foo` 替换成 `bar` 得到 `BAR/bar/Bar`。包含捕获引用的动态替换按引用和显式大小写操作生成结果；VS Code 不再对整个动态结果应用此开关。

匹配使用 Helix 的 Rust regex 引擎，支持常用捕获组、Unicode、跨行和行首/行尾；JavaScript 正则的环视和模式内反向引用仍不支持。无效表达式在面板内提示，不修改文件。替换字符串解析独立按 VS Code 实现。

## 来源与验证

官方文档：[Basic editing — Find and replace](https://code.visualstudio.com/docs/editing/codebasics#_find-and-replace)。源码固定于 `e97039dd9293ef2b9df8876d0bc8c0c8ff87f871`，路径与哈希见 [vscode-reference-manifest.json](vscode-reference-manifest.json)：`findWidget.ts`、`findController.ts`、`findModel.ts`、`replacePattern.ts`、`search.ts` 和 `textModelSearch.ts`。

`tests/vscode_find_replace_oracle.mjs` 执行固定版本上游 TypeScript，核对 66 个替换字符串案例。Rust 单元测试核对相同结果，另覆盖词边界和 CRLF 偏移；`tests/find_widget_regression.py` 通过真实 PTY 验证布局、鼠标、选区、Unicode、替换和撤销。完整安装后的工作区冒烟还验证 F4、新面板和组合键转发。最新结果见 [find-widget-results.json](find-widget-results.json)。

```sh
node prototype/helix/tests/vscode_find_replace_oracle.mjs /path/to/reference-cache --fetch
python prototype/helix/tests/find_widget_regression.py --binary /path/to/hx --runtime /path/to/runtime
```
